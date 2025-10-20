"""
Arena Complete Blacklist System
================================
Integrates all tracking systems to create a comprehensive blacklist of Arena bad actors.
Combines data from multiple sources to protect the community.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Set
import time

# Import existing trackers
from arenaProxyProfitTracker import ArenaProxyProfitTracker
from arenaShitBagTracker import DeployerTokenTracker
from arenaBlacklistTracker import ArenaBlacklistTracker


class ArenaCompleteTracker:
    """
    Master tracker that combines all data sources to create the ultimate blacklist
    """

    def __init__(self, rpc_url: str, api_key: str):
        """Initialize all tracking components"""
        self.rpc_url = rpc_url
        self.api_key = api_key

        # Initialize sub-trackers
        self.profit_tracker = ArenaProxyProfitTracker(
            rpc_url, api_key,
            "0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c"  # Arena proxy
        )
        self.shitbag_tracker = DeployerTokenTracker(rpc_url, api_key)
        self.blacklist_tracker = ArenaBlacklistTracker(rpc_url, api_key)

        # Load known grifters
        self.known_grifters = self.load_known_grifters()

        # Master blacklist
        self.master_blacklist = {
            'version': '2.0',
            'last_updated': None,
            'total_bad_actors': 0,
            'total_victims_protected': 0,
            'total_losses_prevented_avax': 0.0,
            'blacklisted_users': [],
            'statistics': {}
        }

    def load_known_grifters(self) -> Dict:
        """Load the known grifters list from Dune Analytics data"""
        try:
            with open('known_grifters.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ Known grifters file not found. Creating empty list.")
            return {'known_grifters': [], 'additional_suspicious_wallets': []}

    def analyze_wallet_complete(self, wallet_address: str) -> Dict:
        """
        Complete analysis using all available data sources
        """
        print(f"\n{'='*80}")
        print(f"🔍 COMPLETE ANALYSIS: {wallet_address}")
        print(f"{'='*80}\n")

        result = {
            'wallet_address': wallet_address.lower(),
            'arena_name': None,
            'analysis_timestamp': datetime.now().isoformat(),
            'violations': [],
            'metrics': {},
            'evidence': {},
            'risk_score': 0,
            'blacklist_status': False
        }

        # 1. Check if in known grifters list
        print("[1/5] Checking known grifters list...")
        for grifter in self.known_grifters.get('known_grifters', []):
            if grifter['wallet_address'].lower() == wallet_address.lower():
                result['arena_name'] = grifter['arena_name']
                result['violations'].append({
                    'type': 'known_grifter',
                    'source': 'Dune Analytics',
                    'details': grifter['notes'],
                    'severity': 'CRITICAL'
                })
                result['risk_score'] += 50
                print(f"   ⚠️ FOUND in known grifters list: {grifter['arena_name']}")
                break

        # 2. Analyze with profit tracker
        print("[2/5] Analyzing profit patterns...")
        try:
            profit_analysis = self.profit_tracker.analyze_wallet(wallet_address)

            if profit_analysis:
                tokens_deployed = profit_analysis.get('num_tokens_deployed', 0)
                total_profit = profit_analysis.get('total_profit_avax', 0)
                success_rate = profit_analysis.get('success_rate', 0)

                result['metrics']['tokens_deployed'] = tokens_deployed
                result['metrics']['total_profit_avax'] = total_profit
                result['metrics']['success_rate'] = success_rate

                # Check for violations
                if tokens_deployed >= 50:
                    result['violations'].append({
                        'type': 'serial_deployer',
                        'details': f"Deployed {tokens_deployed} tokens",
                        'severity': 'HIGH'
                    })
                    result['risk_score'] += 30

                if total_profit >= 10:
                    result['violations'].append({
                        'type': 'high_profiteer',
                        'details': f"Profited {total_profit:.2f} AVAX from dumps",
                        'severity': 'HIGH'
                    })
                    result['risk_score'] += 20

                print(f"   📊 Tokens: {tokens_deployed}, Profit: {total_profit:.2f} AVAX")
        except Exception as e:
            print(f"   ❌ Profit analysis failed: {e}")

        # 3. Check with shitbag tracker
        print("[3/5] Checking deployment patterns...")
        try:
            # Check if already blacklisted
            if self.shitbag_tracker.is_blacklisted(wallet_address):
                result['violations'].append({
                    'type': 'previously_blacklisted',
                    'details': 'Already in shitbag tracker blacklist',
                    'severity': 'CRITICAL'
                })
                result['risk_score'] += 40
                print(f"   🚫 Already blacklisted in shitbag tracker")

            # Analyze serial deployment
            serial_analysis = self.shitbag_tracker.analyze_serial_deployer(
                wallet_address, min_tokens=50, min_profit=10
            )

            if serial_analysis:
                result['evidence']['serial_deployment'] = serial_analysis
                print(f"   ⚠️ Serial deployer confirmed")
        except Exception as e:
            print(f"   ❌ Deployment pattern check failed: {e}")

        # 4. Enhanced blacklist analysis
        print("[4/5] Analyzing community damage...")
        try:
            blacklist_analysis = self.blacklist_tracker.analyze_deployer_history(wallet_address)

            if blacklist_analysis:
                result['metrics']['unique_victims'] = blacklist_analysis.get('unique_victims', 0)
                result['metrics']['total_losses_avax'] = blacklist_analysis.get('total_losses_avax', 0)
                result['metrics']['rug_score'] = blacklist_analysis.get('average_rug_score', 0)

                # Update arena name if found
                if not result['arena_name']:
                    result['arena_name'] = blacklist_analysis.get('arena_name')

                # Add violation details
                for violation_type, count in blacklist_analysis.get('violation_counts', {}).items():
                    if count > 0:
                        result['violations'].append({
                            'type': violation_type,
                            'count': count,
                            'severity': 'HIGH' if count > 5 else 'MEDIUM'
                        })

                print(f"   👥 Victims: {result['metrics']['unique_victims']}")
                print(f"   💰 Losses: {result['metrics']['total_losses_avax']:.2f} AVAX")
        except Exception as e:
            print(f"   ❌ Community damage analysis failed: {e}")

        # 5. Calculate final risk score
        print("[5/5] Calculating risk assessment...")

        # Adjust risk score based on metrics
        if result['metrics'].get('unique_victims', 0) >= 10:
            result['risk_score'] += 20
        if result['metrics'].get('total_losses_avax', 0) >= 50:
            result['risk_score'] += 20
        if result['metrics'].get('rug_score', 0) >= 60:
            result['risk_score'] += 10

        # Cap at 100
        result['risk_score'] = min(100, result['risk_score'])

        # Determine blacklist status
        result['blacklist_status'] = result['risk_score'] >= 40

        # Risk level
        if result['risk_score'] >= 80:
            risk_level = "🔴 EXTREME RISK"
        elif result['risk_score'] >= 60:
            risk_level = "🟠 HIGH RISK"
        elif result['risk_score'] >= 40:
            risk_level = "🟡 MEDIUM RISK"
        elif result['risk_score'] >= 20:
            risk_level = "🟢 LOW RISK"
        else:
            risk_level = "⚪ MINIMAL RISK"

        print(f"\n   📊 RISK SCORE: {result['risk_score']}/100 - {risk_level}")
        print(f"   🚫 BLACKLIST: {'YES - DO NOT BUY' if result['blacklist_status'] else 'NO - Proceed with caution'}")

        return result

    def build_master_blacklist(self, wallet_addresses: List[str]):
        """
        Build the master blacklist from all data sources
        """
        print(f"\n{'#'*80}")
        print(f"# 🛡️ BUILDING MASTER ARENA BLACKLIST")
        print(f"# Analyzing {len(wallet_addresses)} wallets")
        print(f"{'#'*80}\n")

        blacklisted_count = 0
        total_victims = set()
        total_losses = 0.0

        for i, wallet in enumerate(wallet_addresses, 1):
            print(f"\n[{i}/{len(wallet_addresses)}] Processing...")

            try:
                analysis = self.analyze_wallet_complete(wallet)

                if analysis['blacklist_status']:
                    # Add to master blacklist
                    entry = {
                        'wallet_address': analysis['wallet_address'],
                        'arena_name': analysis['arena_name'] or f"@unknown_{wallet[:8]}",
                        'risk_score': analysis['risk_score'],
                        'violations': analysis['violations'],
                        'metrics': analysis['metrics'],
                        'added_timestamp': datetime.now().isoformat(),
                        'evidence_summary': {
                            'tokens_deployed': analysis['metrics'].get('tokens_deployed', 0),
                            'total_profit_avax': analysis['metrics'].get('total_profit_avax', 0),
                            'unique_victims': analysis['metrics'].get('unique_victims', 0),
                            'total_losses_avax': analysis['metrics'].get('total_losses_avax', 0),
                            'rug_score': analysis['metrics'].get('rug_score', 0)
                        }
                    }

                    self.master_blacklist['blacklisted_users'].append(entry)
                    blacklisted_count += 1

                    # Update statistics
                    victims_count = analysis['metrics'].get('unique_victims', 0)
                    losses = analysis['metrics'].get('total_losses_avax', 0)
                    total_losses += losses

                    print(f"   ❌ BLACKLISTED: {entry['arena_name']}")

            except Exception as e:
                print(f"   ⚠️ Error analyzing {wallet}: {e}")
                continue

            time.sleep(0.3)  # Rate limiting

        # Update master blacklist metadata
        self.master_blacklist['last_updated'] = datetime.now().isoformat()
        self.master_blacklist['total_bad_actors'] = blacklisted_count
        self.master_blacklist['total_losses_prevented_avax'] = total_losses

        # Sort by risk score
        self.master_blacklist['blacklisted_users'].sort(
            key=lambda x: x['risk_score'],
            reverse=True
        )

        print(f"\n{'#'*80}")
        print(f"# ✅ MASTER BLACKLIST COMPLETE")
        print(f"{'#'*80}")
        print(f"  Total Analyzed:        {len(wallet_addresses)}")
        print(f"  Blacklisted:          {blacklisted_count}")
        print(f"  Clean:                {len(wallet_addresses) - blacklisted_count}")
        print(f"  Losses Documented:    {total_losses:.2f} AVAX")
        print(f"{'#'*80}\n")

        return self.master_blacklist

    def save_master_blacklist(self):
        """Save the master blacklist to JSON"""
        filename = f"arena_master_blacklist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.master_blacklist, f, indent=2)
            print(f"✅ Master blacklist saved: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving master blacklist: {e}")
            return None

    def generate_safe_traders_list(self) -> Dict:
        """
        Generate a JSON list of wallet addresses with Arena names that are SAFE to follow
        This is the inverse - users NOT on the blacklist
        """
        safe_list = {
            'version': '1.0',
            'generated': datetime.now().isoformat(),
            'description': 'Arena wallets that are SAFE to follow (not on blacklist)',
            'safe_traders': [],
            'blacklisted_wallets': []
        }

        # Add all blacklisted wallets for reference
        for entry in self.master_blacklist['blacklisted_users']:
            safe_list['blacklisted_wallets'].append({
                'wallet': entry['wallet_address'],
                'arena_name': entry['arena_name'],
                'risk_score': entry['risk_score'],
                'do_not_follow': True
            })

        return safe_list

    def export_for_bots(self) -> str:
        """
        Export blacklist in format suitable for trading bots
        Simple JSON array of addresses to avoid
        """
        bot_blacklist = {
            'version': '1.0',
            'updated': datetime.now().isoformat(),
            'blacklisted_addresses': [],
            'high_risk_addresses': [],
            'medium_risk_addresses': []
        }

        for entry in self.master_blacklist['blacklisted_users']:
            wallet = entry['wallet_address']
            risk = entry['risk_score']

            if risk >= 80:
                bot_blacklist['blacklisted_addresses'].append(wallet)
            elif risk >= 60:
                bot_blacklist['high_risk_addresses'].append(wallet)
            else:
                bot_blacklist['medium_risk_addresses'].append(wallet)

        filename = f"arena_bot_blacklist_{datetime.now().strftime('%Y%m%d')}.json"

        with open(filename, 'w') as f:
            json.dump(bot_blacklist, f, indent=2)

        print(f"✅ Bot blacklist exported: {filename}")
        return filename


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("🛡️ ARENA COMPLETE BLACKLIST SYSTEM 🛡️")
    print("Protecting the community from ruggers, scammers, and bad actors")
    print("="*80 + "\n")

    # Configuration
    RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
    API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with actual key

    # Initialize master tracker
    tracker = ArenaCompleteTracker(RPC_URL, API_KEY)

    # Load known grifters
    known_grifters = tracker.load_known_grifters()
    grifter_wallets = [g['wallet_address'] for g in known_grifters.get('known_grifters', [])]

    # Add any additional suspicious wallets
    additional_wallets = known_grifters.get('additional_suspicious_wallets', [])
    if additional_wallets and additional_wallets[0] != "ADD_WALLET_ADDRESSES_FROM_DUNE_HERE":
        grifter_wallets.extend(additional_wallets)

    print(f"📋 Loaded {len(grifter_wallets)} known grifters from Dune Analytics data")
    print("Starting comprehensive analysis...\n")

    # Build master blacklist
    master_blacklist = tracker.build_master_blacklist(grifter_wallets)

    # Save all outputs
    tracker.save_master_blacklist()
    tracker.export_for_bots()

    # Print top offenders
    print("\n🚫 TOP 5 WORST OFFENDERS")
    print("="*80)

    for i, entry in enumerate(master_blacklist['blacklisted_users'][:5], 1):
        print(f"\n{i}. {entry['arena_name']}")
        print(f"   Wallet: {entry['wallet_address']}")
        print(f"   Risk Score: {entry['risk_score']}/100")
        print(f"   Tokens Created: {entry['evidence_summary']['tokens_deployed']}")
        print(f"   Victims: {entry['evidence_summary']['unique_victims']}")
        print(f"   Losses Caused: {entry['evidence_summary']['total_losses_avax']:.2f} AVAX")

    print("\n" + "="*80)
    print("✅ BLACKLIST GENERATION COMPLETE!")
    print(f"📁 Files created:")
    print(f"   - arena_master_blacklist_*.json (Complete blacklist with evidence)")
    print(f"   - arena_bot_blacklist_*.json (Simple list for trading bots)")
    print(f"   - known_grifters.json (Source data from Dune)")
    print("\n⚠️ IMPORTANT: Add wallet addresses from Dune Analytics to known_grifters.json")
    print("   Visit: https://dune.com/couchdicks/arenatrade-top-grifters")
    print("="*80)


if __name__ == "__main__":
    main()