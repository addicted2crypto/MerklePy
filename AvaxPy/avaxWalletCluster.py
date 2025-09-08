from web3 import Web3

AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"

w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))

print(w3.is_connected())
