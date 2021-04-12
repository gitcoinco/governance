# Gitcoin Governance Contracts   

**This repository is currently private but when the project goes live they will be released publicly under the GNU AFFERO GENERAL PUBLIC LICENSE V3.** 

For our milestone one release we establish the foundational components of decentralized governance system based heavily on the gold standard set by Compound Finance and Uniswap.  

The GTC token distribution event will be front lined by the Quadratic Lands experience. The [Quadratic Lands](https://gitcoin.co/quadraticlands) is an portal to decentralized GTC Token governance where the Gitcoin community can interact with the governance system.  

# Primary Contracts 

1) GTC.sol - ERC20 contract for the GTC Token forked from [Uni.sol](https://github.com/Uniswap/governance/blob/master/contracts/Uni.sol)
2) TokenDistributor.sol - Contract responsible for distributing initial batch of GTC tokens to the community  
3) GovernorAlpha.sol - The governance module of the protocol
4) TimeLock.sol -  The Timelock contract can modify system parameters, logic, and contracts in a 'time-delayed, opt-out' upgrade pattern 
5) TreasuryVester.sol - Contract that can be used to establish a single batch of vested treasury tokens 

 *You can explore live Rinkeby data from all of these contracts with this [Ecosystem Health Query](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=ecosystem-health) on the GTC Token subgraphs.

## 1 - [GTC Token](/docs/GTC-TOKEN.md) 

The [GTC.sol](contracts/GTC.sol) contract is an ERC20 contract forked from Uniswap/Compound. Beyond the standard ERC20 functionally it also has a token delegation feature that allows token holders to allocate voting shares to other addresses or delegates. More detailed info on the contract can be found here [docs/GTC-TOKEN.md](docs/GTC-TOKEN.md). 

You can explore live rinkeby blockchain data for GTC Token contract on the [Gitcoin Token Subgraphs](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=tokenTransfers). 


## 2 - [GTC Token Distributor](/docs/TOKEN-DISTRIBUTOR.md) 
The primary purpose of our [token distribution contract](/contracts/TokenDistributor.sol) is to facilitate retroactive distribution of GTC tokens to users of the Gitcoin protocol. 

You can explore live rinkeby blockchain data for GTC Token Distributor contract on the [Gitcoin Token Subgraphs](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=TokenClaims). 


## 3 - [GovernorAlpha](docs/ZACTODO.md)
[Gitcoin GovernorAlpha](contracts/GovernorAlpha.sol) This contract will..... 

You can explore live Rinkeby blockchain data for the GovernorAlpha contract on the [Gitcoin Token Subgraphs](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=ZAC_TODO).

## 4 - [TimeLock](docs/ZACTODO.md)
[Gitcoin TimeLock](contracts/Timelock.sol) This contract will..... 

You can explore live Rinkeby blockchain data for the Timelock contract on the [Gitcoin Token Subgraphs](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=ZAC_TODO).

## 5 - [TreasuryVester](docs/ZACTODO.md)
[Gitcoin TerasuryVester](contracts/GovernorAlpha.sol) This contract will..... 

You can explore live Rinkeby blockchain data for the GovernorAlpha contract on the [Gitcoin Token Subgraphs](https://thegraph.com/explorer/subgraph/nopslip/wolf-vision?query=ZAC_TODO).

---

### Deployment & Admin Guides: 

[How to deploy contracts with Brownie](docs/deployment-guide.md) or all other guides can be found [in the /docs](/docs) directory. 



