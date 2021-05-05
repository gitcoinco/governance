from brownie import accounts, web3, GTC, TokenDistributor, Timelock, GovernorAlpha, TreasuryVester, Wei
import time
import sys
from dotenv import dotenv_values
import csv

''' 
brownie run deploy-all.py --gas  
or better yet, open console first, then run: 
run('deploy-all')
for individual functions (after initial deploy) - run('deploy-all', 'token_distributor') 

on Rinkeby
1) export your web3 node like - export WEB3_INFURA_PROJECT_ID=''
2) open `brownie console --network rinkeby`
3) accounts.from_mnemonic('your mnemonic here',10)
4) network.gas_limit(10000000)
5) network.gas_price("1 gwei")
6) run('deploy-all')

GTC Token deploy will mint tokens to first param, since distributor has not been deployed yet, we send to HOPPER_ADDRESS
HOPPER_ADDRESS then needs to send to dist contract before claims will process (so tokendist has coins to send!)
'''

# load up some envars 
env = dotenv_values(".deploy-all-local-env")

unix_time_now = time.time()

# some reasonable defaults 
# must be greater than block timestamp of contract deploy - for rinkeby & mainnet we need this to be long enough to accommodate for slow to confirm txs 
treasury_vesting_cliff = (60 * 60 * 24 * 7 * 12) + unix_time_now # 6 months in seconds
treasury_vesting_end = unix_time_now + (treasury_vesting_cliff*2) # this is not production config 

def main():
    # print out some relevant info about our testing env 
    loginfo()

    # DEPLOY TIMELOCK CONTRACT 
    '''<ContractConstructor 'Timelock.constructor(address admin_, uint256 delay_)'>
    /**
    * @notice Construct a new TimeLock contract 
    * @param admin_ - contract admin
    * @param delay_ - delay before successful proposal 
    **/
    ''' 
    try:
        if env['PUBLISH_SOURCE_TO_ETHERSCAN']:
            tl = Timelock.deploy(env['TIMELOCK_ADMIN'], env['TIMELOCK_DELAY'], {'from': env['DEPLOY_FROM']})
        else:
            tl = Timelock.deploy(env['TIMELOCK_ADMIN'], env['TIMELOCK_DELAY'], {'from': env['DEPLOY_FROM']})
    except Exception as e:
        print(f'Error on Timelock deploy: {e}')
        sys.exit(1)

    # DEPLOY TOKEN CONTRACT
    '''
     * @notice Construct a new GTC token
     * @param account The initial account to grant all the tokens
     * @param minter_ The account with minting ability
     * @param mintingAllowedAfter_ The timestamp after which minting may occur - Just adding 2 mins for Rinkeby
    '''
    # NOTE we set minter to hopper_address temporarily so that we have permissions to set the token distr address on token contract after deploy
    # minter is then immediately changed to the Timelock address.
    minting_allowed_after = int(env['GTC_MINT_AFTER_BUFFER']) + int(unix_time_now)   
    try:
        if env['PUBLISH_SOURCE_TO_ETHERSCAN']: 
            gtc = GTC.deploy(env['HOPPER_ADDRESS'], env['HOPPER_ADDRESS'], minting_allowed_after, {'from': env['DEPLOY_FROM']})
        else: 
            gtc = GTC.deploy(env['HOPPER_ADDRESS'], env['HOPPER_ADDRESS'], minting_allowed_after, {'from': env['DEPLOY_FROM']})
        print(f'GTC address {gtc.address}')
    except Exception as e:
        print(f'Error on GTC contract deploy {e}')
        sys.exit(1)
    
    # deploy TokenDistributor.sol takes 4 params, token address, signer address, timelock address, merkleRoot
    # signer address == corresponding public key (address/account) to the private key used 
    # to sign claims with Ethereum Signed Message Service  
    try:
        if env['PUBLISH_SOURCE_TO_ETHERSCAN']: 
            td = TokenDistributor.deploy(gtc.address, env['TOKEN_CLAIM_SIGNER'], tl.address, env['MERKLE_ROOT'], {'from': env['DEPLOY_FROM']})
        else:
            td = TokenDistributor.deploy(gtc.address, env['TOKEN_CLAIM_SIGNER'], tl.address, env['MERKLE_ROOT'], {'from': env['DEPLOY_FROM']})
    except Exception as e:
        print(f'Error on TokenDistributor contract deploy: {e}')
        sys.exit(1)
        
    # deploy the GovernorAlpha 
    try:
        if env['PUBLISH_SOURCE_TO_ETHERSCAN']:
            gov = GovernorAlpha.deploy(tl.address, gtc.address, {'from' : env['DEPLOY_FROM']})
        else:
            gov = GovernorAlpha.deploy(tl.address, gtc.address, {'from' : env['DEPLOY_FROM']})
    except Exception as e:
        print(f'Error on GovernorAlpha deploy: {e}')
        sys.exit(1)
    
    # deploy TresuryVester.sol
    # <ContractConstructor 'TreasuryVester.constructor(address gta_, address recipient_, uint256 vestingAmount_, uint256 vestingBegin_, uint256 vestingCliff_, uint256 vestingEnd_)'>
    time_now = time.time()
    treasury_vesting_begin = time_now + 3600
    try: 
        if env['PUBLISH_SOURCE_TO_ETHERSCAN']:
            tv = TreasuryVester.deploy(gtc.address, tl.address, env['TREASURY_VESTING_AMOUNT'], treasury_vesting_begin, treasury_vesting_cliff, treasury_vesting_end, {'from' : env['DEPLOY_FROM']})
        else: 
            tv = TreasuryVester.deploy(gtc.address, tl.address, env['TREASURY_VESTING_AMOUNT'], treasury_vesting_begin, treasury_vesting_cliff, treasury_vesting_end, {'from' : env['DEPLOY_FROM']})
    except Exception as e:
        print(f'Error on TreasuryVesting deploy: {e}')
        sys.exit(1)

    # allow token dist contract to set delegate addresses on the token contract 
    try: 
        set_GTCToken_address(td, gtc)
    except Exception as e:
        print(f'error running set_GTCToken_Address {e}')
        sys.exit(1) 

    # now that we've set the token dist address on the token contract
    # we need to set the minter on the token to the Timelock address 
    try: 
        set_minter(gtc, tl)
    except Exception as e:
        print(f'Error setting minter address on token contract')    
        sys.exit(1)
    
    ## DISTRIBUTE INITIAL TOKENS ## 
    # 1) - 1/2 to TokenDistributor
    try:  
        gtc.transfer(td.address,Wei("1500000 ether"), {'from': env['HOPPER_ADDRESS']})
    except Exception as e:
        print(f'Error transerting coins to TokenDistribution contract!')
        sys.exit(1)

    # 2) - transfer some coins to team 
    try: 
        transfer_to_team(gtc)
    except Exception as e:
        print(f'Error sending coins to team!')
        sys.exit(1)

    # 3) - transfer some coins to funders
    try: 
        transfer_to_funders(gtc)
    except Exception as e:
        print(f'Error sending coins to funders league!')
        sys.exit(1)

    # 4) - transfer remaining coins to TreasuryVester
    try:
        hopper_balance = gtc.balanceOf(env['HOPPER_ADDRESS']) 
        gtc.transfer(tv.address,hopper_balance, {'from': env['HOPPER_ADDRESS']})
    except Exception as e:
        print(f'Error sending coins to TreasuryVester: {e}')
        sys.exit(1)

    # end main()
     
