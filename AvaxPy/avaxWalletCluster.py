from decimal import Decimal
from web3.middleware import ExtraDataToPOAMiddleware
from web3 import Web3

# --- Connection ---
AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    raise ConnectionError("❌ Failed to connect to AVAX network")
print(f"✅ Connected to Avalanche C-Chain at block {w3.eth.block_number}")

# --- ERC20 Setup (example USDC.e) ---
TOKEN_ADDRESS = Web3.to_checksum_address("0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664")
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
     "payable": False, "stateMutability": "view", "type": "function"},
    {"anonymous": False,
     "inputs": [
         {"indexed": True, "name": "from", "type": "address"},
         {"indexed": True, "name": "to", "type": "address"},
         {"indexed": False, "name": "value", "type": "uint256"}
     ],
     "name": "Transfer", "type": "event"}
]
token = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_ABI)

# --- Wallet Cluster ---
RAW_CLUSTER = [
    "0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e",
    "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF",
    "0x139d124813afCA73D7d71354bFe46DB3dA59702B",
]
CLUSTER = set(Web3.to_checksum_address(a) for a in RAW_CLUSTER)


def get_avax_balance(wallet: str) -> Decimal:
    wei_balance = w3.eth.get_balance(wallet)
    return Decimal(w3.from_wei(wei_balance, "ether"))


def get_token_balance(wallet: str) -> Decimal:
    balance = token.functions.balanceOf(wallet).call()
    return Decimal(balance) / Decimal(1e6)  # adjust for token decimals (USDC.e = 6)


def cluster_balances():
    """Check balances across the cluster."""
    print("\n--- Cluster Balances ---")
    total_avax = Decimal(0)
    total_token = Decimal(0)
    balances = []

    for wallet in CLUSTER:
        avax_bal = get_avax_balance(wallet)
        token_bal = get_token_balance(wallet)
        balances.append((wallet, avax_bal, token_bal))
        total_avax += avax_bal
        total_token += token_bal

    # Sort by token balance
    balances.sort(key=lambda x: x[2], reverse=True)

    for w, avax, tok in balances:
        print(f"{w[:6]}...{w[-4:]} | AVAX: {avax:.3f} | Token: {tok:.2f}")

    print(f"\n💰 Total AVAX: {total_avax:.3f}, Total Token: {total_token:.2f}")
    return balances


def scan_recent_transfers(start_block: int, end_block: int):
    """Scan ERC20 transfers involving the cluster."""
    print(f"\n--- Transfers from block {start_block} to {end_block} ---")

    transfer_event = token.events.Transfer()
    logs = transfer_event.get_logs(from_block=start_block, to_block=end_block)

    trades = []
    for log in logs:
        f, t, v = log['args']['from'], log['args']['to'], log['args']['value']
        v_adj = Decimal(v) / Decimal(1e6)  # adjust decimals

        if f in CLUSTER or t in CLUSTER:
            print(f"🔄 {v_adj} tokens {f[:6]}... -> {t[:6]}...")
            trades.append((f, t, v_adj))
    return trades


if __name__ == "__main__":
    # Balances
    balances = cluster_balances()

    # Transfers in last 500 blocks
    latest_block = w3.eth.block_number
    scan_recent_transfers(latest_block - 500, latest_block)

# from decimal import Decimal, getcontext
# from web3.middleware import ExtraDataToPOAMiddleware
# import time
# from web3 import Web3
# import os


# AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
# w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
# w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# if not w3.is_connected():
#     raise ConnectionError("Failed to connect to AVAX network")

# print(f"✅ Connected to Avalanche C-Chain at block {w3.eth.block_number}")

# token_address = Web3.to_checksum_address("0xC654721fBf1F374fd9FfA3385Bba2F4932A6af55")
# erc20_abi = [{"anonymous": False, "inputs":[
#     {"indexed":True,"name":"from","type":"address"},
#     {"indexed":True,"name":"to","type":"address"},
#     {"indexed":False,"name":"value","type":"uint256"}],
#     "name":"Transfer","type":"event"}],
 
