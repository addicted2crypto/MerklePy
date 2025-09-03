import os
# from python_dotenv import load_dotenv
# load_dotenv()

from web3 import Web3
infura_url ="NEVER PUT YOUR INFURA URL IN A PUBLIC REPO"
# os.getenv("INFURA_URL")
AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc" 
w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
web3 = Web3(Web3.HTTPProvider(infura_url))
print(web3.is_connected())

print(web3.eth.block_number)

balance = web3.eth.get_balance("0x455bF23eA7575A537b6374953FA71B5F3653272c") #FAKE PHISHING BULLSHIT ASSHOLE
print(web3.from_wei(balance, 'ether')) #even avax is called ether thats cool
# print(web3.eth.get_proof('latest', [0], True))

#avax info
print(w3.is_connected())    
print(w3.eth.block_number)

AVAX_balance = w3.eth.get_balance("0x134A48C4Bc6c4C658bd7416A298498da146bbF0A") #Avax 
print(w3.from_wei(AVAX_balance, 'ether'))