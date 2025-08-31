from typing import List, Dict
import eth_hash.auto as hash_lib

def validate_address(address: str) -> bool:
    """
    Validate if the provided address is a valid string.
    
    Args:
        address (str): The address to be validated.
    
    Returns:
        bool: True if the address is valid, False otherwise.
    """
    return isinstance(address, str)

class MerkleTree:
    def __init__(self, addresses: List[str]):
        """
        Initialize a Merkle tree with the provided addresses.
        
        Args:
            addresses (List[str]): A list of addresses to be included in the Merkle tree.
        
        Raises:
            ValueError: If any address is invalid.
        """
        self.addresses = self._validate_and_sort_addresses(addresses)
        self.leaves = [self._hash_address(addr) for addr in self.addresses]
        self.tree = self._build_tree(self.leaves)

    def _validate_and_sort_addresses(self, addresses: List[str]) -> List[str]:
        """
        Validate all input addresses and return a sorted list of unique addresses.
        
        Args:
            addresses (List[str]): A list of addresses to be validated and sorted.
        
        Returns:
            List[str]: A list of valid, unique, and sorted addresses.
        """
        valid_addresses = [addr for addr in addresses if validate_address(addr)]
        return sorted(list(set(valid_addresses)))

    def _hash_address(self, address: str) -> bytes:
        """
        Hash an address using keccak hashing.
        
        Args:
            address (str): The address to be hashed.
        
        Returns:
            bytes: The hashed address.
        """
        try:
            return hash_lib.keccak(address.encode('utf-8'))
        except Exception as e:
            raise ValueError("Failed to hash address: {}".format(str(e)))

    def _build_tree(self, leaves: List[bytes]) -> List[List[bytes]]:
        """
        Recursively build the Merkle tree from the provided leaves.
        
        Args:
            leaves (List[bytes]): A list of hashed addresses to be used as leaves in the Merkle tree.
        
        Returns:
            List[List[bytes]]: The constructed Merkle tree, represented as a list of levels where each level is a list of hashes.
        """
        tree = [leaves]
        current_level = leaves
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                combined_hash = self._combine_hashes(left, right)
                next_level.append(combined_hash)
            
            tree.append(next_level)
            current_level = next_level
        
        return tree

    def _combine_hashes(self, left: bytes, right: bytes) -> bytes:
        """
        Combine two hashes into a single hash while maintaining consistency in the order of hashing.
        
        Args:
            left (bytes): The first hash to be combined.
            right (bytes): The second hash to be combined.
        
        Returns:
            bytes: The combined hash.
        """
        if left <= right:
            return hash_lib.keccak(left + right)
        else:
            return hash_lib.keccak(right + left)

    def get_root(self) -> str:
        """
        Get the root of the Merkle tree as a hexadecimal string.
        
        Returns:
            str: The Merkle tree's root in hexadecimal format.
        """
        if not self.tree:
            raise ValueError("Merkle tree is empty")
        
        return self.tree[-1][0].hex()

    def get_proof(self, address: str) -> List[str]:
        """
        Get the Merkle proof for a given address.
        
        Args:
            address (str): The address for which to generate the proof.
        
        Returns:
            List[str]: A list of hexadecimal strings representing the Merkle proof for the provided address.
        """
        if address not in self.addresses:
            return []
        
        leaf_hash = self._hash_address(address)
        leaf_index = self.addresses.index(address)
        proof = []
        
        for level in self.tree[:-1]:
            is_right = leaf_index % 2
            sibling_index = leaf_index - 1 if is_right else leaf_index + 1
            
            if sibling_index < len(level):
                proof.append(level[sibling_index].hex())
            
            leaf_index //= 2
        
        return proof

def generate_whitelist_data(projects: Dict[str, List[str]]) -> (str, Dict[str, List[str]], List[str]):
    """
    Combine addresses from projects, generate the Merkle tree, and return the root and proofs.
    
    Args:
        projects (Dict[str, List[str]]): A dictionary where keys are project names and values are lists of addresses.
    
    Returns:
        tuple: A tuple containing the Merkle tree's root as a hexadecimal string, a dictionary of proofs for each address, and a list of unique addresses.
    """
    all_addresses = [address for project in projects.values() for address in project]
    merkle_tree = MerkleTree(all_addresses)
    root = merkle_tree.get_root()
    
    proofs = {}
    for address in merkle_tree.addresses:
        proofs[address] = merkle_tree.get_proof(address)
        
    return root, proofs, merkle_tree.addresses

def verify_proof_off_chain(root: str, address: str, proof: List[str]) -> bool:
    """
    Verify a Merkle proof for an address against the provided root.
    
    Args:
        root (str): The expected root of the Merkle tree as a hexadecimal string.
        address (str): The address to verify.
        proof (List[str]): A list of hexadecimal strings representing the Merkle proof.
    
    Returns:
        bool: True if the proof verifies correctly, False otherwise.
    """
    if not proof:
        return False
    
    computed_hash = hash_lib.keccak(address.encode('utf-8'))
    for proof_hash_hex in proof:
        proof_hash = bytes.fromhex(proof_hash_hex)
        
        combined_hash = MerkleTree._combine_hashes(computed_hash, proof_hash)
        computed_hash = combined_hash
        
    return computed_hash.hex() == root

if __name__ == '__main__':
    projects = {
        "Project A": ["address1", "address2", "address3"],
        "Project B": ["address2", "address4", "address5"],
        "Project C": ["address6", "address7", "address8"],
    }
    
    root_node, address_proofs, unique_addresses = generate_whitelist_data(projects)
    
    print("--- Off-chain Merkle Tree Data ---")
    print(f"Merkle Tree Root (for smart contract): {root_node}\n")
    
    print("Example Merkle Proofs:")
    address_to_check = "address1"
    proof_for_addr1 = address_proofs.get(address_to_check)
    print(f"Proof for {address_to_check}: {proof_for_addr1}")
    
    address_to_check_not_whitelisted = "address99"
    proof_for_addr99 = address_proofs.get(address_to_check_not_whitelisted, [])
    print(f"Proof for {address_to_check_not_whitelisted}: {proof_for_addr99}")
    
    print("\n--- Off-chain Verification Simulation ---")
    
    is_whitelisted = verify_proof_off_chain(root_node, "address1", address_proofs["address1"])
    print(f"Is address1 whitelisted? {is_whitelisted}")
    
    is_whitelisted = verify_proof_off_chain(root_node, "address99", proof_for_addr99)
    print(f"Is address99 whitelisted? {is_whitelisted}")

