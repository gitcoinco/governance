import pytest

from brownie import GTA, accounts, web3, Wei, reverts
import time

# First deploy the token contract, scope 'module' says to only run this fixture once
@pytest.fixture(scope="module", autouse=True)
def gtc():
    """deploy the base GTC Token contract"""
    account = accounts[0]
    minter = accounts[0]
    mintingAllowedAfter = int(time.time()) 
    return GTA.deploy(account, minter, mintingAllowedAfter, {'from': accounts[0]})

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    """snapshot/isolate the env after deploying contract so the tests below run against a clean snapshot"""
    pass

def test_deployment(gtc):
    """Confirm that we can get the contract address"""
    assert web3.isChecksumAddress(gtc.address), "Contract address not valid! It's possible the contract did not deploy!"

def test_set_minter(gtc):
    """confirm minter address can be updated"""
    old_minter = gtc.minter()
    new_minter = accounts[5] 
    gtc.setMinter(new_minter)
    assert old_minter != new_minter, "Minter address cannot be the same address as original minter"
    assert gtc.minter() == new_minter, "Minter address could not be updated"

def test_mint(gtc): 
    """ Confirm minter_ address can mint tokens  
        - minimumTimeBetweenMints needs to be set to 1 second to on deploy
        - this will occasionally cause tests to fail even at 1 second
        - mint(address dst, uint rawAmount)  
    """
    mint_to_address = accounts[3]
    mint_info = MintInfo(gtc, mint_to_address)
    gtc.mint(mint_to_address, mint_info.max_mint_amount) 
    after_mint = gtc.balanceOf(mint_to_address)
    assert mint_info.before_mint != after_mint and mint_info.before_mint < after_mint, "Minting less than expected amount"
    assert after_mint == mint_info.max_mint_amount, "Minting amount does not check out"

    # Optional/Debug: Uncomment lines below to intentionally fail test and print values to stdout    
    # print(f'mint_cap: {mint_info.mint_cap}%, total_supply: {mint_info.total_supply}, max_mint_amount: {mint_info.max_mint_amount}, before_mint: {mint_info.before_mint}, after_mint: {after_mint}')
    # assert False, "assert fail to make PyTest print my stuff"

def test_mint_fail(gtc):
    """Here we try to mint more than we're allowed to - contract should revert the tx with no tokens minted"""
    mint_info = MintInfo(gtc, accounts[3])
    # For reference, Brownies way of handling reverted TXs 
    # https://eth-brownie.readthedocs.io/en/stable/tests-pytest-intro.html#handling-reverted-transactions
    with reverts(): 
        gtc.mint(accounts[3], (mint_info.max_mint_amount * 2)) 

    after_mint = gtc.balanceOf(accounts[3])  
    assert mint_info.before_mint == after_mint, "Minted more than mintCap"

def test_minter_permissions(gtc):
    """Here we confirm that only the minter_ address can mint tokens"""
    mint_info = MintInfo(gtc, accounts[3])
    with reverts(): 
        gtc.mint(accounts[3], mint_info.max_mint_amount, {'from': accounts[4]}) # mint(address dst, uint rawAmount)
    
    after_mint = gtc.balanceOf(accounts[3])  
    assert mint_info.before_mint == after_mint, "Non-minter minted!"

class MintInfo:
    """get releveant mint info from the contract"""
    def __init__(self, gtc, _account):
        self.minter = gtc.minter
        self.total_supply = gtc.totalSupply()
        self.mint_cap = gtc.mintCap()
        self.max_mint_amount =  self.mint_cap/100 * self.total_supply 
        self.before_mint = gtc.balanceOf(_account)
        


# Approval - test functions 
def test_approval(gtc):
    ''' conforming/standard ERC20 approval function  
        approve(address spender, uint256 rawAmount)     
    '''
    tx_from = accounts[0]
    spender = accounts[9]
    amount = Wei("100 ether")
    current_allowance = gtc.allowance(tx_from, spender) 

    # create & store pre_tx approval state 
    pre_tx_state = ApprovalState(gtc, spender, amount, tx_from, current_allowance) 
    
    gtc.approve(pre_tx_state.spender, pre_tx_state.amount) # send approval TX
    
    new_allowance = gtc.allowance(tx_from, pre_tx_state.spender)

    # confirm the account is has exactly the newly approved amount more than it previously had 
    assert (new_allowance - amount) == current_allowance,  "Approval values do not match"
    

