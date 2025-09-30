import logging
from decimal import Decimal
from typing import Tuple, Optional
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


# --- Config ---
AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
TOKEN_ADDRESS = "0xC654721fBf1F374fd9FfA3385Bba2F4932A6af55"

RAW_CLUSTER = [
    "0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e",
    "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF",
    "0x139d124813afCA73D7d71354bFe46DB3dA59702B",
    "0xa3cda653810350b18d3956aaf6b369cf68933073",
    "0xF2bd61e529c83722d54d9CD5298037256890fb19",
    "0x6dccb7CA18553c5664e8fc31672d0377ADf910b1",
    "0x49dcf8e78c2a6118ab09c9a771e2aa0b50648780",
    "0x239f8241fd512938DaB29C707196fA1Abff3D22C",
    "0xa648FF555Cc5423e7EF0dE425fEB8B6c4155815b",
    "0xF8d4dD1854bB60950305Af12Fd72B7a547734b12",
]
DEXSCREENER_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/{}"


# --- Setup logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# --- Web3 ---
w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    logger.error("Failed to connect to AVAX RPC at %s", AVAX_RPC_URL)
    raise SystemExit(1)

TOKEN_ADDRESS = Web3.to_checksum_address(TOKEN_ADDRESS)
CLUSTER = [Web3.to_checksum_address(a) for a in RAW_CLUSTER]


# --- ERC20 Minimal ABI ---
ERC20_MIN_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]
token_contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_MIN_ABI)


# --- Helpers ---
def get_token_decimals(contract) -> int:
    try:
        return int(contract.functions.decimals().call())
    except Exception as e:
        logger.warning("No decimals() in token, defaulting to 18: %s", e)
        return 18


def get_avax_balance(wallet: str) -> Decimal:
    wei = w3.eth.get_balance(wallet)
    return Decimal(w3.from_wei(wei, "ether"))


def get_token_balance(contract, wallet: str, decimals: int) -> Decimal:
    raw = contract.functions.balanceOf(wallet).call()
    return Decimal(raw) / Decimal(10**decimals)


def get_token_price_in_avax_dexscreener(token_addr: str) -> Optional[Decimal]:
    try:
        resp = requests.get(DEXSCREENER_TOKEN_URL.format(token_addr), timeout=10)
        resp.raise_for_status()
        pairs = resp.json().get("pairs") or []
        for p in pairs:
            if "priceNative" in p:
                return Decimal(str(p["priceNative"]))
        return None
    except Exception as e:
        logger.warning("Dexscreener price fetch failed: %s", e)
        return None


def find_contract_creation(token_addr: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    token_addr = Web3.to_checksum_address(token_addr)
    latest = w3.eth.block_number
    if not w3.eth.get_code(token_addr):
        return None, None, None

    # Binary search for creation block
    low, high = 0, latest
    while low < high:
        mid = (low + high) // 2
        if w3.eth.get_code(token_addr, block_identifier=mid):
            high = mid
        else:
            low = mid + 1
    creation_block = low

    # Find deployer in that block
    block = w3.eth.get_block(creation_block, full_transactions=True)
    for tx in block.transactions:
        if tx.get("to") is None:
            receipt = w3.eth.get_transaction_receipt(tx.hash)
            if (
                receipt.contractAddress
                and Web3.to_checksum_address(receipt.contractAddress) == token_addr
            ):
                return Web3.to_checksum_address(tx["from"]), receipt.transactionHash.hex(), creation_block
    return None, None, creation_block


# --- Interactive wallet adding ---
def add_wallets_interactively():
    print("\n--- Add Wallets ---")
    print("Paste one or more wallet addresses separated by commas.")
    print("Leave blank and press Enter when done.\n")

    while True:
        user_input = input("➕ Add wallets: ").strip()
        if not user_input:
            break

        new_wallets = [w.strip() for w in user_input.split(",") if w.strip()]
        for w in new_wallets:
            try:
                cs = Web3.to_checksum_address(w)
                if cs not in CLUSTER:
                    CLUSTER.append(cs)
                    print(f"✅ Added {cs}")
                else:
                    print(f"⚠️ Already in cluster: {cs}")
            except Exception as e:
                print(f"❌ Invalid address {w}: {e}")

    print("\nCurrent cluster wallets:")
    for w in CLUSTER:
        print(" ", w)


# --- Cluster balance reporting ---
def cluster_report():
    decimals = get_token_decimals(token_contract)
    price_native = get_token_price_in_avax_dexscreener(TOKEN_ADDRESS)
    deployer, tx_hash, creation_block = find_contract_creation(TOKEN_ADDRESS)

    total_avax, total_token = Decimal(0), Decimal(0)

    print("\n--- Cluster Balances ---")
    balances = []
    for wallet in CLUSTER:
        avax = get_avax_balance(wallet)
        token = get_token_balance(token_contract, wallet, decimals)
        balances.append((wallet, avax, token))
        total_avax += avax
        total_token += token

    balances.sort(key=lambda x: x[2], reverse=True)
    for w, avax, tok in balances:
        print(f"{w[:6]}...{w[-4:]} | AVAX: {avax:.2f} | Token: {tok:.2f}")

    print(f"\n💰 Totals: AVAX= {total_avax:.2f}  ERC20 Tokens= {total_token:.2f}")
    if price_native:
        token_value = total_token * price_native
        print(f"💵 Token value ≈ {token_value:.2f} AVAX (at {price_native} AVAX per token)")

    if deployer:
        print(f"\n📜 Token deployer: {deployer}")
        print(f"   Tx: {tx_hash}")
        print(f"   Block #: {creation_block}")


# --- Cluster transaction links (ERC20 + AVAX transfers) ---
def cluster_transactions(start_block: int, end_block: int):
    print("\n--- Cluster Transaction Links ---")
    interactions = {}

    transfer_event = token_contract.events.Transfer
    max_chunk = 200  # avoid RPC limit

    # ERC20 transfers in chunks
    for chunk_start in range(start_block, end_block + 1, max_chunk):
        chunk_end = min(chunk_start + max_chunk - 1, end_block)
        try:
            logs = transfer_event().get_logs(from_block=chunk_start, to_block=chunk_end)
        except Exception as e:
            logger.warning("Log fetch failed for %s-%s: %s", chunk_start, chunk_end, e)
            continue

        for log in logs:
            from_addr = log["args"]["from"]
            to_addr = log["args"]["to"]
            if from_addr in CLUSTER and to_addr in CLUSTER:
                key = tuple(sorted([from_addr, to_addr]))
                interactions[key] = interactions.get(key, 0) + 1

    # Native AVAX transfers in chunks
    for chunk_start in range(start_block, end_block + 1, max_chunk):
        chunk_end = min(chunk_start + max_chunk - 1, end_block)
        for block_num in range(chunk_start, chunk_end + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                if tx["from"] in CLUSTER and tx["to"] in CLUSTER:
                    key = tuple(sorted([tx["from"], tx["to"]]))
                    interactions[key] = interactions.get(key, 0) + 1

    if not interactions:
        print("📊 No transfers between cluster wallets in this block range.")
        return

    total_transfers = sum(interactions.values())
    for (a, b), count in interactions.items():
        prob = count / total_transfers
        print(f"{a[:6]}...{a[-4:]} ↔ {b[:6]}...{b[-4:]} : {prob:.2%} likelihood")

-
if __name__ == "__main__":
    add_wallets_interactively()
    cluster_report()
    latest_block = w3.eth.block_number
    cluster_transactions(latest_block - 2000, latest_block)  # last ~2k blocks