def transfer_to_team(gtc):
    '''Transfer team coins to coinbase custody'''
    with open("./scripts/team.csv", 'r') as csvfile:
        team = csv.reader(csvfile)
        for row in team:
            gtc.transfer(row[0],row[1], {'from': env['HOPPER_ADDRESS']})      

def transfer_to_funders(gtc):
    '''Transfer funders league coins'''
    with open(env['FUNDERS_DIST'], 'r') as csvfile:
        funders = csv.reader(csvfile)
        for row in funders:
            gtc.transfer(row[0],row[1], {'from': env['HOPPER_ADDRESS']})

def loginfo():
    '''log some helpful into to the console'''
    print(f"\nWeb3 Provider URL: {web3.provider.endpoint_uri}\n")
    for account_number in range(9):
        print(f"account #: {account_number} - {accounts[account_number]}")
    print("\n")    

def set_GTCToken_address(td, gtc):
    '''Call this to set the GTCToken Address on the TokenDistributor contract. 
       This is needed because we have to deploy the GTCToken contract before the token distributor
    '''
    # td, gtc = TokenDistributor[0], GTC[0]
    gtc.setGTCDist(td.address, {'from': accounts[0]})
    print(f'Token now has the TokenDistribution address set to: {gtc.GTCDist()}')

def set_minter(gtc, tl):
    '''set minter address on the token contract'''
    gtc.setMinter(tl.address, {'from': env['HOPPER_ADDRESS']})
    print(f'Token minter address is now set to address: {gtc.minter()}')
