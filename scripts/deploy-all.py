from brownie import accounts, web3, GTC, TokenDistributor, Timelock, GovernorAlpha, TreasuryVester, Wei
import time
import sys
from dotenv import dotenv_values
import csv

''' 
### TLDR:
open brownie console:
run('deploy-all')

run individual functions (after initial deploy) - run('deploy-all', 'token_distributor') 

or just run the script:
brownie run deploy-all.py --gas 

### deploy to Rinkeby 

from terminal: 

1) set Web3 provider:
`export WEB3_INFURA_PROJECT_ID=''`

2) optional if - PUBLISH_SOURCE_TO_ETHERSCAN=True
`export export ETHERSCAN_TOKEN=''`

3) open brownie console:
`brownie console --network rinkeby`

4) load your mnemonic into brownie  
`accounts.from_mnemonic('your-mnemonic-here',10)`

5) network.gas_limit(10000000)
6) network.gas_price("2 gwei")

7) run('deploy-all')

GTC Token deploy will mint tokens to first param, since distributor has not been deployed yet, we send to HOPPER_ADDRESS
HOPPER_ADDRESS then needs to send to dist contract before claims will process (so tokendist has coins to send!)
'''

env_file = ".deploy-all-local-env"

def main():
    loginfo() # print out some relevant info about our environment 
  
    if VALIDATE_PARAMS: # check hardcoded contract params against constructor params 
         validate_params() 
    
    # [[ deploy tx #1 - TIMELOCK.sol]]
    try:
        tl = Timelock.deploy(TIMELOCK_ADMIN, TIMELOCK_DELAY, {'from': DEPLOY_FROM}, publish_source=PUBLISH_SOURCE)
    except Exception as e:
        print(f'Error on Timelock deploy: {e}')
        sys.exit(1)

    # [[ deploy tx #2 - GTC.sol]]
    try:
        gtc = GTC.deploy(HOPPER_ADDRESS, HOPPER_ADDRESS, GTC_MINT_AFTER, {'from': DEPLOY_FROM}, publish_source=PUBLISH_SOURCE)
    except Exception as e:
        print(f'Error on GTC contract deploy {e}')
        sys.exit(1)
    
    # [[ deploy tx #3 - Tokendistributor.sol ]]
    try:
        td = TokenDistributor.deploy(gtc.address, TOKEN_CLAIM_SIGNER, tl.address, MERKLE_ROOT, {'from': DEPLOY_FROM}, publish_source=PUBLISH_SOURCE)
    except Exception as e:
        print(f'Error on TokenDistributor contract deploy: {e}')
        sys.exit(1)

    # [[ deploy tx #4 - GovernorAlpha.sol ]] 
    try:
        gov = GovernorAlpha.deploy(tl.address, gtc.address, {'from' : DEPLOY_FROM}, publish_source=PUBLISH_SOURCE)
    except Exception as e:
        print(f'Error on GovernorAlpha deploy: {e}')
        sys.exit(1)
    
    # [[ deploy tx #5 - TreasuryVester.sol ]] 
    try: 
        tv = TreasuryVester.deploy(gtc.address, tl.address, Wei(f'{TREASURY_VESTING_AMOUNT} ether'), TREASURY_VESTING_BEGIN, TREASURY_VESTING_CLIFF, TREASURY_VESTING_END, {'from' : DEPLOY_FROM}, publish_source=PUBLISH_SOURCE)
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
        gtc.transfer(td.address,Wei(f'{INITIAL_MINT/2} ether'), {'from': HOPPER_ADDRESS})
    except Exception as e:
        print(f'Error transfering coins to TokenDistribution contract')
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
        hopper_balance = gtc.balanceOf(HOPPER_ADDRESS) 
        gtc.transfer(tv.address, hopper_balance, {'from': HOPPER_ADDRESS})
    except Exception as e:
        print(f'Error sending coins to TreasuryVester: {e}')
        sys.exit(1)

    # end main()
     
def transfer_to_team(gtc):
    '''Transfer team coins to coinbase custody'''
    with open("./scripts/team.csv", 'r') as csvfile:
        team = csv.reader(csvfile)
        for row in team:
            gtc.transfer(row[0],row[1], {'from': HOPPER_ADDRESS})      

def transfer_to_funders(gtc):
    '''Transfer funders league coins'''
    with open(env['FUNDERS_DIST'], 'r') as csvfile:
        funders = csv.reader(csvfile)
        for row in funders:
            gtc.transfer(row[0],row[1], {'from': HOPPER_ADDRESS})

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
    gtc.setGTCDist(td.address, {'from': HOPPER_ADDRESS})
    print(f'Token now has the TokenDistribution address set to: {gtc.GTCDist()}')

def set_minter(gtc, tl):
    '''set minter address on the token contract'''
    gtc.setMinter(tl.address, {'from': HOPPER_ADDRESS})
    print(f'Token minter address is now set to address: {gtc.minter()}')

def valid_address(address, name):
    '''used to validate an address'''
    try:
        valid_address = web3.toChecksumAddress(address)
    except ValueError:
        print(f'{name} does not appear to be a valid Ethereum address. Please confirm address is correct and try again.')
        sys.exit(1)
    return valid_address    

