"""
Quick test script to debug factory token detection
"""
import requests
from web3 import Web3

# Configuration
RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with your actual API key
TEST_WALLET = "0x0eead2DafcF656671c3ADec00c1b7EDf968338C0"
FACTORY_ADDRESSES = [
    "0x2196E106Af476f57618373ec028924767c758464",
    "0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e",
    "0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c"
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))

print(f"Testing factory detection for wallet: {TEST_WALLET}\n")
print(f"{'='*70}")

# Step 1: Get wallet transactions
print("\n[STEP 1] Fetching wallet transactions...")
url = "https://api.snowtrace.io/api"
params = {
    'module': 'account',
    'action': 'txlist',
    'address': TEST_WALLET,
    'startblock': 0,
    'endblock': 99999999,
    'sort': 'desc',
    'apikey': API_KEY
}

response = requests.get(url, params=params, timeout=15)
data = response.json()

if data['status'] != '1':
    print(f"❌ ERROR: {data.get('message', 'Unknown error')}")
    exit(1)

transactions = data['result']
print(f"✓ Found {len(transactions)} total transactions")

# Step 2: Filter for factory calls
print("\n[STEP 2] Filtering for factory contract calls...")
factory_txs = []
for tx in transactions:
    to_addr = tx.get('to', '').lower()
    for factory in FACTORY_ADDRESSES:
        if to_addr == factory.lower():
            factory_txs.append(tx)
            break

print(f"✓ Found {len(factory_txs)} factory calls")

if len(factory_txs) == 0:
    print("\n❌ No factory calls found!")
    print("\nShowing first 5 transactions to debug:")
    for i, tx in enumerate(transactions[:5]):
        print(f"\nTx {i+1}:")
        print(f"  Hash: {tx['hash']}")
        print(f"  To: {tx.get('to', 'None')}")
        print(f"  From: {tx.get('from', 'None')}")
    exit(1)

print(f"\nShowing first 3 factory calls:")
for i, tx in enumerate(factory_txs[:3]):
    print(f"\n  Factory Call {i+1}:")
    print(f"    Hash: {tx['hash']}")
    print(f"    To (Factory): {tx['to']}")
    print(f"    Block: {tx['blockNumber']}")

# Step 3: Get internal transactions
print(f"\n[STEP 3] Fetching internal transactions...")
params = {
    'module': 'account',
    'action': 'txlistinternal',
    'address': TEST_WALLET,
    'startblock': 0,
    'endblock': 99999999,
    'sort': 'asc',
    'apikey': API_KEY
}

response = requests.get(url, params=params, timeout=15)
data = response.json()

if data['status'] != '1':
    print(f"❌ ERROR: {data.get('message', 'Could not fetch internal txs')}")
    internal_txs = []
else:
    internal_txs = data['result']
    print(f"✓ Found {len(internal_txs)} internal transactions")

# Step 4: Match internal txs to factory calls
print(f"\n[STEP 4] Matching internal transactions to factory calls...")

if len(internal_txs) > 0:
    print(f"\nShowing first 3 internal transactions:")
    for i, itx in enumerate(internal_txs[:3]):
        print(f"\n  Internal Tx {i+1}:")
        print(f"    Hash: {itx.get('hash', 'N/A')}")
        print(f"    From: {itx.get('from', 'N/A')}")
        print(f"    To: {itx.get('to', 'N/A')}")
        print(f"    ContractAddress: {itx.get('contractAddress', 'N/A')}")
        print(f"    Type: {itx.get('type', 'N/A')}")
else:
    print("  ⚠ No internal transactions found via API")

# Step 5: Try receipt/log parsing for first factory call
print(f"\n[STEP 5] Analyzing receipt/logs for first factory call...")
if len(factory_txs) > 0:
    test_tx = factory_txs[0]
    tx_hash = test_tx['hash']

    print(f"\nAnalyzing tx: {tx_hash}")

    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)

        print(f"  Receipt status: {receipt.status}")
        print(f"  Logs count: {len(receipt.logs)}")

        if len(receipt.logs) > 0:
            print(f"\n  Analyzing logs for token address...")
            for i, log in enumerate(receipt.logs[:5]):
                print(f"\n    Log {i+1}:")
                print(f"      Address (emitter): {log.address}")
                print(f"      Topics count: {len(log.topics)}")

                if len(log.topics) > 0:
                    print(f"      Topic[0] (event sig): {log.topics[0].hex()}")

                if len(log.topics) > 1:
                    print(f"      Topic[1]: {log.topics[1].hex()}")
                    # Try to extract address from topic[1]
                    potential_addr = log.topics[1].hex()
                    if len(potential_addr) >= 66:
                        addr_hex = '0x' + potential_addr[-40:]
                        try:
                            addr_checksum = Web3.to_checksum_address(addr_hex)
                            print(f"      → Extracted address: {addr_checksum}")

                            # Check if it's a contract
                            code = w3.eth.get_code(addr_checksum)
                            print(f"      → Has contract code: {len(code) > 0} ({len(code)} bytes)")

                            if len(code) > 0:
                                print(f"\n      ✅ FOUND TOKEN CONTRACT: {addr_checksum}")
                        except Exception as e:
                            print(f"      → Invalid address: {e}")

    except Exception as e:
        print(f"  ❌ Error getting receipt: {e}")

print(f"\n{'='*70}")
print("Test complete!")
