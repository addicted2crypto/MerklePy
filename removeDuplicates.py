import csv
import json
from Crypto.Hash import keccak
from pymerkle import MerkleTree

def read_addresses_from_csv(file_path):
    """
    Reads addresses from a downloaded Snowtrace CSV file.
    Assumes the address is in the first or second column.
    Returns a set to automatically handle duplicates within the CSV.
    """
    addresses = set()
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            # Skip the header row if it exists
            header = next(reader)
            # Find the column that contains addresses
            address_column_index = -1
            if 'HolderAddress' in header:
                address_column_index = header.index('HolderAddress')
            elif 'Holder' in header:
                address_column_index = header.index('Holder')
            else: # Fallback assuming address is in the first column
                address_column_index = 0

            for row in reader:
                if address_column_index < len(row):
                    addresses.add(row[address_column_index].strip())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return addresses

def keccak256_hash(data):
    """Hashes data using the Keccak-256 algorithm."""
    k = keccak.new(digest_bits=256)
    k.update(data.encode('utf-8'))
    return k.hexdigest()

# --- Configuration ---
# Add all your CSV file paths here
csv_file_paths = [
    'erc721-holders-snowtrace.csv', # Your previously downloaded CSV
    'another-contract-holders.csv', # Another list you want to combine
    'erc20-holders.csv'             # An ERC20 holder list
]

# --- Main Script ---
all_holders = set()

# Combine addresses from all CSV files
for file_path in csv_file_paths:
    print(f"Reading addresses from {file_path}...")
    addresses_from_file = read_addresses_from_csv(file_path)
    all_holders.update(addresses_from_file)

print(f"\nTotal unique addresses found: {len(all_holders)}")

if all_holders:
    # Sort the addresses to ensure the tree is deterministic
    sorted_addresses = sorted(list(all_holders))
    
    # Hash each address with Keccak256
    hashed_addresses = [keccak256_hash(addr) for addr in sorted_addresses]
    
    # Build the Merkle tree
    merkle_tree = MerkleTree[(hashed_addresses)]
    merkle_root = merkle_tree.rootHash.hex()
    
    print(f"\nMerkle Root: {merkle_root}")
    
    # Save the hashed leaves and the root for later use
    merkle_data = {
        "root": merkle_root,
        "leaves": hashed_addresses,
        "original_addresses": sorted_addresses # Optional: store for verification
    }
    with open("combined_merkle_tree_data.json", "w") as f:
        json.dump(merkle_data, f, indent=2)
    
    print("Combined Merkle tree data saved to combined_merkle_tree_data.json")

    # --- Example: Generate a proof for one address ---
    # Pick a test address from your list
    if sorted_addresses:
        test_address = sorted_addresses[0]
        proof = merkle_tree.get_proof(keccak256_hash(test_address))
        print(f"\nExample Merkle Proof for address {test_address}: {proof.hex()}")