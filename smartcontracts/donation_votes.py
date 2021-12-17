import sys
from pyteal import *


class AppVariables:
    """
    All the possible global variables in the application.
    """

    # Count of votes for option one org.
    optionOneVotes = "optionOneVotes"
    # Count of votes for option two org.
    optionTwoVotes = "optionTwoVotes"
    # Creator of the smart contract wallet address.
    creatorAddress = "creatorAddress"
    # Start time for the current challenge in unix timestamp.
    startTime = "startTime"
    # End time for the current challenge in unix timestamp.
    endTime = "endTime"
    # Asset ID which is needed in a user's wallet to allow them to vote.
    assetID = "assetID"
    # Current challenge ID.
    challengeID = "challengeID"
    # Option one org name.
    optionOneName = "optionOneName"
    # Option two org name.
    optionTwoName = "optionTwoName"
    # Option one org's wallet address.
    optionOneWallet = "optionOneWallet"
    # Option two org's wallet address.
    optionTwoWallet = "optionTwoWallet"
    # Asset required to vote.
    voteAsset = "voteAsset"


class LocalVariables:
    """
    All the possible local variables in the application.
    """

    # Last challenge the user voted on.
    lastVotedID = "lastVotedID"
    # Last org the user voted on.
    lastVotedOptionName = "lastVotedOption"


class DefaultValues:
    defaultVotes = 0


def remove_existing_vote():
    # Total votes for org one.
    option_one_votes = App.globalGet(Bytes(AppVariables.optionOneVotes))
    # Total votes for org two.
    option_two_votes = App.globalGet(Bytes(AppVariables.optionTwoVotes))
    # Org one name.
    option_one_name = App.globalGet(Bytes(AppVariables.optionOneName))
    # Org two name.
    option_two_name = App.globalGet(Bytes(AppVariables.optionTwoName))
    # Org user last voted for.
    user_current_voted_option = App.localGet(
        Txn.sender(), Bytes(LocalVariables.lastVotedOptionName)
    )

    return Seq(
        [
            If(user_current_voted_option == option_one_name)
            .Then(
                App.globalPut(
                    Bytes(AppVariables.optionOneVotes), option_one_votes - Int(1)
                )
            )
            .Else(
                App.globalPut(
                    Bytes(AppVariables.optionTwoVotes), option_two_votes - Int(1)
                )
            )
        ]
    )


def on_create():
    """
    Initialization of the global variables in the application with the previously defined default values and application args.
    :return:
    """
    start_time = Btoi(Txn.application_args[2])
    end_time = Btoi(Txn.application_args[3])
    challenge_id = Btoi(Txn.application_args[4])
    option_one_name = Txn.application_args[5]
    option_two_name = Txn.application_args[6]
    asset_id = Btoi(Txn.application_args[7])
    option_one_wallet = Txn.application_args[8]
    option_two_wallet = Txn.application_args[9]
    vote_asset = Btoi(Txn.application_args[10])

    return Seq(
        [
            Assert(And(Global.latest_timestamp() < end_time, challenge_id != Int(0))),
            App.globalPut(Bytes(AppVariables.creatorAddress), Txn.sender()),
            App.globalPut(
                Bytes(AppVariables.optionOneVotes), Int(DefaultValues.defaultVotes)
            ),
            App.globalPut(
                Bytes(AppVariables.optionTwoVotes), Int(DefaultValues.defaultVotes)
            ),
            App.globalPut(Bytes(AppVariables.startTime), start_time),
            App.globalPut(Bytes(AppVariables.endTime), end_time),
            App.globalPut(Bytes(AppVariables.challengeID), challenge_id),
            App.globalPut(Bytes(AppVariables.optionOneName), option_one_name),
            App.globalPut(Bytes(AppVariables.optionTwoName), option_two_name),
            App.globalPut(Bytes(AppVariables.assetID), asset_id),
            App.globalPut(Bytes(AppVariables.optionOneWallet), option_one_wallet),
            App.globalPut(Bytes(AppVariables.optionTwoWallet), option_two_wallet),
            App.globalPut(Bytes(AppVariables.voteAsset), vote_asset),
            Approve(),
        ]
    )


