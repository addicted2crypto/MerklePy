import os
from web3 import Web3

AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"

w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))

print(w3.is_connected())
print(w3.eth.block_number)

wallet_balances = []
avax_wallet_cluster = ["0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e", "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF"]

for wallet in avax_wallet_cluster:
    balaace_in_avax = w3.eth.get_balance(wallet)

    balance_in_avax = w3.from_wei(balaace_in_avax, 'ether')
    wallet_balances.append({
        "wallet": wallet,
        "balance (AVAX)": balance_in_avax
    })
print("Wallet Balances:")
for wallet in wallet_balances: 
    print(wallet)
