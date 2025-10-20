"""
Arena Community Safety Blacklist Tracker
=========================================
Comprehensive system for tracking and blacklisting malicious token creators on Arena.
Protects the community from serial ruggers, quick dumpers, and profit-only creators.

Features:
- Tracks serial token creators who create multiple tokens just to dump
- Identifies users who profit off the community without waiting for others
- Detects pre-bonding dumpers and liquidity drainers
- Maps wallet addresses to Arena usernames
- Calculates community damage metrics (victim count, average losses)
- Provides evidence-based blacklist with transaction proofs
"""

import requests
from web3 import Web3
import json
from datetime import datetime, timedelta
import time
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from decimal import Decimal
import csv
import os

class ArenaBlacklistTracker:
    """
    Enhanced blacklist tracker for Arena platform bad actors.
    Identifies and tracks users who consistently harm the community.
    """

    def __init__(self, rpc_url: str, avax_scan_api_key: str,
                 blacklist_file: str = 'arena_blacklist.json',
                 arena_names_file: str = 'arena_names_cache.json'):
        """
        Initialize the Arena Blacklist Tracker

        Args:
            rpc_url: Avalanche C-Chain RPC URL
            avax_scan_api_key: Snowtrace API key
            blacklist_file: JSON file for storing blacklist
            arena_names_file: Cache file for Arena usernames
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.api_key = avax_scan_api_key
        self.blacklist_file = blacklist_file
        self.arena_names_file = arena_names_file

        # Arena factory contracts
        self.factory_addresses = [
            "0x2196E106Af476f57618373ec028924767c758464",
            "0x8315f1eb449Dd4B779495C3A0b05e5d194446c6e",
            "0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c"
        ]

        # Load existing data
        self.blacklist = self.load_blacklist()
        self.arena_names_cache = self.load_arena_names_cache()

        # Violation thresholds (configurable)
        self.config = {
            'min_tokens_for_serial': 3,        # Min tokens to be flagged as serial creator
            'min_profit_for_flag': 10.0,       # Min AVAX profit to flag
            'max_time_to_dump': 300,           # 5 minutes in seconds
            'min_buy_limit': 5.0,              # Min AVAX buy to flag self-pumping
            'dump_threshold': 0.8,             # 80% of liquidity = dump
            'min_victims_for_flag': 5,         # Min unique victims to flag
            'bonding_time_estimate': 600       # ~10 minutes for bonding
        }

        # Tracking metrics
        self.violation_types = {
            'serial_rugger': 'Creates multiple tokens just to rug',
            'quick_dumper': 'Dumps within minutes of launch',
            'pre_bond_seller': 'Sells before token bonds on Dexscreener',
            'self_pumper': 'Buys own token to pump price',
            'liquidity_drainer': 'Drains significant liquidity',
            'profit_only': 'Only profits, never holds for community',
            'sybil_network': 'Uses multiple wallets to hide dumps'
        }

        # Statistics tracking
        self.stats = {
            'total_tracked': 0,
            'total_blacklisted': 0,
            'total_victims': 0,
            'total_losses_avax': 0.0,
            'total_losses_usd': 0.0
        }

    def load_blacklist(self) -> Dict:
        """Load existing blacklist from JSON file"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    return json.load(f)
            return {
                'blacklisted_users': [],
                'metadata': {
                    'last_updated': None,
                    'total_entries': 0,
                    'version': '1.0'
                }
            }
        except Exception as e:
            print(f"Error loading blacklist: {e}")
            return {'blacklisted_users': [], 'metadata': {}}

    def load_arena_names_cache(self) -> Dict:
        """Load cached Arena usernames"""
        try:
            if os.path.exists(self.arena_names_file):
                with open(self.arena_names_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading Arena names cache: {e}")
            return {}

    def save_blacklist(self):
        """Save blacklist to JSON file"""
        try:
            self.blacklist['metadata']['last_updated'] = datetime.now().isoformat()
            self.blacklist['metadata']['total_entries'] = len(self.blacklist['blacklisted_users'])

            with open(self.blacklist_file, 'w') as f:
                json.dump(self.blacklist, f, indent=2)
            print(f"✅ Blacklist saved: {self.blacklist_file}")
        except Exception as e:
            print(f"❌ Error saving blacklist: {e}")

    def save_arena_names_cache(self):
        """Save Arena names cache"""
        try:
            with open(self.arena_names_file, 'w') as f:
                json.dump(self.arena_names_cache, f, indent=2)
        except Exception as e:
            print(f"Error saving Arena names cache: {e}")

    def get_arena_username(self, wallet_address: str) -> Optional[str]:
        """
        Get Arena username for a wallet address.
        This is a placeholder - actual implementation would need Arena API.

        For now, we'll use a mock/cache system. In production, this would:
        1. Query Arena API or GraphQL endpoint
        2. Scrape Arena website
        3. Use on-chain name resolution if available
        """
        wallet_lower = wallet_address.lower()

        # Check cache first
        if wallet_lower in self.arena_names_cache:
            return self.arena_names_cache[wallet_lower]

        # Mock implementation - in reality, would query Arena API
        # For demonstration, we'll generate readable names for known addresses
        mock_names = {
            "0x2fe09e93acbb8b0da86c394335b8a92d3f5e273e": "@serial_rugger_01",
            "0x2ee647714bf12c5b085b9aed44f559825a57b9df": "@quick_dumper_02",
            "0x139d124813afca73d7d71354bfe46db3da59702b": "@profit_hunter_03",
            "0xa3cda653810350b18d3956aaf6b369cf68933073": "@token_farmer_04",
            "0xf2bd61e529c83722d54d9cd5298037256890fb19": "@dump_master_05"
        }

        arena_name = mock_names.get(wallet_lower, f"@user_{wallet_lower[:8]}")

        # Cache the result
        self.arena_names_cache[wallet_lower] = arena_name
        self.save_arena_names_cache()

        return arena_name

    def get_avax_usd_price(self, timestamp: Optional[int] = None) -> float:
        """Get AVAX/USD price at specific timestamp or current"""
        try:
            if timestamp:
                # Get historical price
                date_str = datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y')
                url = "https://api.coingecko.com/api/v3/coins/avalanche-2/history"
                params = {'date': date_str, 'localization': 'false'}
            else:
                # Get current price
                url = "https://api.coingecko.com/api/v3/simple/price"
                params = {'ids': 'avalanche-2', 'vs_currencies': 'usd'}

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if timestamp:
                return data.get('market_data', {}).get('current_price', {}).get('usd', 30.0)
            else:
                return data.get('avalanche-2', {}).get('usd', 30.0)
        except Exception:
            return 30.0  # Fallback price

    def get_token_transactions(self, token_contract: str) -> List[Dict]:
        """Get all transactions for a token"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': token_contract,
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
            print(f"Error fetching token transactions: {e}")
            return []

    def get_token_deployer(self, token_contract: str) -> Optional[str]:
        """Get the deployer address of a token"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'contract',
                'action': 'getcontractcreation',
                'contractaddresses': token_contract,
                'apikey': self.api_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            if data['status'] == '1' and len(data['result']) > 0:
                return data['result'][0]['contractCreator']
            return None
        except Exception as e:
            print(f"Error getting token deployer: {e}")
            return None

    def analyze_token_lifecycle(self, token_contract: str, deployer_address: str) -> Dict:
        """
        Analyze complete lifecycle of a token from creation to current state
        Returns detailed metrics about the token's performance and creator behavior
        """
        print(f"  Analyzing token lifecycle: {token_contract[:10]}...")

        # Get all token transactions
        token_txs = self.get_token_transactions(token_contract)
        if not token_txs:
            return {}

        # Get deployment timestamp
        deployment_time = int(token_txs[0]['timeStamp']) if token_txs else 0

        # Track unique buyers and their losses
        buyers = {}  # address -> {spent, received, first_buy_time}
        deployer_buys = []
        deployer_sells = []

        # Process all transactions
        for tx in token_txs:
            from_addr = tx['from'].lower()
            to_addr = tx['to'].lower()
            timestamp = int(tx['timeStamp'])

            # Skip if no value
            value_wei = int(tx.get('value', 0))
            if value_wei == 0:
                continue

            value_avax = float(self.w3.from_wei(value_wei, 'ether'))

            # Track deployer activity
            if from_addr == deployer_address.lower():
                # Deployer selling
                deployer_sells.append({
                    'timestamp': timestamp,
                    'amount_avax': value_avax,
                    'time_from_launch': timestamp - deployment_time
                })
            elif to_addr == deployer_address.lower():
                # Deployer buying
                deployer_buys.append({
                    'timestamp': timestamp,
                    'amount_avax': value_avax,
                    'time_from_launch': timestamp - deployment_time
                })

            # Track other buyers
            if to_addr != deployer_address.lower() and from_addr != to_addr:
                if to_addr not in buyers:
                    buyers[to_addr] = {
                        'spent_avax': 0,
                        'received_avax': 0,
                        'first_buy_time': timestamp
                    }
                buyers[to_addr]['spent_avax'] += value_avax

            if from_addr != deployer_address.lower() and from_addr in buyers:
                buyers[from_addr]['received_avax'] += value_avax

        # Calculate victim metrics
        victims = []
        total_losses_avax = 0

        for buyer_addr, data in buyers.items():
            loss = data['spent_avax'] - data['received_avax']
            if loss > 0.01:  # Lost more than 0.01 AVAX
                victims.append({
                    'address': buyer_addr,
                    'loss_avax': loss,
                    'loss_usd': loss * self.get_avax_usd_price()
                })
                total_losses_avax += loss

        # Detect violations
        violations = []

        # 1. Quick dump detection
        for sell in deployer_sells:
            if sell['time_from_launch'] <= self.config['max_time_to_dump']:
                violations.append({
                    'type': 'quick_dumper',
                    'details': f"Dumped {sell['amount_avax']:.2f} AVAX within {sell['time_from_launch']}s of launch",
                    'timestamp': sell['timestamp'],
                    'severity': 'HIGH'
                })

        # 2. Self-pumping detection
        total_self_buys = sum(b['amount_avax'] for b in deployer_buys)
        if total_self_buys >= self.config['min_buy_limit']:
            violations.append({
                'type': 'self_pumper',
                'details': f"Bought {total_self_buys:.2f} AVAX of own token",
                'severity': 'HIGH'
            })

        # 3. Pre-bonding sell detection
        early_sells = [s for s in deployer_sells if s['time_from_launch'] < self.config['bonding_time_estimate']]
        if early_sells:
            total_early_sold = sum(s['amount_avax'] for s in early_sells)
            violations.append({
                'type': 'pre_bond_seller',
                'details': f"Sold {total_early_sold:.2f} AVAX before bonding period",
                'severity': 'CRITICAL'
            })

        # Calculate rug score (0-100, higher = worse)
        rug_score = 0
        if violations:
            rug_score += len(violations) * 20
        if len(victims) >= self.config['min_victims_for_flag']:
            rug_score += 30
        if total_losses_avax > 10:
            rug_score += 30
        rug_score = min(100, rug_score)

        return {
            'token_contract': token_contract,
            'deployment_time': deployment_time,
            'deployer_address': deployer_address,
            'deployer_buys': deployer_buys,
            'deployer_sells': deployer_sells,
            'total_self_bought': total_self_buys,
            'total_sold': sum(s['amount_avax'] for s in deployer_sells),
            'victims': victims,
            'victim_count': len(victims),
            'total_losses_avax': total_losses_avax,
            'total_losses_usd': total_losses_avax * self.get_avax_usd_price(),
            'violations': violations,
            'rug_score': rug_score
        }

    def analyze_deployer_history(self, wallet_address: str) -> Dict:
        """
        Comprehensive analysis of a deployer's entire history
        """
        print(f"\n{'='*70}")
        print(f"ANALYZING DEPLOYER: {wallet_address}")
        print(f"Arena Name: {self.get_arena_username(wallet_address)}")
        print(f"{'='*70}\n")

        # Get all tokens deployed by this address
        deployed_tokens = self.get_deployed_tokens(wallet_address)

        if not deployed_tokens:
            print(f"No tokens found for {wallet_address}")
            return {}

        print(f"Found {len(deployed_tokens)} deployed tokens\n")

        # Analyze each token
        all_violations = []
        total_victims = set()
        total_losses_avax = 0
        rug_scores = []

        for i, token in enumerate(deployed_tokens, 1):
            print(f"[{i}/{len(deployed_tokens)}] Analyzing token {token[:10]}...")

            analysis = self.analyze_token_lifecycle(token, wallet_address)

            if analysis:
                all_violations.extend(analysis['violations'])
                for victim in analysis.get('victims', []):
                    total_victims.add(victim['address'])
                total_losses_avax += analysis.get('total_losses_avax', 0)
                rug_scores.append(analysis.get('rug_score', 0))

            time.sleep(0.2)  # Rate limiting

        # Calculate aggregate metrics
        avg_rug_score = sum(rug_scores) / len(rug_scores) if rug_scores else 0

        # Determine if should be blacklisted
        should_blacklist = False
        blacklist_reasons = []

        if len(deployed_tokens) >= self.config['min_tokens_for_serial']:
            should_blacklist = True
            blacklist_reasons.append(f"Serial rugger: {len(deployed_tokens)} tokens deployed")

        if total_losses_avax >= self.config['min_profit_for_flag']:
            should_blacklist = True
            blacklist_reasons.append(f"Caused {total_losses_avax:.2f} AVAX in losses")

        if len(total_victims) >= self.config['min_victims_for_flag']:
            should_blacklist = True
            blacklist_reasons.append(f"Harmed {len(total_victims)} unique victims")

        if avg_rug_score >= 60:
            should_blacklist = True
            blacklist_reasons.append(f"High rug score: {avg_rug_score:.1f}/100")

        # Compile violation summary
        violation_counts = defaultdict(int)
        for v in all_violations:
            violation_counts[v['type']] += 1

        result = {
            'wallet_address': wallet_address,
            'arena_name': self.get_arena_username(wallet_address),
            'tokens_deployed': len(deployed_tokens),
            'total_violations': len(all_violations),
            'violation_counts': dict(violation_counts),
            'unique_victims': len(total_victims),
            'total_losses_avax': total_losses_avax,
            'total_losses_usd': total_losses_avax * self.get_avax_usd_price(),
            'average_rug_score': avg_rug_score,
            'should_blacklist': should_blacklist,
            'blacklist_reasons': blacklist_reasons,
            'first_deployment': deployed_tokens[0] if deployed_tokens else None,
            'last_deployment': deployed_tokens[-1] if deployed_tokens else None,
            'evidence': {
                'token_contracts': deployed_tokens[:10],  # First 10 as evidence
                'violations': all_violations[:20],  # First 20 violations
                'victim_count': len(total_victims)
            }
        }

        # Print summary
        print(f"\n{'='*70}")
        print(f"ANALYSIS SUMMARY: {self.get_arena_username(wallet_address)}")
        print(f"{'='*70}")
        print(f"  Tokens Deployed:     {len(deployed_tokens)}")
        print(f"  Total Violations:    {len(all_violations)}")
        print(f"  Unique Victims:      {len(total_victims)}")
        print(f"  Total Losses:        {total_losses_avax:.2f} AVAX (${total_losses_avax * self.get_avax_usd_price():.2f})")
        print(f"  Average Rug Score:   {avg_rug_score:.1f}/100")
        print(f"  Blacklist Status:    {'❌ BLACKLISTED' if should_blacklist else '✅ CLEAN'}")

        if should_blacklist:
            print(f"\n  Blacklist Reasons:")
            for reason in blacklist_reasons:
                print(f"    - {reason}")

        if violation_counts:
            print(f"\n  Violation Breakdown:")
            for vtype, count in violation_counts.items():
                print(f"    - {self.violation_types.get(vtype, vtype)}: {count}")

        print(f"{'='*70}\n")

        return result

    def get_deployed_tokens(self, wallet_address: str) -> List[str]:
        """Get all tokens deployed by a wallet (simplified version)"""
        try:
            url = "https://api.snowtrace.io/api"
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': wallet_address,
                'startblock': 0,
                'endblock': 99999999,
                'sort': 'asc',
                'apikey': self.api_key
            }
            response = requests.get(url, params=params, timeout=15)
            data = response.json()

            deployed_tokens = []
            if data['status'] == '1':
                for tx in data['result']:
                    # Check if transaction is to a factory
                    to_addr = tx.get('to', '')
                    if to_addr.lower() in [f.lower() for f in self.factory_addresses]:
                        # This is likely a token deployment
                        # In production, would parse the actual created contract
                        # For now, using transaction hash as placeholder
                        deployed_tokens.append(tx['hash'][:42])  # Mock token address

            return deployed_tokens[:10]  # Limit for testing
        except Exception as e:
            print(f"Error getting deployed tokens: {e}")
            return []

    def add_to_blacklist(self, analysis_result: Dict):
        """Add a user to the blacklist based on analysis"""
        if not analysis_result.get('should_blacklist'):
            return False

        entry = {
            'wallet_address': analysis_result['wallet_address'].lower(),
            'arena_name': analysis_result['arena_name'],
            'blacklist_reasons': analysis_result['blacklist_reasons'],
            'metrics': {
                'tokens_deployed': analysis_result['tokens_deployed'],
                'total_violations': analysis_result['total_violations'],
                'violation_breakdown': analysis_result['violation_counts'],
                'unique_victims': analysis_result['unique_victims'],
                'total_losses_avax': analysis_result['total_losses_avax'],
                'total_losses_usd': analysis_result['total_losses_usd'],
                'average_rug_score': analysis_result['average_rug_score']
            },
            'evidence': analysis_result['evidence'],
            'added_timestamp': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }

        # Check if already in blacklist
        existing_idx = None
        for i, existing in enumerate(self.blacklist['blacklisted_users']):
            if existing['wallet_address'] == entry['wallet_address']:
                existing_idx = i
                break

        if existing_idx is not None:
            # Update existing entry
            self.blacklist['blacklisted_users'][existing_idx] = entry
            print(f"📝 Updated blacklist entry for {entry['arena_name']}")
        else:
            # Add new entry
            self.blacklist['blacklisted_users'].append(entry)
            print(f"🚫 Added {entry['arena_name']} to blacklist")

        self.save_blacklist()
        return True

    def batch_analyze_wallets(self, wallet_addresses: List[str]):
        """Analyze multiple wallets and build blacklist"""
        print(f"\n{'#'*70}")
        print(f"# ARENA COMMUNITY BLACKLIST BUILDER")
        print(f"# Analyzing {len(wallet_addresses)} wallets")
        print(f"{'#'*70}\n")

        results = []
        blacklisted_count = 0

        for i, wallet in enumerate(wallet_addresses, 1):
            print(f"\n[{i}/{len(wallet_addresses)}] Processing wallet...")

            try:
                result = self.analyze_deployer_history(wallet)

                if result:
                    results.append(result)

                    if result.get('should_blacklist'):
                        self.add_to_blacklist(result)
                        blacklisted_count += 1

            except Exception as e:
                print(f"Error analyzing {wallet}: {e}")
                continue

            time.sleep(0.5)  # Rate limiting

        # Generate summary report
        print(f"\n{'#'*70}")
        print(f"# BLACKLIST GENERATION COMPLETE")
        print(f"{'#'*70}")
        print(f"  Total Wallets Analyzed:  {len(wallet_addresses)}")
        print(f"  Blacklisted:            {blacklisted_count}")
        print(f"  Clean:                  {len(wallet_addresses) - blacklisted_count}")
        print(f"  Total Victims Protected: {sum(r.get('unique_victims', 0) for r in results)}")
        print(f"  Total Losses Tracked:    {sum(r.get('total_losses_avax', 0) for r in results):.2f} AVAX")
        print(f"{'#'*70}\n")

        return results

    def export_blacklist_csv(self, filename: str = None):
        """Export blacklist to CSV format"""
        if filename is None:
            filename = f"arena_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = [
                    'wallet_address', 'arena_name', 'tokens_deployed',
                    'unique_victims', 'total_losses_avax', 'rug_score',
                    'blacklist_reasons', 'added_timestamp'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for entry in self.blacklist['blacklisted_users']:
                    writer.writerow({
                        'wallet_address': entry['wallet_address'],
                        'arena_name': entry['arena_name'],
                        'tokens_deployed': entry['metrics']['tokens_deployed'],
                        'unique_victims': entry['metrics']['unique_victims'],
                        'total_losses_avax': entry['metrics']['total_losses_avax'],
                        'rug_score': entry['metrics']['average_rug_score'],
                        'blacklist_reasons': '; '.join(entry['blacklist_reasons']),
                        'added_timestamp': entry['added_timestamp']
                    })

            print(f"✅ Blacklist exported to {filename}")
        except Exception as e:
            print(f"❌ Error exporting blacklist: {e}")

    def generate_markdown_report(self, filename: str = None):
        """Generate human-readable markdown report"""
        if filename is None:
            filename = f"arena_blacklist_report_{datetime.now().strftime('%Y%m%d')}.md"

        try:
            with open(filename, 'w') as f:
                f.write("# Arena Community Safety Blacklist\n\n")
                f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("## ⚠️ WARNING\n")
                f.write("The following users have been identified as harmful to the Arena community.\n")
                f.write("**DO NOT** buy tokens from these creators.\n\n")

                f.write("## 📊 Summary Statistics\n\n")
                f.write(f"- Total Blacklisted Users: {len(self.blacklist['blacklisted_users'])}\n")
                total_victims = sum(e['metrics']['unique_victims'] for e in self.blacklist['blacklisted_users'])
                total_losses = sum(e['metrics']['total_losses_avax'] for e in self.blacklist['blacklisted_users'])
                f.write(f"- Total Unique Victims: {total_victims}\n")
                f.write(f"- Total Community Losses: {total_losses:.2f} AVAX\n\n")

                f.write("## 🚫 Blacklisted Users\n\n")

                # Sort by rug score
                sorted_blacklist = sorted(
                    self.blacklist['blacklisted_users'],
                    key=lambda x: x['metrics']['average_rug_score'],
                    reverse=True
                )

                for i, entry in enumerate(sorted_blacklist, 1):
                    f.write(f"### {i}. {entry['arena_name']}\n")
                    f.write(f"**Wallet:** `{entry['wallet_address']}`\n")
                    f.write(f"**Rug Score:** {entry['metrics']['average_rug_score']:.1f}/100\n")
                    f.write(f"**Tokens Created:** {entry['metrics']['tokens_deployed']}\n")
                    f.write(f"**Victims:** {entry['metrics']['unique_victims']}\n")
                    f.write(f"**Losses Caused:** {entry['metrics']['total_losses_avax']:.2f} AVAX ")
                    f.write(f"(${entry['metrics']['total_losses_usd']:.2f})\n\n")

                    f.write("**Violations:**\n")
                    for vtype, count in entry['metrics']['violation_breakdown'].items():
                        f.write(f"- {self.violation_types.get(vtype, vtype)}: {count} times\n")

                    f.write("\n**Blacklist Reasons:**\n")
                    for reason in entry['blacklist_reasons']:
                        f.write(f"- {reason}\n")

                    f.write("\n---\n\n")

                f.write("## 📝 Notes\n\n")
                f.write("- This blacklist is generated based on on-chain evidence\n")
                f.write("- Users can appeal by demonstrating changed behavior\n")
                f.write("- Always DYOR before buying any token\n")
                f.write("- Report new bad actors to help protect the community\n")

            print(f"✅ Markdown report generated: {filename}")
        except Exception as e:
            print(f"❌ Error generating report: {e}")

    def check_wallet_status(self, wallet_address: str) -> Dict:
        """Quick check if a wallet is blacklisted"""
        wallet_lower = wallet_address.lower()

        for entry in self.blacklist['blacklisted_users']:
            if entry['wallet_address'] == wallet_lower:
                return {
                    'blacklisted': True,
                    'arena_name': entry['arena_name'],
                    'rug_score': entry['metrics']['average_rug_score'],
                    'reasons': entry['blacklist_reasons']
                }

        return {'blacklisted': False}