# OnVote handles a user casting a vote.
def on_vote():
    # Checks what challenge the user last voted on.
    user_last_voted_challenge_id = App.localGet(
        Txn.sender(), Bytes(LocalVariables.lastVotedID)
    )
    # Checks if the user is holding a specified asset.
    user_holds_vote_asset = AssetHolding.balance(
        Txn.sender(), App.globalGet(Bytes(AppVariables.voteAsset))
    )
    # The organization that the user is voting for.
    user_choice = Txn.application_args[1]
    # Total votes for org one.
    option_one_votes = App.globalGet(Bytes(AppVariables.optionOneVotes))
    # Total votes for org two.
    option_two_votes = App.globalGet(Bytes(AppVariables.optionTwoVotes))
    # Org one name.
    option_one_name = App.globalGet(Bytes(AppVariables.optionOneName))
    # Org two name.
    option_two_name = App.globalGet(Bytes(AppVariables.optionTwoName))

    # Checks that the organization the user voted for is in the current challenge.
    user_vote_valid = Or(
        user_choice == App.globalGet(Bytes(AppVariables.optionOneName)),
        user_choice == App.globalGet(Bytes(AppVariables.optionTwoName)),
    )

    # Checks that the user holds the asset that allows for voting and that the current time is within the allowed voting time range.
    can_user_vote = And(
        user_holds_vote_asset.value() > Int(0),
        Global.latest_timestamp() > App.globalGet(Bytes(AppVariables.startTime)),
        Global.latest_timestamp() < App.globalGet(Bytes(AppVariables.endTime)),
    )

    # Checks if user has voted in the current challenge.
    has_user_voted = user_last_voted_challenge_id == App.globalGet(
        Bytes(AppVariables.challengeID)
    )

    # Updates vote count with users choice.
    add_new_vote = (
        If(user_choice == option_one_name)
        .Then(
            App.globalPut(Bytes(AppVariables.optionOneVotes), option_one_votes + Int(1))
        )
        .Else(
            App.globalPut(Bytes(AppVariables.optionTwoVotes), option_two_votes + Int(1))
        )
    )

    # Update local variables on user's wallet.
    update_user_local_variables = Seq(
        [
            App.localPut(
                Txn.sender(),
                Bytes(LocalVariables.lastVotedID),
                App.globalGet(Bytes(AppVariables.challengeID)),
            ),
            App.localPut(
                Txn.sender(), Bytes(LocalVariables.lastVotedOptionName), user_choice
            ),
        ]
    )

    return Seq(
        [
            user_holds_vote_asset,
            Assert(user_vote_valid),
            Assert(can_user_vote),
            If(has_user_voted).Then(remove_existing_vote()),
            add_new_vote,
            update_user_local_variables,
            Approve(),
        ]
    )


# OnSetup handles opting in the smart contract into a specified asset.
def on_setup():
    # Asset to be opted in.
    opt_in_asset = Btoi(Txn.application_args[1])

    return Seq(
        [
            Assert(
                And(
                    # The wallet triggering the setup must be the original creator and receiver.
                    Txn.sender()
                    == App.globalGet(Bytes(AppVariables.creatorAddress))
                )
            ),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    # Send 0 units of the asset to itself to opt-in.
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: opt_in_asset,
                    TxnField.asset_receiver: Global.current_application_address(),
                }
            ),
            InnerTxnBuilder.Submit(),
            Approve(),
        ]
    )


