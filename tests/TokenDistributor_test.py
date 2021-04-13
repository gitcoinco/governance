import pytest
from brownie import GTA, TokenDistributor, Timelock, accounts, web3, Wei, reverts
import time
import requests
import json
import hmac
import hashlib
import binascii

v1_api_uri = 'https://esms-audit.grasshopper.surf/v1/sign_claim'
dev_hmac_key = 'E49756B4C8FAB4E48222A3E7F3B97CC3' 
signing_address = '0x58E159e41bA3987755fF762836CC7338C0bC01ef' # dev/testing
# merkleRoot = '0x7dc3a9718c26cf4e870fcaa7702635cb4305e15b5a8acbf2c665641c4775d8a3' # testing 50k 4/6/2021
merkleRoot = '0x4a719904edbd7da1b3be6b34f9543dc6e1f1a633027f7cbecc6fc21ece6e00b4' # new 50k sample dist 4/13/21
timelock_delay = 172800 # 2 days in seconds

@pytest.fixture(scope="module")
def token():
    """ 
        Deploy the token contract w/three params:
        multiSig - The initial account to grant all the tokens
        minter_ - The account with minting ability 
        mintingAllowedAfter_ - The timestamp after which minting may occur (unix time)
    """ 
    multiSig = accounts[0]
    minter = accounts[0]
    mintingAllowedAfter = int(time.time()) 
    return GTA.deploy(multiSig, minter, mintingAllowedAfter, {'from': accounts[0]})

@pytest.fixture(scope="module")
def tl():
    """
        TimeLock Contract - Only needed here in the TD test as all GTC not claimed 
        can be swept to TimeLock after 6 months
    """
    multiSig = accounts[0] 
    return Timelock.deploy(multiSig, timelock_delay, {'from': accounts[0]})

@pytest.fixture(scope="module")
def td(token, tl):
    """ 
        TokenDistributor.sol constructor params:
        <constructor(address _token, address _signer, address _timeLock, bytes32 _merkleRoot)> 
        _token - ERC20 token that will be distributed  
        _signer - pub-key/address of the account used to sign token claims
        _timeLock - Address for the TimeLock contract
        _merkleRoot - Merkle Root of the distribution tree 
    """
    _token = token.address
    return TokenDistributor.deploy(_token, signing_address, tl.address, merkleRoot, {'from': accounts[0]})

@pytest.fixture(scope="module")
def set_dist_address(token, td):
    """Token needs to know the tokenDist contract address for approved setting of delegate with different source address"""
    return token.setGTCDist(td.address, {'from': accounts[0]}) 

@pytest.fixture(scope="module")
def seed(token, td):
    """Tansfer seed tokens to the distributor contract"""
    return token.transfer(td.address, Wei('1000000 ether'), {'from': accounts[0]})

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    """snapshot/isolate the env after above fixtures so the tests below run against a clean snapshot"""
    pass

def test_valid_contract_address(token, td):
    """generic test to confirm we have a working contract address"""
    assert web3.isChecksumAddress(token.address) and web3.isChecksumAddress(token.address), "One or more contract addresses could not be validated. Please confirm contracts we're deployed as expected."
 
def test_dist_address_on_token(token, td):
    token.setGTCDist(td.address, {'from': accounts[0]})
    assert token.GTCDist() != '0x0000000000000000000000000000000000000000', "Token doesn't have the TokenDistribution contract address set appropriately for delegation on dist."

def test_token_claim(token,td,seed, set_dist_address): 
    '''
       Submit claim to ESMS use respone to make on-chain claim.
       Test that a valid claim will transfer tokens to user  
    '''
  
    claim_address = accounts[0].address
    delegate_address = accounts[1].address
    user_id = 1
    total_claim = Wei("1 ether")
    
    token_claim = TokenClaim(user_id, claim_address, delegate_address, total_claim) 
    
    # get use balance before claim 
    balance_before = token.balanceOf(claim_address)

    # place token claim 
    td.claimTokens(token_claim.user_id, token_claim.user_address, token_claim.user_amount, token_claim.delegate_address, token_claim.hash, token_claim.sig, token_claim.proof, token_claim.leaf)

    # get use balance before claim 
    balance_after = token.balanceOf(claim_address)

    print(f'balance_before: {balance_before}')
    print(f'balance_after: {balance_after}')

    assert balance_before < balance_after, "Tokens do not appear to have been sent"
    # uncomment to debug and print details to stdout 
    # assert False, "You intentionally triggered execpetion to print debug info to stdout"

