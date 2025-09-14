from decimal import Decimal, getcontext
from web3.middleware import ExtraDataToPOAMiddleware
import time
from web3 import Web3
import os

AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"

w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
print(w3.is_connected())
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
if not w3.is_connected():
    print("Failed to connect to AVAX network")
    exit()
print(f"Connected to Avalanche C-chain. Current block: {w3.eth.block_number}\n")

raw_avax_wallet_cluster = ["0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e", "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF","0x139d124813afCA73D7d71354bFe46DB3dA59702B","0xa3cda653810350b18d3956aaf6b369cf68933073","0xF2bd61e529c83722d54d9CD5298037256890fb19","0x49DCf8E78c2a6118aB09C9a771E2Aa0B50648780"]

# Will when you modify the output addresses
#   displayed_address = f"{original_wallet_address[:5]}...{original_wallet_address[-3:]}"
#     print(f"{displayed_address}: {wallet_info['balance (AVAX)']} AVAX")

avax_wallet_cluster = [Web3.to_checksum_address(addr) for addr in raw_avax_wallet_cluster]
cluster_wallet_set = set(avax_wallet_cluster)

total_avax_balance = Decimal(0)
wallet_balances = []

print("--- Checking Wallet Balances ---\n")

for wallet in avax_wallet_cluster:
    try:
        balaace_in_avax = w3.eth.get_balance(wallet)

        balance_in_avax = w3.from_wei(balaace_in_avax, 'ether')
        total_avax_balance += Decimal(balance_in_avax)
        wallet_balances.append({
           "wallet": wallet,
            "balance (AVAX)": f"{balance_in_avax:.18f}"
      })
    except Exception as e:
     print(f"Error fetching balance for {wallet}: {e}")
for wallet in wallet_balances: 
    print(f"{wallet['wallet']}: {wallet['balance (AVAX)']} AVAX")
    print(f"\nTotal AVAX balance across cluster: {total_avax_balance:.18f} AVAX\n")

    transfer_count = 0
    found_transfers = False
start_block = w3.eth.block_number - 200
end_block = w3.eth.block_number

print(f"--- Caculating AVAX transfers between cluster wallets from block {start_block} to {end_block} ---\n")

for block_num in range(start_block, end_block + 1):
    try: 
        block = w3.eth.get_block(block_num, full_transactions=True)
        
        if block.transactions:
            block_has_cluster_transfer = False
            for tx in block.transactions:
             tx_from = tx.get('from')
             tx_to = tx.get('to')

             if tx_from in cluster_wallet_set and tx_to in cluster_wallet_set:
                if tx_get('input') == '0x':
                    transfer_count += 1
                    print(f"Transfer found in block {block_num}: {tx_from} -> {tx_to}")

            if not block_has_cluster_transfer:
                print(f"No trasfers between cluster wallets found in blocks {start_block} to {end_block}.\n")

        else:
            print(f"No transactions in block {block_num}.")  

    except Exception as e:
        print(f"Error processing block {block_num}: {e}")


    time.sleep(.5)
if not found_transfers:
    print(f"No transfers between cluster wallets found in blocks {start_block} to {end_block}.\n")

else:    
    print(f"\nTotal AVAX transfers within the cluster in the last 2000 block: {transfer_count}")        