import os
# from python_dotenv import load_dotenv
# load_dotenv()

from web3 import Web3
infura_url ="NEVER_SHARE_YOUR_INFURA_URL"
# os.getenv("INFURA_URL")

web3 = Web3(Web3.HTTPProvider(infura_url))
print(web3.is_connected())

print(web3.eth.block_number)

balance = web3.eth.get_balance("0x616767179c5305a89f13348134C681061Cf0bA9e")
print(web3.from_wei(balance, 'ether')) #even avax is called ether thats cool