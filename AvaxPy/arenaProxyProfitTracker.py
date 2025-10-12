import requests
from web3 import Web3
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Set
import time

class ArenaProxyProfitTracker:
    """
    Track token deployments and profits through the Arena proxy deployer
    Focuses on calculating AVAX profits from buy-then-sell strategies
    Includes USD conversion and secondary wallet transfer tracking
    """

    def __init__(self, rpc_url, avax_scan_api_key, arena_proxy_address):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.api_key = avax_scan_api_key
        self.arena_proxy = Web3.to_checksum_address(arena_proxy_address)

        # Arena factory contract addresses that create tokens via internal transactions
        self.factory_addresses = [
            Web3.to_checksum_address("0x2196E106Af476f57618373ec028924767c758464"),
            Web3.to_checksum_address("0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e"),
            Web3.to_checksum_address(arena_proxy_address)  # Original proxy
        ]

        self.avax_usd_price_cache = {}  # Cache AVAX prices by timestamp
        self.results = {
            'wallets': {},
            'summary': {},
            'timestamp': datetime.now().isoformat()
        }

    def get_wallet_transactions(self, wallet_address: str, start_block: int = 0) -> List[Dict]:
        """Get all transactions for a wallet address"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': wallet_address,
                'startblock': start_block,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.api_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            else:
                print(f"API Error for {wallet_address}: {data.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"Error fetching transactions for {wallet_address}: {e}")
            return []

    def get_internal_transactions(self, wallet_address: str) -> List[Dict]:
        """Get internal transactions (contract calls) for a wallet"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'txlistinternal',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.api_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            return []
        except Exception as e:
            print(f"Error fetching internal transactions: {e}")
            return []

    def get_avax_usd_price(self, timestamp: int) -> float:
        """
        Get AVAX/USD price at a specific timestamp
        Uses CoinGecko API with caching to avoid rate limits
        """
        # Use daily granularity for caching (timestamp rounded to day)
        day_timestamp = (timestamp // 86400) * 86400

        if day_timestamp in self.avax_usd_price_cache:
            return self.avax_usd_price_cache[day_timestamp]

        try:
            # Convert to date format for CoinGecko
            date_str = datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y')

            url = "https://api.coingecko.com/api/v3/coins/avalanche-2/history"
            params = {
                'date': date_str,
                'localization': 'false'
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'market_data' in data and 'current_price' in data['market_data']:
                price = data['market_data']['current_price'].get('usd', 0)
                self.avax_usd_price_cache[day_timestamp] = price
                return price
            else:
                # Fallback: try current price
                return self.get_current_avax_price()

        except Exception as e:
            print(f"    [WARNING] Could not fetch AVAX price for {date_str}: {e}")
            # Return current price as fallback
            return self.get_current_avax_price()

    def get_current_avax_price(self) -> float:
        """Get current AVAX/USD price"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'avalanche-2',
                'vs_currencies': 'usd'
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            return data.get('avalanche-2', {}).get('usd', 0)
        except Exception as e:
            print(f"    [WARNING] Could not fetch current AVAX price: {e}")
            return 30.0  # Fallback approximate price

    def get_avax_balance(self, wallet_address: str) -> float:
        """
        Get current AVAX balance for a wallet address
        Returns balance in AVAX (not Wei)
        """
        try:
            wallet_address = Web3.to_checksum_address(wallet_address)
            balance_wei = self.w3.eth.get_balance(wallet_address)
            balance_avax = float(self.w3.from_wei(balance_wei, 'ether'))
            return balance_avax
        except Exception as e:
            print(f"    [WARNING] Could not fetch AVAX balance for {wallet_address}: {e}")
            return 0.0

    def find_secondary_wallets(self, deployer_address: str, token_contract: str) -> Set[str]:
        """
        Find secondary wallets that received token transfers from the deployer
        These could be used to hide dumps
        """
        print(f"    [TRACKING] Looking for secondary wallets...")

        secondary_wallets = set()
        token_transfers = self.get_token_transfers(deployer_address, token_contract)

        for transfer in token_transfers:
            from_addr = transfer['from'].lower()
            to_addr = transfer['to'].lower()
            deployer_lower = deployer_address.lower()

            # If deployer sent tokens to another wallet (not a contract/DEX)
            if from_addr == deployer_lower and to_addr != deployer_lower:
                # Check if recipient has low transaction count (likely secondary wallet)
                recipient_txs = self.get_wallet_transactions(to_addr)

                # If wallet has relatively few transactions, likely a secondary wallet
                if len(recipient_txs) < 100:  # Adjustable threshold
                    secondary_wallets.add(Web3.to_checksum_address(to_addr))
                    print(f"      → Found potential secondary: {to_addr[:10]}... ({len(recipient_txs)} txs)")

        return secondary_wallets

    def find_factory_deployed_tokens(self, wallet_address: str) -> List[Dict]:
        """
        Find tokens deployed via factory contracts (internal transactions)
        This catches tokens created through factory.createToken() calls
        """
        print(f"\n[FACTORY SCAN] Looking for factory-deployed tokens...")

        deployed_tokens = []
        transactions = self.get_wallet_transactions(wallet_address)

        print(f"[INFO] Scanning {len(transactions)} transactions for factory calls...")

        # Get ALL internal transactions once (more efficient)
        print(f"[INFO] Fetching internal transactions...")
        all_internal_txs = self.get_internal_transactions(wallet_address)
        print(f"[INFO] Found {len(all_internal_txs)} internal transactions")

        factory_calls = 0
        for tx in transactions:
            to_addr = tx.get('to', '')
            if not to_addr:
                continue

            to_addr_lower = to_addr.lower()

            # Check if transaction calls one of our known factory addresses
            if to_addr_lower in [f.lower() for f in self.factory_addresses]:
                factory_calls += 1

                try:
                    tx_hash = tx['hash']

                    # Method 1: Check internal transactions for contract creations
                    found_in_internal = False
                    for itx in all_internal_txs:
                        # Match by transaction hash
                        if itx.get('hash', '').lower() == tx_hash.lower():
                            # Check if this internal tx created a contract
                            # Internal tx has 'to' == '' or 'contractAddress' field
                            contract_addr = itx.get('contractAddress', '')

                            # Sometimes contract creation is indicated by empty 'to' field
                            if not contract_addr and itx.get('to', '') == '':
                                # This might be a contract creation, but address not in this field
                                continue

                            if contract_addr and contract_addr != '' and contract_addr != '0x0000000000000000000000000000000000000000':
                                contract_addr = Web3.to_checksum_address(contract_addr)

                                deployed_tokens.append({
                                    'contract_address': contract_addr,
                                    'tx_hash': tx_hash,
                                    'block_number': int(tx['blockNumber']),
                                    'timestamp': int(tx['timeStamp']),
                                    'datetime': datetime.fromtimestamp(int(tx['timeStamp'])).isoformat(),
                                    'gas_used': int(tx['gasUsed']),
                                    'gas_price': int(tx['gasPrice']),
                                    'deployment_type': 'factory',
                                    'factory_address': to_addr
                                })

                                print(f"  ✓ Found factory token: {contract_addr[:10]}... (Block: {tx['blockNumber']})")
                                found_in_internal = True
                                break

                    # Method 2: If not found in internal txs, try parsing logs/receipt
                    if not found_in_internal:
                        try:
                            receipt = self.w3.eth.get_transaction_receipt(tx_hash)

                            # Check receipt logs for contract creation events
                            # Many factory contracts emit a TokenCreated event with the new token address
                            if receipt and receipt.logs:
                                for log in receipt.logs:
                                    # Token address is often in the first topic or in the data
                                    # For factory contracts, the created token address might be in topics[1]
                                    if len(log.topics) > 1:
                                        # Try to extract address from topics
                                        potential_addr = log.topics[1].hex()
                                        # Address is the last 20 bytes (40 hex chars) of the topic
                                        if len(potential_addr) >= 66:  # 0x + 64 chars
                                            addr_hex = '0x' + potential_addr[-40:]
                                            try:
                                                contract_addr = Web3.to_checksum_address(addr_hex)

                                                # Verify this looks like a valid contract by checking it has code
                                                if len(self.w3.eth.get_code(contract_addr)) > 0:
                                                    deployed_tokens.append({
                                                        'contract_address': contract_addr,
                                                        'tx_hash': tx_hash,
                                                        'block_number': int(tx['blockNumber']),
                                                        'timestamp': int(tx['timeStamp']),
                                                        'datetime': datetime.fromtimestamp(int(tx['timeStamp'])).isoformat(),
                                                        'gas_used': int(tx['gasUsed']),
                                                        'gas_price': int(tx['gasPrice']),
                                                        'deployment_type': 'factory',
                                                        'factory_address': to_addr
                                                    })

                                                    print(f"  ✓ Found factory token (via logs): {contract_addr[:10]}... (Block: {tx['blockNumber']})")
                                                    break
                                            except Exception:
                                                continue
                        except Exception as e:
                            print(f"  [DEBUG] Could not parse receipt for {tx_hash[:10]}...: {e}")

                except Exception as e:
                    print(f"  ✗ Error processing factory tx {tx.get('hash', 'unknown')[:10]}...: {e}")
                    continue

                # Rate limiting
                time.sleep(0.05)

        print(f"[FACTORY] Found {factory_calls} factory calls, {len(deployed_tokens)} tokens created\n")
        return deployed_tokens

    def find_deployed_tokens(self, wallet_address: str) -> List[Dict]:
        """
        Find all token contracts deployed by a wallet
        Includes both direct deployments and factory-created tokens
        Returns list of deployed contract addresses with metadata
        """
        print(f"\n[SCANNING] Finding deployed tokens for {wallet_address[:10]}...")

        # First, find factory-deployed tokens (most common for Arena)
        factory_tokens = self.find_factory_deployed_tokens(wallet_address)

        # Also check for direct deployments
        print(f"\n[DIRECT SCAN] Looking for direct contract deployments...")
        direct_tokens = []
        transactions = self.get_wallet_transactions(wallet_address)

        print(f"[INFO] Scanning {len(transactions)} transactions for direct deployments...")

        for tx in transactions:
            # Contract creation has empty 'to' field
            if tx.get('to', '') == '' or tx.get('to') is None:
                # Get transaction receipt to find contract address
                try:
                    tx_hash = tx['hash']
                    receipt = self.w3.eth.get_transaction_receipt(tx_hash)

                    if receipt and receipt.contractAddress:
                        contract_addr = Web3.to_checksum_address(receipt.contractAddress)

                        direct_tokens.append({
                            'contract_address': contract_addr,
                            'tx_hash': tx_hash,
                            'block_number': int(tx['blockNumber']),
                            'timestamp': int(tx['timeStamp']),
                            'datetime': datetime.fromtimestamp(int(tx['timeStamp'])).isoformat(),
                            'gas_used': int(tx['gasUsed']),
                            'gas_price': int(tx['gasPrice']),
                            'deployment_type': 'direct'
                        })

                        print(f"  ✓ Found direct deployment: {contract_addr[:10]}... (Block: {tx['blockNumber']})")

                except Exception as e:
                    print(f"  ✗ Error processing tx {tx.get('hash', 'unknown')}: {e}")
                    continue

                # Rate limiting
                time.sleep(0.1)

        print(f"[DIRECT] Found {len(direct_tokens)} direct deployments\n")

        # Combine both types
        all_tokens = factory_tokens + direct_tokens

        # Remove duplicates based on contract address
        seen_addresses = set()
        unique_tokens = []
        for token in all_tokens:
            addr = token['contract_address']
            if addr not in seen_addresses:
                seen_addresses.add(addr)
                unique_tokens.append(token)

        print(f"[RESULT] Total unique tokens deployed: {len(unique_tokens)}")
        print(f"  - Factory deployments: {len(factory_tokens)}")
        print(f"  - Direct deployments: {len(direct_tokens)}\n")

        return unique_tokens

    def get_token_transfers(self, wallet_address: str, token_contract: str) -> List[Dict]:
        """Get all token transfer events for a specific wallet and token"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_contract,
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.api_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data['status'] == '1':
                return data['result']
            return []
        except Exception as e:
            print(f"Error fetching token transfers: {e}")
            return []

    def analyze_token_trades(self, wallet_address: str, token_contract: str,
                            deployment_block: int) -> Dict:
        """
        Analyze all trades (buys and sells) for a specific token
        Returns profit/loss calculation in AVAX and USD
        Includes secondary wallet tracking
        """
        print(f"    [ANALYZING] Token {token_contract[:10]}...")

        # Find secondary wallets used for hiding dumps
        secondary_wallets = self.find_secondary_wallets(wallet_address, token_contract)

        # Track all wallets (primary + secondary)
        all_wallets = {wallet_address.lower()}
        all_wallets.update([w.lower() for w in secondary_wallets])

        buys = []  # AVAX spent to acquire tokens
        sells = []  # AVAX received from selling tokens
        secondary_sells = []  # Sales from secondary wallets

        # Analyze primary wallet transactions
        all_txs = self.get_wallet_transactions(wallet_address, start_block=deployment_block)
        token_transfers = self.get_token_transfers(wallet_address, token_contract)

        for tx in all_txs:
            if int(tx['blockNumber']) < deployment_block:
                continue

            tx_hash = tx['hash']
            value_wei = int(tx.get('value', 0))
            value_avax = float(self.w3.from_wei(value_wei, 'ether'))
            timestamp = int(tx['timeStamp'])

            # Get USD price at transaction time
            avax_usd_price = self.get_avax_usd_price(timestamp)

            # Check if this transaction involved the token
            related_transfers = [t for t in token_transfers if t['hash'] == tx_hash]

            if not related_transfers:
                continue

            # Determine if buy or sell based on direction
            for transfer in related_transfers:
                from_addr = transfer['from'].lower()
                to_addr = transfer['to'].lower()
                wallet_lower = wallet_address.lower()

                # Buy: wallet receives tokens
                if to_addr == wallet_lower and from_addr != wallet_lower:
                    buys.append({
                        'tx_hash': tx_hash,
                        'block': int(tx['blockNumber']),
                        'timestamp': timestamp,
                        'avax_spent': value_avax,
                        'usd_spent': value_avax * avax_usd_price,
                        'avax_usd_price': avax_usd_price,
                        'token_amount': int(transfer['value']) / (10 ** int(transfer.get('tokenDecimal', 18))),
                        'wallet': 'primary'
                    })

                # Sell: wallet sends tokens
                elif from_addr == wallet_lower and to_addr != wallet_lower:
                    # For sells, we need to find AVAX received (might be in internal txs)
                    internal_txs = self.get_internal_transactions(wallet_address)
                    avax_received = 0

                    # Find internal tx with matching hash
                    for itx in internal_txs:
                        if itx['hash'] == tx_hash and itx['to'].lower() == wallet_lower:
                            avax_received = float(self.w3.from_wei(int(itx.get('value', 0)), 'ether'))
                            break

                    sells.append({
                        'tx_hash': tx_hash,
                        'block': int(tx['blockNumber']),
                        'timestamp': timestamp,
                        'avax_received': avax_received,
                        'usd_received': avax_received * avax_usd_price,
                        'avax_usd_price': avax_usd_price,
                        'token_amount': int(transfer['value']) / (10 ** int(transfer.get('tokenDecimal', 18))),
                        'wallet': 'primary'
                    })

            # Rate limiting
            time.sleep(0.05)

        # Analyze secondary wallet transactions
        for secondary_wallet in secondary_wallets:
            print(f"      [SECONDARY] Analyzing {secondary_wallet[:10]}...")
            sec_txs = self.get_wallet_transactions(secondary_wallet, start_block=deployment_block)
            sec_transfers = self.get_token_transfers(secondary_wallet, token_contract)

            for tx in sec_txs:
                if int(tx['blockNumber']) < deployment_block:
                    continue

                tx_hash = tx['hash']
                timestamp = int(tx['timeStamp'])
                avax_usd_price = self.get_avax_usd_price(timestamp)

                related_transfers = [t for t in sec_transfers if t['hash'] == tx_hash]
                if not related_transfers:
                    continue

                for transfer in related_transfers:
                    from_addr = transfer['from'].lower()
                    to_addr = transfer['to'].lower()

                    # Only track sells from secondary wallet
                    if from_addr == secondary_wallet.lower():
                        internal_txs = self.get_internal_transactions(secondary_wallet)
                        avax_received = 0

                        for itx in internal_txs:
                            if itx['hash'] == tx_hash and itx['to'].lower() == secondary_wallet.lower():
                                avax_received = float(self.w3.from_wei(int(itx.get('value', 0)), 'ether'))
                                break

                        secondary_sells.append({
                            'tx_hash': tx_hash,
                            'block': int(tx['blockNumber']),
                            'timestamp': timestamp,
                            'avax_received': avax_received,
                            'usd_received': avax_received * avax_usd_price,
                            'avax_usd_price': avax_usd_price,
                            'token_amount': int(transfer['value']) / (10 ** int(transfer.get('tokenDecimal', 18))),
                            'wallet': secondary_wallet
                        })

                time.sleep(0.05)

        # Calculate totals (including secondary wallets)
        total_avax_spent = sum(b['avax_spent'] for b in buys)
        total_usd_spent = sum(b['usd_spent'] for b in buys)

        total_avax_received = sum(s['avax_received'] for s in sells)
        total_usd_received = sum(s['usd_received'] for s in sells)

        # Add secondary wallet sales
        secondary_avax_received = sum(s['avax_received'] for s in secondary_sells)
        secondary_usd_received = sum(s['usd_received'] for s in secondary_sells)

        total_avax_received += secondary_avax_received
        total_usd_received += secondary_usd_received

        profit_avax = total_avax_received - total_avax_spent
        profit_usd = total_usd_received - total_usd_spent

        result = {
            'token_address': token_contract,
            'num_buys': len(buys),
            'num_sells': len(sells),
            'num_secondary_sells': len(secondary_sells),
            'total_avax_spent': total_avax_spent,
            'total_usd_spent': total_usd_spent,
            'total_avax_received': total_avax_received,
            'total_usd_received': total_usd_received,
            'profit_avax': profit_avax,
            'profit_usd': profit_usd,
            'secondary_wallets': list(secondary_wallets),
            'secondary_avax_profit': secondary_avax_received,
            'secondary_usd_profit': secondary_usd_received,
            'buy_transactions': buys,
            'sell_transactions': sells,
            'secondary_sell_transactions': secondary_sells
        }

        print(f"      Buys: {len(buys)} | Sells: {len(sells)} + {len(secondary_sells)} secondary")
        print(f"      Profit: {profit_avax:.4f} AVAX (${profit_usd:.2f} USD)")
        if secondary_sells:
            print(f"      Secondary Profit: {secondary_avax_received:.4f} AVAX (${secondary_usd_received:.2f} USD)")

        return result

    def analyze_wallet(self, wallet_address: str) -> Dict:
        """
        Complete analysis of a single wallet
        Returns all deployed tokens and profit metrics
        """
        wallet_address = Web3.to_checksum_address(wallet_address)

        print(f"\n{'='*70}")
        print(f"ANALYZING WALLET: {wallet_address}")
        print(f"{'='*70}")

        # Get current AVAX balance
        avax_balance = self.get_avax_balance(wallet_address)
        print(f"[BALANCE] Current AVAX: {avax_balance:.18f} AVAX")
        print(f"{'='*70}\n")

        # Find all deployed tokens
        deployed_tokens = self.find_deployed_tokens(wallet_address)

        if not deployed_tokens:
            print(f"[WARNING] No token deployments found for {wallet_address}")
            print(f"[INFO] AVAX Balance: {avax_balance:.18f} AVAX\n")
            return {
                'wallet_address': wallet_address,
                'avax_balance': avax_balance,
                'num_tokens_deployed': 0,
                'total_profit_avax': 0,
                'total_profit_usd': 0,
                'tokens': []
            }

        # Analyze each token
        print(f"\n[PROFIT ANALYSIS] Analyzing {len(deployed_tokens)} tokens...\n")

        token_analyses = []
        total_profit_avax = 0
        total_profit_usd = 0
        profitable_count = 0
        total_secondary_wallets = set()

        for i, token_info in enumerate(deployed_tokens, 1):
            print(f"  [{i}/{len(deployed_tokens)}] Token: {token_info['contract_address'][:10]}...")

            try:
                analysis = self.analyze_token_trades(
                    wallet_address,
                    token_info['contract_address'],
                    token_info['block_number']
                )

                # Merge deployment info with analysis
                full_analysis = {**token_info, **analysis}
                token_analyses.append(full_analysis)

                total_profit_avax += analysis['profit_avax']
                total_profit_usd += analysis['profit_usd']
                if analysis['profit_avax'] > 0:
                    profitable_count += 1

                # Track unique secondary wallets(you sneaky huh? ;-))
                total_secondary_wallets.update(analysis.get('secondary_wallets', []))

            except Exception as e:
                print(f"      ✗ Error analyzing token: {e}")
                continue

            # Rate limiting between tokens
            time.sleep(0.3)

        # Calculate summary metrics
        result = {
            'wallet_address': wallet_address,
            'avax_balance': avax_balance,
            'num_tokens_deployed': len(deployed_tokens),
            'num_tokens_analyzed': len(token_analyses),
            'profitable_tokens': profitable_count,
            'total_profit_avax': total_profit_avax,
            'total_profit_usd': total_profit_usd,
            'average_profit_per_token_avax': total_profit_avax / len(token_analyses) if token_analyses else 0,
            'average_profit_per_token_usd': total_profit_usd / len(token_analyses) if token_analyses else 0,
            'success_rate': (profitable_count / len(token_analyses) * 100) if token_analyses else 0,
            'total_secondary_wallets_used': len(total_secondary_wallets),
            'secondary_wallets': list(total_secondary_wallets),
            'tokens': token_analyses
        }

        # Print summary
        print(f"\n{'='*70}")
        print(f"WALLET SUMMARY: {wallet_address[:10]}...")
        print(f"{'='*70}")
        print(f"  AVAX Balance:          {avax_balance:.18f} AVAX")
        print(f"  Tokens Deployed:       {result['num_tokens_deployed']}")
        print(f"  Tokens Analyzed:       {result['num_tokens_analyzed']}")
        print(f"  Profitable Tokens:     {profitable_count}")
        print(f"  Total Profit:          {total_profit_avax:.4f} AVAX (${total_profit_usd:.2f} USD)")
        print(f"  Avg Profit/Token:      {result['average_profit_per_token_avax']:.4f} AVAX (${result['average_profit_per_token_usd']:.2f} USD)")
        print(f"  Success Rate:          {result['success_rate']:.1f}%")
        print(f"  Secondary Wallets:     {len(total_secondary_wallets)}")
        print(f"{'='*70}\n")

        return result

    def analyze_multiple_wallets(self, wallet_addresses: List[str]) -> Dict:
        """
        Analyze multiple wallets and generate combined report
        """
        print(f"\n{'#'*70}")
        print(f"# ARENA PROXY PROFIT TRACKER")
        print(f"# Analyzing {len(wallet_addresses)} wallets")
        print(f"# Arena Proxy: {self.arena_proxy}")
        print(f"{'#'*70}\n")

        all_results = []

        for wallet in wallet_addresses:
            result = self.analyze_wallet(wallet)
            all_results.append(result)
            self.results['wallets'][wallet] = result

        # Calculate combined metrics
        total_tokens = sum(r['num_tokens_deployed'] for r in all_results)
        total_profit_avax = sum(r['total_profit_avax'] for r in all_results)
        total_profit_usd = sum(r['total_profit_usd'] for r in all_results)
        total_profitable = sum(r['profitable_tokens'] for r in all_results)
        total_analyzed = sum(r['num_tokens_analyzed'] for r in all_results)
        total_secondary = sum(r.get('total_secondary_wallets_used', 0) for r in all_results)

        self.results['summary'] = {
            'num_wallets_analyzed': len(wallet_addresses),
            'total_tokens_deployed': total_tokens,
            'total_tokens_analyzed': total_analyzed,
            'total_profitable_tokens': total_profitable,
            'combined_profit_avax': total_profit_avax,
            'combined_profit_usd': total_profit_usd,
            'average_profit_per_wallet_avax': total_profit_avax / len(wallet_addresses) if wallet_addresses else 0,
            'average_profit_per_wallet_usd': total_profit_usd / len(wallet_addresses) if wallet_addresses else 0,
            'overall_success_rate': (total_profitable / total_analyzed * 100) if total_analyzed else 0,
            'total_secondary_wallets': total_secondary
        }

        # Print final summary
        print(f"\n{'#'*70}")
        print(f"# COMBINED SUMMARY - ALL WALLETS")
        print(f"{'#'*70}")
        print(f"  Wallets Analyzed:          {len(wallet_addresses)}")
        print(f"  Total Tokens Deployed:     {total_tokens}")
        print(f"  Total Tokens Analyzed:     {total_analyzed}")
        print(f"  Total Profitable Tokens:   {total_profitable}")
        print(f"  COMBINED PROFIT:           {total_profit_avax:.4f} AVAX (${total_profit_usd:.2f} USD)")
        print(f"  Avg Profit per Wallet:     {self.results['summary']['average_profit_per_wallet_avax']:.4f} AVAX (${self.results['summary']['average_profit_per_wallet_usd']:.2f} USD)")
        print(f"  Overall Success Rate:      {self.results['summary']['overall_success_rate']:.1f}%")
        print(f"  Total Secondary Wallets:   {total_secondary}")
        print(f"{'#'*70}\n")

        return self.results

    def export_results(self, filename: Optional[str] = None):
        """Export results to JSON file"""
        if filename is None:
            filename = f"arena_profit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"[EXPORT] Results saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to export results: {e}")

    def generate_blacklist_entries(self, min_tokens: int = 5000, min_profit_usd: float = 100.0) -> List[Dict]:
        """
        Generate blacklist entries for wallets meeting criteria

        Args:
            min_tokens: Minimum combined tokens deployed to blacklist
            min_profit_usd: Minimum combined profit in USD to blacklist
        """
        blacklist_entries = []

        for wallet_addr, data in self.results['wallets'].items():
            num_tokens = data['num_tokens_deployed']
            profit_avax = data['total_profit_avax']
            profit_usd = data['total_profit_usd']
            secondary_wallets = data.get('total_secondary_wallets_used', 0)

            if num_tokens >= min_tokens or profit_usd >= min_profit_usd:
                entry = {
                    'address': wallet_addr.lower(),
                    'reason': f"Arena deployer: {num_tokens} tokens deployed, ${profit_usd:.2f} USD profit ({profit_avax:.2f} AVAX)",
                    'evidence': {
                        'tokens_deployed': num_tokens,
                        'tokens_analyzed': data['num_tokens_analyzed'],
                        'profitable_tokens': data['profitable_tokens'],
                        'total_profit_avax': profit_avax,
                        'total_profit_usd': profit_usd,
                        'success_rate': data['success_rate'],
                        'secondary_wallets_used': secondary_wallets,
                        'pattern': 'arena_serial_deployer',
                        'arena_proxy': self.arena_proxy
                    },
                    'timestamp': datetime.now().isoformat(),
                    'flagged_by': 'ArenaProxyProfitTracker'
                }
                blacklist_entries.append(entry)

                print(f"\n[BLACKLIST] {wallet_addr}")
                print(f"  Reason: {entry['reason']}")
                if secondary_wallets > 0:
                    print(f"  Secondary Wallets Used: {secondary_wallets}")

        return blacklist_entries

    def print_detailed_token_report(self, wallet_address: str, top_n: int = 10):
        """Print detailed report of top N most profitable tokens for a wallet"""
        wallet_address = Web3.to_checksum_address(wallet_address)

        if wallet_address not in self.results['wallets']:
            print(f"No data found for wallet {wallet_address}")
            return

        wallet_data = self.results['wallets'][wallet_address]
        tokens = wallet_data['tokens']

        # Sort by profit (USD)
        sorted_tokens = sorted(tokens, key=lambda x: x.get('profit_usd', 0), reverse=True)

        print(f"\n{'='*70}")
        print(f"TOP {top_n} MOST PROFITABLE TOKENS - {wallet_address[:10]}...")
        print(f"{'='*70}\n")

        for i, token in enumerate(sorted_tokens[:top_n], 1):
            print(f"{i}. Token: {token['token_address']}")
            print(f"   Deployed: {token['datetime']}")
            print(f"   Buys: {token['num_buys']} | Sells: {token['num_sells']} (Primary)")
            if token.get('num_secondary_sells', 0) > 0:
                print(f"   Secondary Sells: {token['num_secondary_sells']} via {len(token.get('secondary_wallets', []))} wallets")
            print(f"   Spent: {token['total_avax_spent']:.4f} AVAX (${token['total_usd_spent']:.2f})")
            print(f"   Received: {token['total_avax_received']:.4f} AVAX (${token['total_usd_received']:.2f})")
            print(f"   PROFIT: {token['profit_avax']:.4f} AVAX (${token['profit_usd']:.2f})")
            print()

    def check_buy_limit_violations(self, min_buy_limit: float = 5.0) -> Dict:
        """
        Check if deployers bought more than the min_buy_limit in AVAX
        Returns violations for potential blacklisting

        Args:
            min_buy_limit: Minimum AVAX buy amount to be flagged (default 5 AVAX)
        """
        print(f"\n{'='*70}")
        print(f"CHECKING BUY LIMIT VIOLATIONS (>{min_buy_limit} AVAX)")
        print(f"{'='*70}\n")

        violations = []

        for wallet_addr, data in self.results['wallets'].items():
            for token in data['tokens']:
                total_bought = token.get('total_avax_spent', 0)

                # If bought more than limit
                if total_bought > min_buy_limit:
                    # Will lets check if they dumped (sold more than they bought)
                    total_sold = token.get('total_avax_received', 0)

                    # Only flag if they dumped (profited or broke even) before bonding is a no-no
                    if total_sold >= total_bought * 0.8:  # Sold at least 80% of value(prebond is so much worse bro)
                        violation = {
                            'wallet': wallet_addr,
                            'token': token['token_address'],
                            'avax_bought': total_bought,
                            'avax_sold': total_sold,
                            'profit_avax': token.get('profit_avax', 0),
                            'profit_usd': token.get('profit_usd', 0),
                            'deployed': token.get('datetime', 'unknown'),
                            'num_buys': token.get('num_buys', 0),
                            'num_sells': token.get('num_sells', 0),
                            'secondary_sells': token.get('num_secondary_sells', 0)
                        }
                        violations.append(violation)

                        print(f"[VIOLATION] {wallet_addr[:10]}...")
                        print(f"  Token: {token['token_address'][:10]}...")
                        print(f"  Bought: {total_bought:.2f} AVAX (limit: {min_buy_limit})")
                        print(f"  Sold: {total_sold:.2f} AVAX")
                        print(f"  Profit: {violation['profit_avax']:.2f} AVAX (${violation['profit_usd']:.2f})")
                        if violation['secondary_sells'] > 0:
                            print(f"  Secondary dumps: {violation['secondary_sells']}")
                        print()

        print(f"Total violations found: {len(violations)}\n")
        return {
            'violations': violations,
            'total_violations': len(violations),
            'min_buy_limit': min_buy_limit
        }


# Main execution
if __name__ == "__main__":
    # Configuration
    RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
    API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with your actual API key
    ARENA_PROXY = "0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c"

    # List of target wallets to analyze
    # NOTE: Last wallet (0x0eead2...) has ~20 factory-deployed tokens in last 4 hours - good test case
    TARGET_WALLETS = [
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
        "0x0eead2dafcf656671c3adec00c1b7edf968338c0",  # Test wallet with factory deployments
    ]

    # Initialize tracker
    tracker = ArenaProxyProfitTracker(RPC_URL, API_KEY, ARENA_PROXY)

    # Analyze wallets
    results = tracker.analyze_multiple_wallets(TARGET_WALLETS)

    # Export results
    tracker.export_results()

    # Generate blacklist entries
    print(f"\n{'='*70}")
    print("BLACKLIST EVALUATION")
    print(f"{'='*70}")
    blacklist_entries = tracker.generate_blacklist_entries(
        min_tokens=2500,  # Will watch this as cur half of 5000 since we're checking 2 wallets
        min_profit_usd=50.0   # Minimum USD profit to blacklist
    )

    # Check for buy limit violations (>5 AVAX buys that were dumped)
    buy_violations = tracker.check_buy_limit_violations(min_buy_limit=5.0)

    # Print detailed reports for each wallet
    for wallet in TARGET_WALLETS:
        tracker.print_detailed_token_report(wallet, top_n=10)

    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"\nBlacklist Entries: {len(blacklist_entries)}")
    print(f"Buy Limit Violations: {buy_violations['total_violations']}")
    print(f"\nNote: Dexscreener bonding check not yet implemented.")
    print(f"      Currently flagging dumps that recovered 80%+ of buy value.")
    print(f"{'='*70}")
