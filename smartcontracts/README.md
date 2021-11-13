# Getting Started
- [Install Docker Desktop](https://docs.docker.com/desktop/mac/install/)
- [Install PyTeal](https://pyteal.readthedocs.io/en/stable/installation.html)
- If you use VS Code, there is the [Algorand VS Code Extension](https://marketplace.visualstudio.com/items?itemName=obsidians.vscode-algorand)
- From the root of this repository, set up Python virtual environment

        python3 -m venv venv

- From the root of this repository, to activate the virtual environment

        . venv/bin/activate

- From the root of this repository, install requirements. You may need to re-run this if more requirements are added in the future.
        
        pip3 install -r requirements.txt

# Resources
- [TEAL (Transaction Execution Approval Language) Documentation](https://developer.algorand.org/docs/get-details/dapps/avm/teal/specification/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/en/stable/overview.html)
- [TEAL Guidelines](https://developer.algorand.org/docs/get-details/dapps/avm/teal/guidelines/) Important for production quality code!
