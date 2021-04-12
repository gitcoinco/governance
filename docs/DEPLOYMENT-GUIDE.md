# Guide to Deploying Contracts With Brownie 

## Brownie Install Setup & Config

Brownie is a Python-based development and testing framework for smart contracts targeting the Ethereum Virtual Machine. Detailed instructions for installing Brownie can be found [here](https://eth-brownie.readthedocs.io/en/stable/install.html). 

One nice thing about Brownie is that you can install it using pipx and it will install Brownie into a virtual environment and makes it available directly from the commandline. Once installed, you will never have to activate a virtual environment prior to using Brownie.

## Deploy Governance Contracts Locally 

You can use this [script](../scripts/deploy-all.py) to easily deploy all contract and automatically run some of the base configurations like this:

```bash
brownie console 
```
This will launch a local Etheruem test/dev chain using `ganach-cli`. Next, from the within the brownie console run the deployment script: 

```python
>>> run('deploy-all')
```

---


