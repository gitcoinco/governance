from brownie import accounts, web3, GTA, TokenDistributor, Timelock, GovernorAlpha, TreasuryVester, Wei
import time
import sys

''' 
brownie run deploy-all.py --gas  
or better yet, open console first, then run: 
run('deploy-all')
for individual functions (after initial deploy) - run('deploy-all', 'token_distributor') 

on Rinkeby
1) export your web3 node like - export WEB3_INFURA_PROJECT_ID='eebdcf4d9e2440d8b99edc88cf04a099'
2) open `brownie console --network rinkeby`
3) accounts.from_mnemonic('your mnemonic here',10)
4) network.gas_limit(10000000)
5) network.gas_price("1 gwei")
6) run('deploy-all')

GTA Token deploy will mint tokens to first param, since distributor has not been deployed yet, we send to multsig
multiSig then needs to send to dist contract before claims will process (so tokendist has coins to send!)
'''

publish_source_ES = False; # True if you want to auto verify contract source on Etherscan
owocki_address = accounts[0] # all tokens will be minted to this address initially before being transferred accordingly 
multiSig = accounts[0] # 
timeNow = time.time()
signing_address_1 = '0x58E159e41bA3987755fF762836CC7338C0bC01ef'
merkleRoot = '0x7dc3a9718c26cf4e870fcaa7702635cb4305e15b5a8acbf2c665641c4775d8a3' # testing 50k 4/6/2021
timelock_delay = 172800 # 2 days in seconds
treasury_vesting_begin = timeNow + 120 # must be greater than block timestamp of contract deploy 
treasury_vesting_cliff = (60 * 60 * 24 * 7 * 12) + timeNow # 6 months in seconds
treasury_vesting_amount = Wei("1000 ether")
treasury_vesting_end = timeNow + (treasury_vesting_cliff*2)
cb_custody = accounts[4].address # coinbase custody address   

def main():
    # print out some relevant info about our testing env 
    loginfo()
    '''
     * @notice Construct a new GTA token
     * @param account The initial account to grant all the tokens
     * @param minter_ The account with minting ability
     * @param mintingAllowedAfter_ The timestamp after which minting may occur - Just adding 2 mins for Rinkeby
    '''
    try:
        if publish_source_ES: 
            gta = GTA.deploy(owocki_address, multiSig, int(timeNow + 120), {'from': accounts[0]}, publish_source=True)
        else: 
            gta = GTA.deploy(owocki_address, multiSig, int(timeNow + 120), {'from': accounts[0]})
        print(f'GTA address {gta.address}')
    except Exception as e:
        print(f'Error on GTA contract deploy {e}')
        sys.exit(1)
    
    # deploy the timelock contract 
    try:
        if publish_source_ES:
            tl = Timelock.deploy(multiSig, timelock_delay, {'from': accounts[0]}, publish_source=True)
        else:
            tl = Timelock.deploy(multiSig, timelock_delay, {'from': accounts[0]})
    except Exception as e:
        print(f'Error on Timelock deploy: {e}')
        sys.exit(1)
    
    # deploy TokenDistributor.sol takes 4 params, token address, signer address, timelock address, merkleRoot
    # signer address == corresponding public key (address/account) to the private key used 
    # to sign claims with Ethereum Signed Message Service  
    try:
        if publish_source_ES: 
            td = TokenDistributor.deploy(gta.address, signing_address_1, tl.address, merkleRoot, {'from': accounts[0]}, publish_source=True)
        else:
            td = TokenDistributor.deploy(gta.address, signing_address_1, tl.address, merkleRoot, {'from': accounts[0]})
    except Exception as e:
        print(f'Error on TokenDistributor contract deploy: {e}')
        sys.exit(1)
        
    # deploy the GovernorAlpha 
    try:
        if publish_source_ES:
            gov = GovernorAlpha.deploy(tl.address, gta.address, {'from' : accounts[0]}, publish_source=True)
        else:
            gov = GovernorAlpha.deploy(tl.address, gta.address, {'from' : accounts[0]})
    except Exception as e:
        print(f'Error on GovernorAlpha deploy: {e}')
        sys.exit(1)
    
    # deploy TresuryVesting.sol
    # <ContractConstructor 'TreasuryVester.constructor(address gta_, address recipient_, uint256 vestingAmount_, uint256 vestingBegin_, uint256 vestingCliff_, uint256 vestingEnd_)'> 
    try: 
        if publish_source_ES:
            tv = TreasuryVester.deploy(gta.address, tl.address, treasury_vesting_amount, treasury_vesting_begin, treasury_vesting_cliff, treasury_vesting_end, {'from' : accounts[0]}, publish_source=True)
        else: 
            tv = TreasuryVester.deploy(gta.address, tl.address, treasury_vesting_amount, treasury_vesting_begin, treasury_vesting_cliff, treasury_vesting_end, {'from' : accounts[0]})
    except Exception as e:
        print(f'Error on TreasuryVesting deploy: {e}')
        sys.exit(1)


    # allow token dist contract to set delegate addresses 
    try: 
        set_GTCToken_address(td, gta)
    except Exception as e:
        print(f'error running set_GTCToken_Address {e}')
        sys.exit(1) 
    
    ## DISTRIBUTE INITIAL TOKENS ## 
    # 1/2 to TokenDistributor 
    gta.transfer(td.address,Wei("1500000 ether"), {'from': owocki_address})
    # transfer to CB custody 
    gta.transfer(cb_custody,Wei("1000000 ether"), {'from': owocki_address})

    

def loginfo():
    '''log some helpful into to the console'''
    print(f"\nWeb3 Provider URL: {web3.provider.endpoint_uri}\n")
    for account_number in range(9):
        print(f"account #: {account_number} - {accounts[account_number]}")
    print("\n")    

'''After you run the main() you can run these manually for testing/development of a given contract''' 

# outdated, needs to updated 
def token_distributor():
    '''Base token dist testing functionality using EIP712''' 
    
    # get our contract 
    td, gta = TokenDistributor[0], GTA[0]

    # then, mint some tokens to the dist contract 
    gta.mint(td.address, Wei("1000 ether"), {'from' : accounts[0]})

    # make a claim (with checksummed addy)
    td.claimTokens(
        1, 
        "0x8e9d312F6E0B3F511bb435AC289F2Fd6cf1F9C81",
        1000000000000000, 
        "0xdcf3bbdb1d57c11a9b1e8747cc192c25aaba0ecdf7b37db9371243c778384bb1",
        "0xb69b614985b3697c8785c044612cbde07259a7bfde402b797f9c825fec1002c03551e4217ede8cd2445f32bd43916f08be824d867d63239d7245000609f468271b",
        {'from': accounts[0]}
    )

def set_GTCToken_address(td, gta):
    '''Used call this to set the GTCToken Address on the TokenDistributor contract. 
       This is needed because we have to deploy the GTCToken contract before the token distributor
    '''
    # td, gta = TokenDistributor[0], GTA[0]
    gta.setGTCDist(td.address, {'from': accounts[0]})
    print(f'GTA contract now as the the address: {gta.GTCDist()} set in for the TokenDistributor Contract')

