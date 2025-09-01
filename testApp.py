import os
from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
infura_url = os.getenv("INFURA_URL")

web3 = Web3(Web3.HTTPProvider(infura_url))
print(web3.is_connected())

print(web3.eth.block_number)

balance = web3.eth.get_balance("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
print(web3.from_wei(balance, 'ether'))