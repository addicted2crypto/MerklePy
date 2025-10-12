import requests
from web3 import Web3
import json
from datetime import datetime
import time

class DeployerTokenTracker:
    def __init__(self, rpc_url, avax_scan_api_key=None, blacklist_file='wallet_blacklist.json'):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.avax_scan_api_key = avax_scan_api_key
        self.deployer_addresses = set()
        self.blacklist_file = blacklist_file
        self.wallet_blacklist = self.load_blacklist()

    def load_blacklist(self):
        """Load blacklist from JSON file"""
        try:
            with open(self.blacklist_file, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            return {
                'wallets': [],
                'metadata': {}
            }

    def save_blacklist(self):
        """Save blacklist to JSON file"""
        try:
            with open(self.blacklist_file, 'w') as f:
                json.dump(self.wallet_blacklist, f, indent=4)
            print(f"Blacklist saved to {self.blacklist_file}")
        except Exception as e:
            print(f"Error saving blacklist: {e}")

    def add_to_blacklist(self, wallet_address, reason, evidence):
        """Add a wallet to the blacklist with metadata"""
        wallet_address = wallet_address.lower()

        if wallet_address not in [w['address'] for w in self.wallet_blacklist['wallets']]:
            entry = {
                'address': wallet_address,
                'reason': reason,
                'evidence': evidence,
                'timestamp': datetime.now().isoformat(),
                'flagged_by': 'arenaShitBagTracker'
            }
            self.wallet_blacklist['wallets'].append(entry)
            print(f"[BLACKLISTED] {wallet_address}: {reason}")
            self.save_blacklist()
            return True
        else:
            print(f"Wallet {wallet_address} already in blacklist")
            return False

    def is_blacklisted(self, wallet_address):
        """Check if a wallet is in the blacklist"""
        wallet_address = wallet_address.lower()
        return wallet_address in [w['address'] for w in self.wallet_blacklist['wallets']]

    def get_blacklist_count(self):
        """Get total number of blacklisted wallets"""
        return len(self.wallet_blacklist['wallets'])
        
    def add_deployer_addresses(self, addresses):
        """Add addresses to monitor for deployment patterns"""
        self.deployer_addresses.update(addresses)
        
    def check_self_purchase(self, deployer_address, token_contract):
        """Check if deployer purchased the token they created"""
        try:
            # Get transaction history for deployer address
            transactions = self.get_address_transactions(deployer_address)
            
            # Filter for token purchases (buy actions)
            buy_transactions = []
            for tx in transactions:
                if self.is_token_purchase(tx, token_contract):
                    buy_transactions.append(tx)
                    
            return len(buy_transactions) > 0
            
        except Exception as e:
            print(f"Error checking self purchase for {deployer_address}: {e}")
            return False
            
    def check_token_transfer_pattern(self, deployer_address, token_contract):
        """Logic to identify 1 transfer then dump on mfers, will  also add
        2 transfer then dump on mfers, and 3 transfer then dump on mfers
        and a call to stages and spaces held during sales events"""
        try:
            
            transfers = self.get_token_transfers(deployer_address, token_contract)
            
            suspicious_patterns = []
            
            for transfer in transfers:
                # Check if this is a transfer to a new wallet
                if self.is_single_step_transfer(transfer):
                    # Check if recipient wallet later sells the tokens
                    recipient = transfer['to']
                    sale_info = self.check_wallet_sales(recipient, token_contract)
                    
                    if sale_info:
                        profit_info = self.calculate_transfer_profit(transfer, sale_info)
                        suspicious_patterns.append({
                            'transfer': transfer,
                            'sale_info': sale_info,
                            'profit': profit_info,
                            'flag': 'single_step_transfer_with_sale'
                        })
                        
            return suspicious_patterns
            
        except Exception as e:
            print(f"Error checking transfer pattern for {deployer_address}: {e}")
            return []
            
    def is_single_step_transfer(self, transfer):
        """Check if transfer is a direct 1-step transfer"""
        # This would analyze transaction structure to identify direct transfers
        # Could check for simple transfer vs complex multi-step operations
        return True  # Placeholder logic
        
    def check_wallet_sales(self, wallet_address, token_contract):
        """Check if wallet has sold the tokens"""
        try:
            # Get transactions where wallet sold tokens
            transactions = self.get_address_transactions(wallet_address)
            for tx in transactions:
                if self.is_token_sale(tx, token_contract):
                    return tx
            return None
        except Exception:
            return None
            
    def calculate_transfer_profit(self, transfer, sale_transaction):
        """Calculate profit from transfer pattern"""
        try:
            # Get token amount transferred
            transfer_amount = self.get_token_amount(transfer)
            
            # Get sale proceeds
            sale_proceeds = self.get_sale_proceeds(sale_transaction)
            
            # Calculate profit in AVAX terms
            profit = sale_proceeds - transfer_amount  # Simplified logic
            
            return {
                'amount_transferred': transfer_amount,
                'sale_proceeds': sale_proceeds,
                'profit': profit,
                'profit_in_avax': self.convert_to_avax(profit)
            }
        except Exception as e:
            print(f"Error calculating profit: {e}")
            return None
            
    def analyze_deployer_selling_pattern(self, deployer_address, token_contract):
        """
        Analyze if deployer sold into others' buy volume
        Returns evidence dict if suspicious pattern found
        """
        try:
            print(f"\n[ANALYZING] Deployer: {deployer_address}")
            print(f"[ANALYZING] Token: {token_contract}")

            # Get token deployment info
            deployment_info = self.get_token_deployment(deployer_address, token_contract)
            if not deployment_info:
                return None

            # Get all token transactions
            token_txs = self.get_token_transactions(token_contract)

            # Separate buy and sell transactions
            buy_txs = []
            deployer_sell_txs = []

            for tx in token_txs:
                if self.is_buy_transaction(tx, token_contract):
                    buy_txs.append(tx)
                elif self.is_sell_transaction(tx, token_contract, deployer_address):
                    deployer_sell_txs.append(tx)

            # Check if deployer sold during or right after others bought
            suspicious_sells = []
            for sell_tx in deployer_sell_txs:
                # Find buy volume around the time of this sell
                nearby_buys = self.find_nearby_buys(sell_tx, buy_txs, time_window=300)  # 5 min window

                if nearby_buys:
                    total_buy_volume = sum(self.get_tx_value(tx) for tx in nearby_buys)
                    sell_value = self.get_tx_value(sell_tx)

                    suspicious_sells.append({
                        'sell_tx': sell_tx['hash'],
                        'sell_amount': sell_value,
                        'nearby_buy_count': len(nearby_buys),
                        'total_buy_volume': total_buy_volume,
                        'timestamp': sell_tx.get('timestamp', 'unknown')
                    })

            # Flag if deployer consistently sold into buy volume
            if len(suspicious_sells) >= 2:  # At least 2 instances
                evidence = {
                    'deployer': deployer_address,
                    'token': token_contract,
                    'deployment_time': deployment_info.get('timestamp', 'unknown'),
                    'suspicious_sell_count': len(suspicious_sells),
                    'total_deployer_sells': len(deployer_sell_txs),
                    'suspicious_sells': suspicious_sells,
                    'pattern': 'sold_into_buy_volume'
                }

                # Add to blacklist
                reason = f"Token deployer sold into buy volume {len(suspicious_sells)} times"
                self.add_to_blacklist(deployer_address, reason, evidence)

                return evidence

            return None

        except Exception as e:
            print(f"Error analyzing deployer selling pattern: {e}")
            return None

    def find_nearby_buys(self, sell_tx, buy_txs, time_window=300):
        """Find buy transactions near a sell transaction (within time_window seconds)"""
        sell_time = sell_tx.get('timestamp', 0)
        nearby = []

        for buy_tx in buy_txs:
            buy_time = buy_tx.get('timestamp', 0)
            time_diff = abs(sell_time - buy_time)

            if time_diff <= time_window and buy_time <= sell_time:
                nearby.append(buy_tx)

        return nearby

    def get_all_deployed_contracts(self, deployer_address):
        """Get all contracts deployed by an address"""
        try:
            # Get all transactions from deployer
            txs = self.get_address_transactions(deployer_address)

            deployed_contracts = []
            for tx in txs:
                # Contract creation has empty 'to' field
                if tx.get('to', '') == '' and tx.get('contractAddress', ''):
                    deployed_contracts.append({
                        'contract': tx['contractAddress'],
                        'tx_hash': tx['hash'],
                        'timestamp': tx.get('timeStamp', '0'),
                        'block': tx.get('blockNumber', '0')
                    })

            return deployed_contracts
        except Exception as e:
            print(f"Error getting deployed contracts: {e}")
            return []

    def calculate_token_profit(self, deployer_address, token_contract):
        """Calculate total profit from a single token"""
        try:
            # Get all token transactions
            token_txs = self.get_token_transfers(deployer_address, token_contract)

            total_received_avax = 0
            total_spent_avax = 0

            for tx in token_txs:
                value_wei = int(tx.get('value', 0))
                value_avax = self.w3.from_wei(value_wei, 'ether')

                # If deployer is sender, they're selling (receiving AVAX)
                if tx.get('from', '').lower() == deployer_address.lower():
                    # This is a token transfer out - need to find corresponding AVAX received
                    # For now, estimate based on transaction value
                    total_received_avax += float(value_avax)

                # If deployer is receiver, they're buying (spending AVAX)
                elif tx.get('to', '').lower() == deployer_address.lower():
                    total_spent_avax += float(value_avax)

            profit = total_received_avax - total_spent_avax
            return {
                'token': token_contract,
                'total_received': total_received_avax,
                'total_spent': total_spent_avax,
                'profit': profit
            }
        except Exception as e:
            print(f"Error calculating profit for token {token_contract}: {e}")
            return None

    def analyze_serial_deployer(self, wallet_address, min_tokens=50, min_profit=10):
        """
        Analyze if wallet is a serial deployer who profits from multiple tokens

        Args:
            wallet_address: Address to analyze
            min_tokens: Minimum number of tokens to be flagged (default 50)
            min_profit: Minimum total profit in AVAX to be flagged (default 10)
        """
        try:
            print(f"\n{'='*60}")
            print(f"[ANALYZING SERIAL DEPLOYER] {wallet_address}")
            print(f"{'='*60}")

            # Get all contracts deployed by this address
            deployed_contracts = self.get_all_deployed_contracts(wallet_address)
            num_deployed = len(deployed_contracts)

            print(f"[INFO] Total contracts deployed: {num_deployed}")

            if num_deployed < min_tokens:
                print(f"[PASS] Below threshold ({min_tokens} tokens)")
                return None

            # Calculate profit from each token
            total_profit = 0
            profitable_tokens = []

            print(f"[INFO] Analyzing profit from {num_deployed} tokens...")

            for i, contract_info in enumerate(deployed_contracts[:100]):  # Limit to first 100 for API limits
                contract = contract_info['contract']
                print(f"  Analyzing token {i+1}/{min(num_deployed, 100)}: {contract[:10]}...")

                profit_info = self.calculate_token_profit(wallet_address, contract)

                if profit_info and profit_info['profit'] > 0:
                    total_profit += profit_info['profit']
                    profitable_tokens.append(profit_info)

                # Rate limiting
                time.sleep(0.2)

            print(f"\n[RESULTS]")
            print(f"  Tokens deployed: {num_deployed}")
            print(f"  Profitable tokens: {len(profitable_tokens)}")
            print(f"  Total profit: {total_profit:.4f} AVAX")

            # Check if meets blacklist criteria
            if num_deployed >= min_tokens and total_profit >= min_profit:
                evidence = {
                    'deployer': wallet_address,
                    'total_contracts_deployed': num_deployed,
                    'profitable_tokens': len(profitable_tokens),
                    'total_profit_avax': total_profit,
                    'sample_profitable_tokens': profitable_tokens[:10],  # Save first 10 as evidence
                    'pattern': 'serial_deployer_with_profit',
                    'threshold_tokens': min_tokens,
                    'threshold_profit': min_profit
                }

                reason = f"Serial deployer: {num_deployed} tokens deployed, {total_profit:.2f} AVAX profit"
                self.add_to_blacklist(wallet_address, reason, evidence)

                print(f"\n[BLACKLISTED] {wallet_address}")
                print(f"  Reason: {reason}")

                return evidence
            else:
                print(f"[PASS] Does not meet criteria:")
                if num_deployed < min_tokens:
                    print(f"  - Tokens: {num_deployed} < {min_tokens}")
                if total_profit < min_profit:
                    print(f"  - Profit: {total_profit:.2f} < {min_profit} AVAX")
                return None

        except Exception as e:
            print(f"Error analyzing serial deployer: {e}")
            import traceback
            traceback.print_exc()
            return None

    def batch_analyze_deployers(self, wallet_addresses, min_tokens=50, min_profit=10):
        """
        Analyze multiple wallet addresses for serial deployment patterns

        Args:
            wallet_addresses: List of addresses to analyze
            min_tokens: Minimum tokens to flag
            min_profit: Minimum profit in AVAX to flag
        """
        results = []

        print(f"\n{'='*60}")
        print(f"BATCH ANALYSIS - {len(wallet_addresses)} wallets")
        print(f"Criteria: {min_tokens}+ tokens, {min_profit}+ AVAX profit")
        print(f"{'='*60}")

        for i, wallet in enumerate(wallet_addresses, 1):
            print(f"\n[{i}/{len(wallet_addresses)}] Analyzing wallet: {wallet}")

            result = self.analyze_serial_deployer(wallet, min_tokens, min_profit)

            if result:
                results.append({
                    'wallet': wallet,
                    'flagged': True,
                    'evidence': result
                })
            else:
                results.append({
                    'wallet': wallet,
                    'flagged': False
                })

            # Rate limiting between wallets
            time.sleep(1)

        # Summary
        flagged_count = sum(1 for r in results if r['flagged'])
        print(f"\n{'='*60}")
        print(f"BATCH ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"Total analyzed: {len(wallet_addresses)}")
        print(f"Flagged: {flagged_count}")
        print(f"Passed: {len(wallet_addresses) - flagged_count}")
        print(f"{'='*60}")

        return results

    def track_token_deployer(self, token_contract):
        """
        Main method to track a token's deployer and check for rug patterns
        """
        try:
            # Get token deployer
            deployer = self.get_token_deployer(token_contract)
            if not deployer:
                print(f"Could not find deployer for token {token_contract}")
                return None

            print(f"\n[TRACKING] Token deployer: {deployer}")

            # Check if already blacklisted
            if self.is_blacklisted(deployer):
                print(f"[WARNING] Deployer {deployer} is already blacklisted!")
                return None

            # Analyze selling patterns
            evidence = self.analyze_deployer_selling_pattern(deployer, token_contract)

            if evidence:
                print(f"\n[ALERT] Suspicious pattern detected!")
                print(f"Deployer added to blacklist: {deployer}")
                return evidence
            else:
                print(f"No suspicious patterns found for {deployer}")
                return None

        except Exception as e:
            print(f"Error tracking token deployer: {e}")
            return None

    def get_address_transactions(self, address):
        """Get transaction history for an address using Snowtrace API"""
        if not self.avax_scan_api_key:
            print("Warning: No API key provided, using limited access")
            return []

        try:
            url = f"https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'desc',
                'apikey': self.avax_scan_api_key
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            return []
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []

    def get_token_transactions(self, token_contract):
        """Get all transactions for a specific token"""
        if not self.avax_scan_api_key:
            print("Warning: No API key provided")
            return []

        try:
            url = f"https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_contract,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.avax_scan_api_key
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            return []
        except Exception as e:
            print(f"Error fetching token transactions: {e}")
            return []

    def get_token_deployer(self, token_contract):
        """Get the deployer address of a token contract"""
        try:
            # Get contract creation transaction
            url = f"https://api.snowtrace.io/api"
            params = {
                'module': 'contract',
                'action': 'getcontractcreation',
                'contractaddresses': token_contract,
                'apikey': self.avax_scan_api_key
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1' and len(data['result']) > 0:
                return data['result'][0]['contractCreator']

            return None
        except Exception as e:
            print(f"Error getting token deployer: {e}")
            return None

    def get_token_deployment(self, deployer_address, token_contract):
        """Get deployment information for a token"""
        try:
            url = f"https://api.snowtrace.io/api"
            params = {
                'module': 'contract',
                'action': 'getcontractcreation',
                'contractaddresses': token_contract,
                'apikey': self.avax_scan_api_key
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1' and len(data['result']) > 0:
                result = data['result'][0]
                return {
                    'deployer': result['contractCreator'],
                    'tx_hash': result['txHash'],
                    'timestamp': 'check_tx_for_timestamp'
                }
            return None
        except Exception as e:
            print(f"Error getting deployment info: {e}")
            return None

    def is_buy_transaction(self, tx, token_contract):
        """Check if transaction is a buy (someone purchasing the token)"""
        # This assumes a swap where AVAX is sent and tokens are received
        # You may need to adjust based on DEX contract
        try:
            # Check if this is a transfer TO someone (receiving tokens)
            if tx.get('to', '').lower() != token_contract.lower():
                return True
            return False
        except Exception:
            return False

    def is_sell_transaction(self, tx, token_contract, seller_address):
        """Check if transaction is a sell by specific address"""
        try:
            # Check if seller is sending tokens
            if tx.get('from', '').lower() == seller_address.lower():
                # And tokens are being sent (likely to DEX)
                return True
            return False
        except Exception:
            return False

    def get_tx_value(self, tx):
        """Get transaction value in AVAX"""
        try:
            value = int(tx.get('value', 0))
            return self.w3.from_wei(value, 'ether')
        except Exception:
            return 0

    def get_token_transfers(self, address, token_contract):
        """Get token transfer events for an address"""
        if not self.avax_scan_api_key:
            return []

        try:
            url = f"https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_contract,
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.avax_scan_api_key
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            return []
        except Exception as e:
            print(f"Error fetching token transfers: {e}")
            return []

    def is_token_purchase(self, tx, token_contract):
        """Check if transaction is a token purchase"""
        # Placeholder - implement based on DEX logic
        return False

    def is_token_sale(self, tx, token_contract):
        """Check if transaction is a token sale"""
        # Placeholder - implement based on DEX logic
        return False

    def get_token_amount(self, transfer):
        """Get token amount from transfer"""
        try:
            return int(transfer.get('value', 0))
        except Exception:
            return 0

    def get_sale_proceeds(self, sale_transaction):
        """Get proceeds from a sale transaction"""
        try:
            return int(sale_transaction.get('value', 0))
        except Exception:
            return 0

    def convert_to_avax(self, amount):
        """Convert amount to AVAX"""
        try:
            return self.w3.from_wei(amount, 'ether')
        except Exception:
            return 0

    def export_blacklist(self, filename=None):
        """Export blacklist to CSV for easy sharing"""
        if filename is None:
            filename = f"blacklist_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            import csv
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['address', 'reason', 'timestamp', 'pattern']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for wallet in self.wallet_blacklist['wallets']:
                    writer.writerow({
                        'address': wallet['address'],
                        'reason': wallet['reason'],
                        'timestamp': wallet['timestamp'],
                        'pattern': wallet['evidence'].get('pattern', 'unknown')
                    })

            print(f"Blacklist exported to {filename}")
        except Exception as e:
            print(f"Error exporting blacklist: {e}")


# Example usage
if __name__ == "__main__":
    # Initialize tracker
    RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
    API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Get from snowtrace.io

    tracker = DeployerTokenTracker(RPC_URL, API_KEY)

    print("=" * 60)
    print("ARENA SHITBAG TRACKER - Wallet Blacklist System")
    print("=" * 60)

    # Method 1: Track a specific token deployer for selling into buy volume
    # token_address = "0x..."  # Replace with actual token address
    # result = tracker.track_token_deployer(token_address)

    # Method 2: Analyze wallets for serial deployment patterns (50+ tokens, profit)
    # Replace these with your 3 test wallet addresses
    test_wallets = [
        "0xWALLET_ADDRESS_1",  # Replace with actual address
        "0xWALLET_ADDRESS_2",  # Replace with actual address
        "0xWALLET_ADDRESS_3",  # Replace with actual address
    ]

    # Batch analyze for serial deployers
    # Criteria: 50+ tokens deployed AND 10+ AVAX profit
    results = tracker.batch_analyze_deployers(
        test_wallets,
        min_tokens=50,      # Minimum tokens to blacklist
        min_profit=10       # Minimum AVAX profit to blacklist
    )

    # Method 3: Analyze single wallet for serial deployment
    # single_wallet = "0xWALLET_ADDRESS"
    # tracker.analyze_serial_deployer(single_wallet, min_tokens=50, min_profit=10)

    # Print blacklist stats
    print(f"\n{'=' * 60}")
    print(f"FINAL BLACKLIST STATS")
    print(f"{'=' * 60}")
    print(f"Total wallets in blacklist: {tracker.get_blacklist_count()}")

    # Show blacklisted wallets
    if tracker.wallet_blacklist['wallets']:
        print(f"\nBlacklisted Wallets:")
        for entry in tracker.wallet_blacklist['wallets']:
            print(f"\n  Address: {entry['address']}")
            print(f"  Reason: {entry['reason']}")
            print(f"  Flagged: {entry['timestamp']}")

    print(f"\n{'=' * 60}")

    # Export blacklist to CSV
    tracker.export_blacklist()