# token = w3.eth.contract(address=token_address, abi=erc20_abi)
# logs = w3.eth.get_logs({
#     "fromBlock": start_block,
#     "toBlock": end_block,   
#     "address": token_address,
# })
# for log in logs:
#     decoded = token.events.Transfer().process_log(log)
#     from_addr = decoded['args']['from']
#     to_addr = decoded['args']['to']
#     value = decoded['args']['value']
# if from_addr in cluster_wallet_set or to_addr in cluster_wallet_set:
#         print(f"ERC20 transfer {value} tokens from {from_addr} -> {to_addr}")
#     if decoded['args']['from'] in cluster_wallet_set and decoded['args']['to'] in cluster_wallet_set:
#        print(f"ERC-20 transfer {decoded['arg']['value']} from {decoded['args']['from']} to {decoded['args']['from']} to {decoded['args']['to']}")
# if not w3.is_connected():
#     print("Failed to connect to AVAX network")
#     exit()
# print(f"Connected to Avalanche C-chain. Current block: {w3.eth.block_number}\n")

# raw_avax_wallet_cluster = ["0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e", "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF","0x139d124813afCA73D7d71354bFe46DB3dA59702B","0xa3cda653810350b18d3956aaf6b369cf68933073","0xF2bd61e529c83722d54d9CD5298037256890fb19","0x49DCf8E78c2a6118aB09C9a771E2Aa0B50648780"]

# # Will when you modify the output addresses
# #   displayed_address = f"{original_wallet_address[:5]}...{original_wallet_address[-3:]}"
# #     print(f"{displayed_address}: {wallet_info['balance (AVAX)']} AVAX")

# avax_wallet_cluster = [Web3.to_checksum_address(addr) for addr in raw_avax_wallet_cluster]
# cluster_wallet_set = set(avax_wallet_cluster)

# total_avax_balance = Decimal(0)
# wallet_balances = []

# print("--- Checking Wallet Balances ---\n")

# for wallet in avax_wallet_cluster:
#     try:
#         # Get balance in wei and convert to AVAX
#         balaace_in_avax = w3.eth.get_balance(wallet)

#         balance_in_avax = w3.from_wei(balaace_in_avax, 'ether')
#         total_avax_balance += Decimal(balance_in_avax)
#         wallet_balances.append({
#            "wallet": wallet,
#             "balance (AVAX)": f"{balance_in_avax:.18f}"
#       })
#     except Exception as e:
#      print(f"Error fetching balance for {wallet}: {e}")
# for wallet in wallet_balances: 
#     print(f"{wallet['wallet']}: {wallet['balance (AVAX)']} AVAX")
#     print(f"\nTotal AVAX balance across cluster: {total_avax_balance:.18f} AVAX\n")

#     transfer_count = 0
#     found_transfers = False
# start_block = w3.eth.block_number - 200
# end_block = w3.eth.block_number

# print(f"--- Caculating AVAX transfers between cluster wallets from block {start_block} to {end_block} ---\n")

# for block_num in range(start_block, end_block + 1):
#     try: 
#         block = w3.eth.get_block(block_num, full_transactions=True)
        
#         if block.transactions:
#             block_has_cluster_transfer = False
#             for tx in block.transactions:
#              tx_from = tx.get('from')
#              tx_to = tx.get('to')

#              if tx_from in cluster_wallet_set and tx_to in cluster_wallet_set:
#                 if tx.get('input') == '0x':
#                     transfer_count += 1
#                     print(f"Transfer found in block {block_num}: {tx_from} -> {tx_to}")

#             if not block_has_cluster_transfer:
#                 print(f"No trasfers between cluster wallets found in blocks {start_block} to {end_block}.\n")

#         else:
#             print(f"No transactions in block {block_num}.")  

#     except Exception as e:
#         print(f"Error processing block {block_num}: {e}")


#     time.sleep(.05)
# if not found_transfers:
#     print(f"No transfers between cluster wallets found in blocks {start_block} to {end_block}.\n")

# else:    
#     print(f"\nTotal AVAX transfers within the cluster in the last 2000 block: {transfer_count}")
# 
#         