# OnWithdraw handles sending assets to the winning organization's wallet.
def on_complete_voting():
    # Asset to be withdrawn.
    withdraw_asset_id = Btoi(Txn.application_args[1])
    total_votes = App.globalGet(Bytes(AppVariables.optionOneVotes)) + App.globalGet(
        Bytes(AppVariables.optionTwoVotes)
    )
    asset_holding = AssetHolding.balance(
        Global.current_application_address(), withdraw_asset_id
    )

    # Send wallet specified amount of asset.
    @Subroutine(TealType.none)
    def sendAssetsTo(wallet: Expr, amount: Expr) -> Expr:
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: withdraw_asset_id,
                    TxnField.asset_amount: amount,
                    TxnField.asset_receiver: wallet,
                    TxnField.sender: Global.current_application_address(),
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    # Send rest of asset to specified wallet.
    @Subroutine(TealType.none)
    def closeAssetsTo(wallet: Expr) -> Expr:
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: withdraw_asset_id,
                    TxnField.asset_close_to: wallet,
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    return Seq(
        [
            asset_holding,
            Assert(
                And(
                    # The wallet triggering the withdraw must be the original creator.
                    Txn.sender() == App.globalGet(Bytes(AppVariables.creatorAddress)),
                    # The current time must be after the end time.
                    Global.latest_timestamp()
                    > App.globalGet(Bytes(AppVariables.endTime)),
                    # Smart contract must hold specified asset
                    asset_holding.hasValue(),
                )
            ),
            # Send wallet one number of assets proportional to number of votes option one recieved.
            sendAssetsTo(
                App.globalGet(Bytes(AppVariables.optionOneWallet)),
                asset_holding.value()
                * App.globalGet(Bytes(AppVariables.optionOneVotes))
                / total_votes,
            ),
            # # Send rest of assets to wallet two.
            closeAssetsTo(App.globalGet(Bytes(AppVariables.optionTwoWallet))),
            Approve(),
        ]
    )


# Handle updating the smart contract to start a new challenge.
def on_update():
    withdraw_asset_id = App.globalGet(Bytes(AppVariables.assetID))
    start_time = Btoi(Txn.application_args[1])
    end_time = Btoi(Txn.application_args[2])
    option_one_name = Txn.application_args[3]
    option_two_name = Txn.application_args[4]
    option_one_wallet = Txn.application_args[5]
    option_two_wallet = Txn.application_args[6]
    new_asset_id = Btoi(Txn.application_args[7])
    current_challenge_id = App.globalGet(Bytes(AppVariables.challengeID))

    asset_holding = AssetHolding.balance(
        Global.current_application_address(), withdraw_asset_id
    )

    return Seq(
        [
            asset_holding,
            Assert(
                And(
                    # The wallet triggering the close must be the original creator and receiver.
                    Txn.sender() == App.globalGet(Bytes(AppVariables.creatorAddress)),
                    # Can only update after current challenge is over.
                    Global.latest_timestamp()
                    > App.globalGet(Bytes(AppVariables.endTime)),
                    # Make sure previous vote rewards have been sent before updating.
                    asset_holding.value() == Int(0),
                )
            ),
            App.globalPut(Bytes(AppVariables.optionOneName), option_one_name),
            App.globalPut(Bytes(AppVariables.optionTwoName), option_two_name),
            App.globalPut(Bytes(AppVariables.startTime), start_time),
            App.globalPut(Bytes(AppVariables.endTime), end_time),
            App.globalPut(Bytes(AppVariables.optionOneWallet), option_one_wallet),
            App.globalPut(Bytes(AppVariables.optionTwoWallet), option_two_wallet),
            App.globalPut(Bytes(AppVariables.assetID), new_asset_id),
            App.globalPut(
                Bytes(AppVariables.challengeID), current_challenge_id + Int(1)
            ),
            App.globalPut(
                Bytes(AppVariables.optionOneVotes), Int(DefaultValues.defaultVotes)
            ),
            App.globalPut(
                Bytes(AppVariables.optionTwoVotes), Int(DefaultValues.defaultVotes)
            ),
            Approve(),
        ]
    )


