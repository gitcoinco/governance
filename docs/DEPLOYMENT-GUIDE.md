# Guide to Deploying Contracts With Brownie 

## Brownie Install Setup & Config

Brownie is a Python-based development and testing framework for smart contracts targeting the Ethereum Virtual Machine. Detailed instructions for installing Brownie can be found [here](https://eth-brownie.readthedocs.io/en/stable/install.html). 

One nice thing about Brownie is that you can install it using pipx and it will install Brownie into a virtual environment and makes it available directly from the commandline. Once installed, you will never have to activate a virtual environment prior to using Brownie.

#### Setting up your brownie config file(s)

1) `brownie-config.yaml` - If saved in the root directory of a project it will be loaded whenever that project is active. If saved in your home path, it will always be loaded. More info on how to setup/configure [brownie-config.yaml here](https://eth-brownie.readthedocs.io/en/stable/config.html#config). 

2) `network-config.yaml` - While network configurations can also be put in brownie-config.yaml it's a good idea to put your network configs outside your repo directory as it will likely contain some private info. By default, Brownie will install a network-config file in `~/.brownie/network-config.yaml`

You can set your things like Infura keys and test mnemonics in your local network-config.yaml so you don't have to manually set them with environment variables. 

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