def valid_unix_time(time, name):
    '''used to validate that a given unix time param is valid'''
    try:
        valid_unix_time = int(time)
        return valid_unix_time
    except ValueError:
        print(f'Invalid unix time found for: {name}. Please confirm {name} is an integer and try again.')
        sys.exit(1)
    
def valid_boolean(value, name):
    '''return bool'''
    if value == 'True' or value == 'true':
        return True
    if value == 'False' or value == 'false':
        return False
    else:
        print(f'{name} must be True or False. Please check {name} and try again.')
        sys.exit(1)

def valid_hexstr(value, name):
    '''Primitive/limited check to confirm we have a valid hexstr'''
    try:
        web3.toBytes(hexstr=value)
        return value
    except Exception as e:
        print(f'{name} does not appear to be a valid hexstr.')
        sys.exit(1)

def valid_int(value, name):
    '''Confrim value is a valid integer'''
    try:
        int_value = int(value)
        if str(int_value) == value:
            return int_value
        else:
            raise ValueError(f'{name} does not have a valid value')
    except Exception as e:
        print(f'There was an issue validating {name} - {e}')

def validate_params():
    '''Compare constructor params with hardcoded contract params to make sure we wont fail deploy'''
    # TIMELOCK.sol
    if not TIMELOCK_DELAY >= MINIMUM_DELAY:
        print(f'TIMELOCK_DELAY must be >= MINIMUM_DELAY. Exiting deploy as per VALIDATE_PARAMS=True')
        sys.exit(1)
    if not TIMELOCK_DELAY <= MAXIMUM_DELAY:
        print(f'TIMELOCK_DELAY must be <= MAXIMUM_DELAY. Exiting deploy as per VALIDATE_PARAMS=True')
        sys.exit(1)
    
    # GTC.sol 
    if not GTC_MINT_AFTER >= time.time():
        print(f'GTC_MINT_AFTER must be >= current block time - minting can only begin after deployment. Exiting deploy as per VALIDATE_PARAMS=True')
        sys.exit(1)
    
    # TreasuryVester.sol 
    if not TREASURY_VESTING_BEGIN >= time.time():
        print(f'TREASURY_VESTING_BEGIN must be >= deploy time - vesting begin too early')
        sys.exit(1)
    if not TREASURY_VESTING_CLIFF >= TREASURY_VESTING_BEGIN:
        print(f'TREASURY_VESTING_CLIFF must be >= TREASURY_VESTING_BEGIN - cliff is too early')
        sys.exit(1)
    if not TREASURY_VESTING_END > TREASURY_VESTING_CLIFF:
        print(f'TREASURY_VESTING_END must be > TREASURY_VESTING_CLIFF - end is too early')
        sys.exit(1)

# load up the envars 
try:
    env = dotenv_values(env_file)
except Exception as e:
    print(f'Unable to load environment variables. Please confirm file exists - {e}')
    sys.exit(1)

TIMELOCK_ADMIN = valid_address(env['TIMELOCK_ADMIN'], 'TIMELOCK_ADMIN') # ends up as
TIMELOCK_DELAY = valid_unix_time(env['TIMELOCK_DELAY'], 'TIMELOCK_DELAY') # delay in seconds before a proposal can be executed 
DEPLOY_FROM = valid_address(env['DEPLOY_FROM'], 'DEPLOY_FROM')
PUBLISH_SOURCE = valid_boolean(env['PUBLISH_SOURCE_TO_ETHERSCAN'], 'PUBLISH_SOURCE')
GTC_MINT_AFTER = valid_unix_time(env['GTC_MINT_AFTER'], 'GTC_MINT_AFTER')
HOPPER_ADDRESS = valid_address(env['HOPPER_ADDRESS'], 'HOPPER_ADDRESS') # Temp address used during initial deploy
TOKEN_CLAIM_SIGNER = valid_address(env['TOKEN_CLAIM_SIGNER'], 'TOKEN_CLAIM_SIGNER')
MERKLE_ROOT = valid_hexstr(env['MERKLE_ROOT'], 'MERKLE_ROOT')
TREASURY_VESTING_AMOUNT = valid_int(env['TREASURY_VESTING_AMOUNT'], 'TREASURY_VESTING_AMOUNT')
TREASURY_VESTING_BEGIN = valid_unix_time(env['TREASURY_VESTING_BEGIN'], 'TREASURY_VESTING_BEGIN')
TREASURY_VESTING_CLIFF = valid_unix_time(env['TREASURY_VESTING_CLIFF'], 'TREASURY_VESTING_CLIFF')
TREASURY_VESTING_END = valid_unix_time(env['TREASURY_VESTING_END'], 'TREASURY_VESTING_END')
VALIDATE_PARAMS = valid_boolean(env['VALIDATE_PARAMS'], 'VALIDATE_PARAMS') # should we proactively check that params wont fail deploy?
INITIAL_MINT = valid_int(env['INITIAL_MINT'], 'INITIAL_MINT') # total amount initially minted 

if VALIDATE_PARAMS:
    # what are the hardcoded params from Timelock?
    MINIMUM_DELAY = valid_unix_time(env['MINIMUM_DELAY'], 'MINIMUM_DELAY')
    MAXIMUM_DELAY = valid_unix_time(env['MAXIMUM_DELAY'], 'MAXIMUM_DELAY')