import time
import os
import json
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()
infura_url = os.getenv("INFURA_URL")
AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"


w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
web3 = Web3(Web3.HTTPProvider(infura_url))
#avax info
print(w3.is_connected())    
print(w3.eth.block_number)

AVAX_balance = w3.eth.get_balance("0x134A48C4Bc6c4C658bd7416A298498da146bbF0A") #Avax 
print(w3.from_wei(AVAX_balance, 'ether'))

phishing_addresses =["0x19Fa72D9D076668CeD11399BaE149F916938BD8D","0x455bF23eA7575A537b6374953FA71B5F3653272c" ] #will add addresses to watch here
print(web3.is_connected())

print(web3.eth.block_number)

processed_transactions = set()

def handle_transaction(transaction):
    value = web3.from_wei(transaction.get("value", 0), 'ether')
    print(f"Phishing address detected: {transaction['from']} -> {transaction['to']}, Value: {value} ETH")

    from_balance = 0
    to_balance = 0

    if transaction["from"] in phishing_addresses: from_balance = web3.from_wei(web3.eth.get_balance(transaction["from"]), "ether")
    print(f"Current balance of phishing sender wallet: {transaction['from']}, {web3.from_wei(from_balance, 'ether')} ETH")
    if transaction["to"] in phishing_addresses: to_balance = web3.from_wei(web3.eth.get_balance(transaction["to"]), "ether")
    print(f"Current balance of phishing receiver wallet: {transaction['to']}, {web3.from_wei(to_balance, 'ether')} ETH")
    processed_transactions.add(transaction["hash"])
block_filter = web3.eth.filter('latest')
print(block_filter)
while True:
    block_number = web3.eth.block_number
    transactions = web3.eth.get_block(block_number, full_transactions=True).transactions

    for transaction in transactions:
        handle_transaction(transaction)

    time.sleep(1)    
for address in phishing_addresses:
    balance = web3.eth.get_balance(address)
    print(f"Balance of {address}: {web3.from_wei(balance, 'ether')}")






# Smart Contract Reconsruction
abi = json.loads('[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"AddSupportedChainId","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"newBridgeRoleAddress","type":"address"}],"name":"MigrateBridgeRole","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"address","name":"feeAddress","type":"address"},{"indexed":false,"internalType":"uint256","name":"feeAmount","type":"uint256"},{"indexed":false,"internalType":"bytes32","name":"originTxId","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"originOutputIndex","type":"uint256"}],"name":"Mint","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"Unwrap","type":"event"},{"inputs":[{"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"addSupportedChainId","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burn","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"burnFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"chainIds","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newBridgeRoleAddress","type":"address"}],"name":"migrateBridgeRole","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address","name":"feeAddress","type":"address"},{"internalType":"uint256","name":"feeAmount","type":"uint256"},{"internalType":"bytes32","name":"originTxId","type":"bytes32"},{"internalType":"uint256","name":"originOutputIndex","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"uint256","name":"chainId","type":"uint256"}],"name":"unwrap","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

address = "0xC654721fBf1F374fd9FfA3385Bba2F4932A6af55" #juicy
# "0x152b9d0FdC40C096757F570A51E494bd4b943E50" #wrapped btc

contract = w3.eth.contract(address=address, abi=abi) 

print(contract)

totalSupply = contract.functions.totalSupply().call()
print(totalSupply) #wrapped btc total supply