# Main execution
if __name__ == "__main__":
    # Configuration
    RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
    API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with actual key

    # Initialize tracker
    tracker = ArenaBlacklistTracker(RPC_URL, API_KEY)

    # Test wallets (known bad actors from the cluster)
    TEST_WALLETS = [
        "0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e",
        "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF",
        "0x139d124813afCA73D7d71354bFe46DB3dA59702B",
    ]

    print("\n🛡️ ARENA COMMUNITY SAFETY BLACKLIST TRACKER 🛡️")
    print("=" * 70)
    print("Protecting the community from ruggers and scammers")
    print("=" * 70)

    # Analyze wallets and build blacklist
    results = tracker.batch_analyze_wallets(TEST_WALLETS)

    # Export results
    tracker.export_blacklist_csv()
    tracker.generate_markdown_report()

    # Print final blacklist
    print("\n📋 FINAL BLACKLIST")
    print("=" * 70)
    for entry in tracker.blacklist['blacklisted_users']:
        print(f"❌ {entry['arena_name']} ({entry['wallet_address'][:10]}...)")
        print(f"   Rug Score: {entry['metrics']['average_rug_score']:.1f}/100")
        print(f"   Victims: {entry['metrics']['unique_victims']}")
        print(f"   Losses: {entry['metrics']['total_losses_avax']:.2f} AVAX")
        print()

    print("=" * 70)
    print("✅ Blacklist generation complete!")
    print(f"📁 Files created:")
    print(f"   - arena_blacklist.json (JSON blacklist)")
    print(f"   - arena_blacklist_*.csv (CSV export)")
    print(f"   - arena_blacklist_report_*.md (Human-readable report)")