"""
def test_claim_gas_cost(token, td, seed):
    '''Submit claim to EMSS, use response to make claim
       repeat successful claims N times to see if/when gas costs rise 10% 
    '''
    total_claims = 10
    claim = 1
    while claim < total_claims:
        # default is only 10 accounts, we run add() to generate new accounts
        if claim > 9:
            accounts.add()
        claim_address = accounts[claim].address
        user_id = claim
        claim_amount = 1000000000000000000
        delegate_address = accounts[claim].address
       
        # get balance before  
        balance_before = token.balanceOf(claim_address)
        # craft claim object 
        token_claim = TokenClaim(user_id, claim_address, delegate_address, claim_amount) 
        # make claim
        claim_tx = td.claimTokens(token_claim.user_id, token_claim.user_address, token_claim.user_amount, token_claim.delegate_address, token_claim.hash, token_claim.sig, token_claim.proof, token_claim.leaf)
        # get use balance before claim 
        balance_after = token.balanceOf(claim_address)

        # print(f'balance_before: {balance_before}')
        # print(f'balance_after: {balance_after}')
        print(f'gas_used: {claim_tx.gas_used}')
        print(f'web3 block number: {web3.eth.blockNumber}')
        assert balance_before < balance_after, "Tokens do not appear to have been sent"
        
        if claim == 1:
            original_gas_used = claim_tx.gas_used
            gas_upper_limit = original_gas_used + (original_gas_used/10)
     
        print(f'gas upper limit: {gas_upper_limit}')
        # trigger if gas price jump more than 10% from original 
        assert claim_tx.gas_used < original_gas_used + (original_gas_used/10), "10% gas price increase"
        
        claim += 1
    
    # uncomment to debug and print details to stdout 
    assert False, "You intentionally triggered execpetion to print debug info to stdout"
"""
"""
def generate_claim(_user_id, _user_address, _user_amount):
    ''' 1) POST to the ESMS & get a valid signed claim
        2) call TokenClaim & confirm token distribution   
    '''
    post_data = {}
    post_data['user_id'] = _user_id
    post_data['user_address'] = _user_address
    post_data['user_amount'] = _user_amount 

    computed_hash = create_sha256_signature(dev_hmac_key, json.dumps(post_data))

    header = { 
        "X-GITCOIN-SIG" : computed_hash,
        "content-type": "application/json",
    }
    try:
        r = requests.post(v1_api_uri, data=json.dumps(post_data), headers=header)
    except:
        print('failed to get claim!')
        return False 

    # uncomment for debug/verbose 
    # print(f'generate_claim: {r.json()}')

    return r.json()
"""

class TokenClaim:

  def __init__(self, _user_id, _user_address, _delegate_address, _total_claim):
      ''' push claim objects emitted from Ethereum Message
          Signing Service into an on-chain claimable object 
      '''
      raw_claim = generate_claim(_user_id, _user_address, _delegate_address, _total_claim)
     
      self.user_id = _user_id
      self.user_address = _user_address 
      self.user_amount = _total_claim
      self.delegate_address = _delegate_address
      self.hash = raw_claim["eth_signed_message_hash_hex"]
      self.sig = raw_claim["eth_signed_signature_hex"]
      self.leaf = raw_claim["leaf"]
      self.proof = raw_claim["proof"]