# Transfer - test functions  
def test_transfer(gtc):
    """confirm token transfer"""
    amount = Wei("42 ether")
    tx_from = accounts[4]
    tx_to = accounts[5] 

    # create & store mint info, then mint some tokens to send 
    mint_info = MintInfo(gtc, tx_from)
    gtc.mint(tx_from, (mint_info.max_mint_amount))
    
    pre_tx_from_balance = gtc.balanceOf(tx_from)
    pre_tx_to_balance = gtc.balanceOf(tx_to)
    
    gtc.transfer(tx_to, amount, {'from': tx_from})
    
    assert gtc.balanceOf(tx_from) == pre_tx_from_balance - amount, "Sending account balance mismatch"
    assert gtc.balanceOf(tx_to) == pre_tx_to_balance + amount, "Receiving account balance mismatch"


# Delegate - Tests 
# 1) test_delegate - confirm tokens can be delegated from one address to another 
# 2) test_self_delegate - confirm an address can delegate to itself  
# 3) test_transfer_delegate - confirm delegate is updated accordingly on token transfer   
## 

def test_delegate(gtc):
    """test to confirm tokens can be delegated from A1-->A2"""
    delegator = accounts[4]
    delegatee = accounts[5] 

    # create & store mint info, then mint tokens to delegate 
    mint_info = MintInfo(gtc, delegator)
    gtc.mint(delegator, (mint_info.max_mint_amount))
    
    pre_tx_delegate_delegator = gtc.delegates(delegator)
    pre_tx_delegate_delegatee = gtc.delegates(delegatee)
    
    gtc.delegate(delegatee, {'from': delegator})

    post_tx_delegate_delegator = gtc.delegates(delegator)
    post_tx_delegate_delegatee = gtc.delegates(delegatee)
    
    assert pre_tx_delegate_delegator == "0x0000000000000000000000000000000000000000", "delegator not 0x"
    assert pre_tx_delegate_delegatee == "0x0000000000000000000000000000000000000000", "delegatee not 0x"
    assert post_tx_delegate_delegatee == "0x0000000000000000000000000000000000000000", "delegatee incorrectly set"
    assert post_tx_delegate_delegator == delegatee, "delegatee not set correctly"

def test_self_delegate(gtc):
    """ Test to confirm self-delegate A1-->A1"""
    delegator = accounts[6]
    delegatee = accounts[6] 

    # create & store mint info, then mint tokens to delegate 
    mint_info = MintInfo(gtc, delegator)
    gtc.mint(delegator, (mint_info.max_mint_amount))
    
    pre_tx_delegate_delegator = gtc.delegates(delegator)
    pre_tx_delegate_delegatee = gtc.delegates(delegatee)
    
    gtc.delegate(delegatee, {'from': delegator})

    post_tx_delegate_delegator = gtc.delegates(delegator)

    assert pre_tx_delegate_delegator == "0x0000000000000000000000000000000000000000", "delegator not 0x"
    assert pre_tx_delegate_delegatee == "0x0000000000000000000000000000000000000000", "delegatee not 0x"
    assert post_tx_delegate_delegator == delegatee, "delegatee not set correctly"

