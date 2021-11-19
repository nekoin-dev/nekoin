from pyteal import *
import sys


def approval_program():
    # Keys for the global data stored by this smart contract.

    # AssetID that this smart contract will freeze.
    # For Nekoin, this is 404044168.
    asset_id_key = Bytes("asset_id")
    # Address of the wallet that will receive the funds in this smart contract when it is closed.
    # For Nekoin, this is O6UUGUA4LCJSMYUP2ZYHRETX5I2XJSXELGJCRDCBDNQ7KSSCBJRSPZRZCI.
    # We will freeze the donation wallet's 2 billion Nekos.
    receiver_address_key = Bytes("receiver_address_key")
    # Unix timestamp after which this smart contract can be closed.
    # For Nekoin, this is 1669881600 which is December 1, 2022 00:00:00 PST
    unlock_time_key = Bytes("unlock_time")
    # Unix timestamp when last withdrawal occured.
    last_withdrawal_time_key = Bytes("latest_withdrawal_time")
    # Period of time represented in seconds when at most one transfer is allowed.
    # For Nekoin, this is 604800 which is one week
    time_period_key = Bytes("time_period")
    # Unix timestamp for when the smart contract begins.
    contract_start_time_key = Bytes("contract_start_time")
    # Amount of asset to be withdrawn per withdrawal.
    withdraw_amount_key = Bytes("withdraw_amount")

    # Sends all of the asset specified by assetID to the specified account.
    @Subroutine(TealType.none)
    def closeAssetsTo(assetID: Expr, account: Expr) -> Expr:
        asset_holding = AssetHolding.balance(
            Global.current_application_address(), assetID
        )
        return Seq(
            asset_holding,
            If(asset_holding.hasValue()).Then(
                Seq(
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields(
                        {
                            TxnField.type_enum: TxnType.AssetTransfer,
                            TxnField.xfer_asset: assetID,
                            TxnField.asset_close_to: account,
                        }
                    ),
                    InnerTxnBuilder.Submit(),
                )
            ),
        )

    # Sends all of the Algo's to the specified account.
    @Subroutine(TealType.none)
    def closeAccountTo(account: Expr) -> Expr:
        return If(Balance(Global.current_application_address()) != Int(0)).Then(
            Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.close_remainder_to: account,
                    }
                ),
                InnerTxnBuilder.Submit(),
            )
        )

    # Sends specified withdrawal amount of an asset specified by assetID to the specified account.
    @Subroutine(TealType.none)
    def sendAssetsTo(assetID: Expr, account: Expr) -> Expr:
        asset_holding = AssetHolding.balance(
            Global.current_application_address(), assetID
        )
        return Seq(
            asset_holding,
            If(asset_holding.value() > App.globalGet(withdraw_amount_key)).Then(
                Seq(
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields(
                        {
                            TxnField.type_enum: TxnType.AssetTransfer,
                            TxnField.xfer_asset: assetID,
                            TxnField.asset_amount: App.globalGet(withdraw_amount_key),
                            TxnField.asset_receiver: account,
                            TxnField.sender: Global.current_application_address(),
                        }
                    ),
                    InnerTxnBuilder.Submit(),
                    App.globalPut(last_withdrawal_time_key, Global.latest_timestamp()),
                )
            ),
        )

    # Check how long it has been since the current period has started.
    @Subroutine(TealType.uint64)
    def timeInCurrentPeriod():
        current_time_from_start_of_contract = Global.latest_timestamp() - App.globalGet(
            contract_start_time_key
        )
        return current_time_from_start_of_contract % App.globalGet(time_period_key)

    # Check how long it has been since the last withdrawal.
    @Subroutine(TealType.uint64)
    def timeSinceLastwithdrawal():
        return Global.latest_timestamp() - App.globalGet(last_withdrawal_time_key)

    # OnCreate handles creating this periodic withdrawal smart contract.
    # arg[0]: the assetID of the asset we want to freeze. For Nekoin it is 404044168
    # arg[1]: the recipient of the assets held in this smart contract. Must be the creator.
    # arg[2]: the Unix timestamp of when this smart contract can be closed. When the
    #         contract is closed, everything is sent to the receiver.
    # arg[3]: period of time represented in seconds when the sc will allow one withdrawal.
    # arg[4]: the Unix timestamp of when the first period begins.
    # arg[5]: the amount of the assetID to be withdrawn per withdrawal.
    on_create_receiver = Txn.application_args[1]
    on_create_unlock_time = Btoi(Txn.application_args[2])
    on_create_time_period = Btoi(Txn.application_args[3])
    on_create_contract_start_time = Btoi(Txn.application_args[4])
    on_create_withdraw_amount = Btoi(Txn.application_args[5])
    on_create = Seq(
        Assert(
            And(
                # The unlock timestamp must be at some point in the future.
                Global.latest_timestamp() < on_create_unlock_time,
                # Each time period must be longer than 0 seconds.
                on_create_time_period > Int(0),
                # Withdraw amount must be longer than 0.
                on_create_withdraw_amount > Int(0),
                # The transaction sender must be the recipeint of the funds.
                Txn.sender() == on_create_receiver,
            )
        ),
        App.globalPut(asset_id_key, Btoi(Txn.application_args[0])),
        App.globalPut(receiver_address_key, on_create_receiver),
        App.globalPut(unlock_time_key, on_create_unlock_time),
        App.globalPut(time_period_key, on_create_time_period),
        App.globalPut(contract_start_time_key, on_create_contract_start_time),
        App.globalPut(withdraw_amount_key, on_create_withdraw_amount),
        App.globalPut(last_withdrawal_time_key, Int(0)),
        Approve(),
    )

    # OnSetup handles setting up this freeze smart contract. Namely, it tells this smart
    # contract to opt into the asset it was created to hold. This smart contract must
    # hold enough Algo's to make this transaction.
    on_setup = Seq(
        Assert(
            And(
                # The wallet triggering the setup must be the original creator and receiver.
                Txn.sender() == App.globalGet(receiver_address_key),
                # This smart contract must be set up before the unlock timestamp.
                Global.latest_timestamp() < App.globalGet(unlock_time_key),
            )
        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                # Send 0 units of the asset to itself to opt-in.
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: App.globalGet(asset_id_key),
                TxnField.asset_receiver: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        Approve(),
    )

    # OnWithdraw handles withdrawing the money, which will trigger sending a specified amount of the funds to a user if a withdrawal has not been made in the same period of time.
    on_withdraw = Seq(
        Assert(
            And(
                # The wallet triggering the withdrawal must be the original creator and receiver.
                Txn.sender() == App.globalGet(receiver_address_key),
                # Check current time is after contract start time.
                Global.latest_timestamp() >= App.globalGet(contract_start_time_key),
                # Check if last withdrawal happened before the current period begins.
                timeSinceLastwithdrawal() > timeInCurrentPeriod(),
            )
        ),
        # Only run if the last withdrawal did not happen in the same time period.
        # Send specified amount of assets to reciever.
        sendAssetsTo(App.globalGet(asset_id_key), App.globalGet(receiver_address_key)),
        Approve(),
    )

    # Handle NoOp call.
    on_no_op = Cond(
        [Txn.application_args[0] == Bytes("setup"), on_setup],
        [Txn.application_args[0] == Bytes("withdraw"), on_withdraw],
    )

    # OnOptIn handles when a wallet requests to opt into this smart contract. Only the
    # wallet receiving (and sending) the funds can opt into this smart contract.
    on_opt_in = Seq(
        Assert(
            # Only the original creator and receiver can opt into this smart contract.
            Txn.sender()
            == App.globalGet(receiver_address_key)
        ),
        Approve(),
    )

    # OnDelete handles deleting the smart contract, which will trigger sending all the funds
    # held in this wallet to the receiver. This transaction will only be approved if the
    # latest_timestamp is after the unlock timestamp (the lock up has expired).
    on_delete = Seq(
        Assert(
            And(
                # The wallet triggering the close must be the original creator and receiver.
                Txn.sender() == App.globalGet(receiver_address_key),
                # The current timestamp must be greater than the unlock timestamp. Otherwise
                # this transaction will be rejected.
                App.globalGet(unlock_time_key) <= Global.latest_timestamp(),
            )
        ),
        # These operations are only run if unlock timestamp has passed.
        # Close all the assets and Algo's held by this account to the receiver.
        closeAssetsTo(App.globalGet(asset_id_key), App.globalGet(receiver_address_key)),
        closeAccountTo(App.globalGet(receiver_address_key)),
        Approve(),
    )

    # Application router for this smart contract.
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_no_op],
        [Txn.on_completion() == OnComplete.OptIn, on_opt_in],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [
            Or(
                # This smart contract cannot be closed out.
                Txn.on_completion() == OnComplete.CloseOut,
                # This smart contract cannot be updated.
                Txn.on_completion() == OnComplete.UpdateApplication,
            ),
            Reject(),
        ],
    )

    return program


def clear_program():
    return Approve()


original_stdout = sys.stdout

with open("periodic_withdrawals_approval.teal", "w") as f:
    sys.stdout = f
    print(compileTeal(approval_program(), Mode.Application, version=5))
    sys.stdout = original_stdout

with open("periodic_withdrawals_clear.teal", "w") as f:
    sys.stdout = f
    print(compileTeal(clear_program(), Mode.Application, version=5))
    sys.stdout = original_stdout