def generate_claim(user_id, user_address, delegate_address, total_claim):
    '''Generate claim'''
    """ sample response from signed message server 
    {'user_address': '0xb6b7c3C5Bc1c76c9E3447e37C395c6a7863E10Fb', 'delegate_address': '0xb6b7c3C5Bc1c76c9E3447e37C395c6a7863E10Fb', 'user_id': 42, 'user_amount': '1', 'eth_signed_message_hash_hex': '0x6657cd98194e8f3ab90f6b005c374e921fcc092121574b58844b34586e975b8d', 'eth_signed_signature_hex': '0xf4c06d3d9b1a3c1882aae62fd33ce2b39f583100b81afa3b4a835d8fcd4f1344549eeb9ca65d3575ecd67921125adffe698aa57e8609d53668016443964b97a21b', 'leaf': '0x008d03279d9a4f44cf36924a31c880c95faf3177f4fa7726733c7ac1089755ce', 'proof': ['0x0de35c2593959552ded8255d817deab3a7f4cc203fd76361463a8e42adc829d8', '0x804ff4c42606f6508b261a21116983ba3684e79d62b3099bea7252cba3f49d80', '0xd69c4295cb03542d4f3e4d25104acd4e3a2045578a60a6e84bd6f726c3d3e118', '0x3606b8ab60140d5f7235b473f8f1767d99406aa148789ec7792d2d2fb1443c3c', '0x73e043f3f3c01654bbba6511ecb45e0394f2c6b8744158a2e33b362bcc9aef79', '0x5c3b7d51d089ae42355ab7e7ae7bef54bb7866fac67f21f2ab4ad724053ea70d', '0x7411b24f7e4c91c3fa592fb47aff92569a513844f15ccb2a198103410307df3c', '0x6cd22fa40073b504ad8ac40b75ca7e2bce035a43bf6af2b19d313b653442c0d0', '0xd7c878d0a90bb9356bbdf9e2aac75078a7cc6e7c10d83944104b17bcdfe4bb43', '0xc16714991d1bfa87d8bd12abad00e3b444f2f19be626bab064192464c952595a', '0x2c8a544490facafefeef8ce9d77230409f0d5e78b270f37e6a589defc861ac47', '0x62edaa1d4f30f01e4173d1973fa61978ad44698ea177a0a4ce01c1ed69cb67c4', '0xb8e40e8bf355f8e27ce49889c333acaceac5b688cb280c564b075f896d5ed431', '0xf4bdaa77202fd68933fe94c3514f29938f4ba3539d211f76e7a245eced220874', '0x94f98f7dad31685991775c4240667d549dc68af6acc65372ea8ea09e7a3fbc72', '0xa2df046c9788e3a7bf21b75f0c6429b784f15bdaa0cf4119dd5fbb6485b006b0']}
    """    
    post_data_to_emss = {}
    post_data_to_emss['user_id'] = user_id
    post_data_to_emss['user_address'] = user_address
    post_data_to_emss['delegate_address'] = delegate_address
    post_data_to_emss['user_amount'] = total_claim

    # print(f'POST DATA FOR ESMS: {json.dumps(post_data_to_emss)}')
    # create a hash of post data
    try:                 
        sig = create_sha256_signature(dev_hmac_key, json.dumps(post_data_to_emss))
    except: 
        print('Error creating hash of POST data for ESMS')

    header = { 
        "X-GITCOIN-SIG" : sig,
        "content-type": "application/json",
    }

    # POST relevant user data to micro service that returns signed transation data for the user broadcast
    try: 
        emss_response = requests.post(v1_api_uri, data=json.dumps(post_data_to_emss), headers=header)
        emss_response_content = emss_response.content
        emss_response.raise_for_status() # raise exception on error 
    except requests.exceptions.ConnectionError:
        print('TD TEST: ConnectionError while connecting to EMSS!')
     
    except requests.exceptions.Timeout:
        # Maybe set up for a retry
        print('TD TEST: Timeout while connecting to EMSS!')
 
    except requests.exceptions.TooManyRedirects:
        print('TD TEST: Too many redirects while connecting to EMSS!')
     
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print(f'TD TEST:  Error posting to EMSS - {e}')

    # pass returned values from eth signer microservice
    # ESMS returns bytes object of json. so, we decode it
    full_response = json.loads( emss_response_content.decode('utf-8'))

    # print(f'GTC Token Distributor - ESMS response: {full_response}')
    return full_response 
    

def create_sha256_signature(key, message):
    '''Given key & message, returns HMAC digest of the message'''
    try:
        byte_key = binascii.unhexlify(key)
        message = message.encode()
        return hmac.new(byte_key, message, hashlib.sha256).hexdigest().upper()
    except Exception as e:
        logger.error(f'GTC Distributor - Error Hashing Message: {e}')
        return False 