def test_transfer_delegate(gtc):
    """ confirm delegate is updated accordingly on token transfer
        1) given token holder with a delegate:  
            a) unset - 0x0000000000000000000000000000000000000000  
            b) self 
            c) other 
        2) confirm transfer behavior: 
            a) unset - should remain unset with 0x0000000000000000000000000000000000000000, no 'votes' delegated 
            b) self - 
            c) other -
    """
    a = accounts[0].address
    b = accounts[1].address
    c = accounts[2].address
    d = accounts[3].address
    e = accounts[4].address
    f = accounts[5].address
    
    # fund test accounts that don't already have tokens 
    gtc.transfer(accounts[1], Wei("1000 ether"), {'from': a})
    gtc.transfer(accounts[2], Wei("1000 ether"), {'from': a})  
    
    # create/store pre tx delegate info for accounts 'a', 'd', 'e' 
    pre_a_delegate_info = DelegateInfo(gtc, a) 

    # self delgate address 'b', then create/store pre tx delegate info 
    gtc.delegate(b, {'from': b}) # self delegate 
    pre_b_delegate_info = DelegateInfo(gtc, b)
    
    # delegate 'c' to 'd', then create/store pre tx delegate info
    gtc.delegate(d, {'from': c}) # a2 delegate to a3 
    pre_c_delegate_info = DelegateInfo(gtc, c)

    pre_d_delegate_info = DelegateInfo(gtc, d)
    pre_e_delegate_info = DelegateInfo(gtc, e)
    pre_f_delegate_info = DelegateInfo(gtc, f)
    
    # confrim delegates are correctly established 
    assert pre_a_delegate_info.delegate == "0x0000000000000000000000000000000000000000", "adddress 'a' delegate incorrectly set"
    assert pre_b_delegate_info.delegate == accounts[1], "address 'b' delegate not set to self"
    assert pre_c_delegate_info.delegate == accounts[3], "address 'c' delegate not set to 'd'"

    # acccount 'a' transfers to itself 
    gtc.transfer(a, Wei("1000 ether"), {'from': a})
    # account 'b' transfers to someone else 
    gtc.transfer(e, Wei("999 ether"), {'from': b})
    # account 'c' transfers to someone else
    gtc.transfer(f, Wei("999 ether"), {'from': c})

    post_a_delegate_info = DelegateInfo(gtc, a)
    post_b_delegate_info = DelegateInfo(gtc, b)
    post_c_delegate_info = DelegateInfo(gtc, c)
    post_d_delegate_info = DelegateInfo(gtc, d)
    post_e_delegate_info = DelegateInfo(gtc, e)
    post_f_delegate_info = DelegateInfo(gtc, f)

    # # Debug: Uncomment lines below to intentionally fail test and print values to stdout
    # print(f'pre_a_delegate_info: {vars(pre_a_delegate_info), web3.fromWei(pre_a_delegate_info.balance, "ether")}')    
    # print(f'post_a_delegate_info: {vars(post_a_delegate_info), web3.fromWei(post_a_delegate_info.balance, "ether")}\n')
  
    # print(f'pre_b_delegate_info: {vars(pre_b_delegate_info), web3.fromWei(pre_b_delegate_info.balance, "ether")}')    
    # print(f'post_b_delegate_info: {vars(post_b_delegate_info), web3.fromWei(post_b_delegate_info.balance, "ether")}\n')

    # print(f'pre_c_delegate_info: {vars(pre_c_delegate_info), web3.fromWei(pre_c_delegate_info.balance, "ether")}')    
    # print(f'post_c_delegate_info: {vars(post_c_delegate_info), web3.fromWei(post_c_delegate_info.balance, "ether")}\n')

    # print(f'pre_d_delegate_info: {vars(pre_d_delegate_info), web3.fromWei(pre_d_delegate_info.balance, "ether")}')    
    # print(f'post_d_delegate_info: {vars(post_d_delegate_info), web3.fromWei(post_d_delegate_info.balance, "ether")}\n')

    # print(f'pre_e_delegate_info: {vars(pre_e_delegate_info), web3.fromWei(pre_e_delegate_info.balance, "ether")}')    
    # print(f'post_e_delegate_info: {vars(post_e_delegate_info), web3.fromWei(post_e_delegate_info.balance, "ether")}\n')

    # print(f'pre_f_delegate_info: {vars(pre_f_delegate_info), web3.fromWei(pre_f_delegate_info.balance, "ether")}')    
    # print(f'post_f_delegate_info: {vars(post_f_delegate_info), web3.fromWei(post_f_delegate_info.balance, "ether")}\n')


    assert post_a_delegate_info.delegate == "0x0000000000000000000000000000000000000000", "Delegate 'a' address should not have changed."
    assert post_b_delegate_info.delegate == pre_b_delegate_info.address, "Self Delegate for address 'b' failed."
    assert pre_c_delegate_info.delegate == post_d_delegate_info.address, "Delegate from address 'c' to 'd' failed."

    # # testing second transaction 
    # gtc.transfer(b, Wei("10000 ether"), {'from': a})  
    # post_2_b_delegate_info = DelegateInfo(gtc, b)
    
    # print(f'pre_b_delegate_info: {vars(pre_b_delegate_info), web3.fromWei(pre_b_delegate_info.balance, "ether")}')    
    # print(f'post_b_delegate_info: {vars(post_b_delegate_info), web3.fromWei(post_b_delegate_info.balance, "ether")}')
    # print(f'post_2_b_delegate_info: {vars(post_2_b_delegate_info), web3.fromWei(post_2_b_delegate_info.balance, "ether")}\n')
    
    # assert False, "assert fail to make PyTest print my stuff"


class DelegateInfo:
    """class for storing delegate info""" 
    def __init__(self, gtc, _address):
        self.address = _address
        self.delegate = gtc.delegates(_address)
        self.balance = gtc.balanceOf(_address)
        self.votes = gtc.getCurrentVotes(_address)

"""
# Permit - test functions 
def test_permit():
    '''permit(address owner, address spender, uint rawAmount, uint deadline, uint8 v, bytes32 r, bytes32 s)
       deadline is new UNIswap feature - done with EIP712 signature  
    '''
    pass
"""

class ApprovalState:
    """create/store state of an Approval TX"""
    def __init__(self, gtc, _spender, _amount, _tx_from, _current_amount):
        self.spender = _spender
        self.amount = _amount
        self.from_address = _tx_from
        self.current_allowance = _current_amount

class TransferState:
    """snapshot of state before transaction"""
    def __init__(self, gtc, _to_address, _from_address, _amount):
        self.to_address = _to_address
        self.from_address = _from_address
        self.amount = _amount
    