def handle_no_op():
    return Cond(
        [Txn.application_args[0] == Bytes("completeVoting"), on_complete_voting()],
        [Txn.application_args[0] == Bytes("vote"), on_vote()],
        [Txn.application_args[0] == Bytes("setup"), on_setup()],
        [Txn.application_args[0] == Bytes("update"), on_update()],
    )


def closeAssetsTo(account: Expr) -> Expr:
    asset_id = App.globalGet(Bytes(AppVariables.assetID))
    asset_holding = AssetHolding.balance(Global.current_application_address(), asset_id)
    return Seq(
        asset_holding,
        If(asset_holding.value() == Int(0))
        .Then(
            Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: asset_id,
                        TxnField.asset_close_to: account,
                    }
                ),
                InnerTxnBuilder.Submit(),
            )
        )
        .Else(Seq([Reject()])),
    )


def close_account_to(account: Expr) -> Expr:
    asset_balance = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(Bytes(AppVariables.assetID))
    )
    return Seq(
        [
            asset_balance,
            If(asset_balance.value() == Int(0))
            .Then(
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
            .Else(Seq([Reject()])),
        ]
    )


def handle_delete():
    creator_account = App.globalGet(Bytes(AppVariables.creatorAddress))
    return Seq(
        [
            Assert(
                And(
                    # The wallet triggering the close must be the original creator and receiver.
                    Txn.sender() == App.globalGet(Bytes(AppVariables.creatorAddress)),
                    # Can only delete after current challenge is over.
                    Global.latest_timestamp()
                    > App.globalGet(Bytes(AppVariables.endTime)),
                )
            ),
            # Remove assets before deleting
            closeAssetsTo(creator_account),
            # Remove algos before deleting
            close_account_to(creator_account),
            Approve(),
        ]
    )


# Handle wallet opting into the smart contract.
def handle_opt_in():
    return Seq(
        [
            App.localPut(Txn.sender(), Bytes(LocalVariables.lastVotedID), Int(0)),
            App.localPut(
                Txn.sender(), Bytes(LocalVariables.lastVotedOptionName), Bytes("NA")
            ),
            Approve(),
        ]
    )


# Handle updating the smart contract to start a new challenge.
def handle_close_out():
    # Org user last voted for.
    user_current_voted_option = App.localGet(
        Txn.sender(), Bytes(LocalVariables.lastVotedOptionName)
    )

    # Checks what challenge the user last voted on.
    user_last_voted_challenge_id = App.localGet(
        Txn.sender(), Bytes(LocalVariables.lastVotedID)
    )

    # Checks if user has voted in the current challenge.
    has_user_voted = user_last_voted_challenge_id == App.globalGet(
        Bytes(AppVariables.challengeID)
    )

    return Seq([If(has_user_voted).Then(remove_existing_vote()), Approve()])


def approval_program():
    """
    Approval program of the application. Combines all the logic of the application that was implemented previously.
    :return:
    """

    program = Cond(
        [Txn.application_id() == Int(0), on_create()],
        [Txn.on_completion() == OnComplete.NoOp, handle_no_op()],
        [Txn.on_completion() == OnComplete.OptIn, handle_opt_in()],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_delete()],
        [Txn.on_completion() == OnComplete.CloseOut, handle_close_out()],
        [
            Or(
                # This smart contract cannot be updated.
                Txn.on_completion()
                == OnComplete.UpdateApplication,
            ),
            Reject(),
        ],
    )

    return program


def clear_program():
    return Approve()


original_stdout = sys.stdout

with open("donation_votes_approval.teal", "w") as f:
    sys.stdout = f
    print(compileTeal(approval_program(), Mode.Application, version=5))
    sys.stdout = original_stdout

with open("donation_votes_clear.teal", "w") as f:
    sys.stdout = f
    print(compileTeal(clear_program(), Mode.Application, version=5))
    sys.stdout = original_stdout
