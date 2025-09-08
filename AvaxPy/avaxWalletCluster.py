import os
from web3 import Web3

AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"

w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))

print(w3.is_connected())
print(w3.eth.block_number)


avax_wallet_cluster = ("0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e")


print(w3.from_wei(avax_wallet_cluster, 'ether'))
