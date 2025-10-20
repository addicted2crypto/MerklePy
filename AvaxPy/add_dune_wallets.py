"""
Helper script to add wallet addresses from Dune Analytics to the known grifters list
"""

import json
import os

def add_wallets_from_dune():
    """
    Interactive script to add wallet addresses from Dune Analytics
    """
    print("\n" + "="*70)
    print("🔍 ADD WALLETS FROM DUNE ANALYTICS")
    print("="*70)
    print("\nThis tool helps you add wallet addresses from:")
    print("https://dune.com/couchdicks/arenatrade-top-grifters\n")

    # Load existing data
    try:
        with open('known_grifters.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: known_grifters.json not found!")
        return

    print("Current known grifters: ", len(data['known_grifters']))
    print("\nPaste wallet addresses from Dune (one per line).")
    print("Type 'DONE' when finished:\n")

    new_wallets = []
    while True:
        line = input("> ").strip()

        if line.upper() == 'DONE':
            break

        # Validate wallet address format
        if line.startswith('0x') and len(line) == 42:
            # Check if already exists
            exists = False
            for grifter in data['known_grifters']:
                if grifter['wallet_address'].lower() == line.lower():
                    print(f"  ⚠️ Already exists: {line}")
                    exists = True
                    break

            if not exists:
                new_wallets.append(line)
                print(f"  ✅ Added: {line}")
        elif line:
            print(f"  ❌ Invalid address format: {line}")

    if new_wallets:
        print(f"\n📝 Adding {len(new_wallets)} new wallet(s)...")

        # Get additional info for each wallet
        for wallet in new_wallets:
            print(f"\nWallet: {wallet}")
            arena_name = input("Arena username (or press Enter to skip): ").strip()
            tokens = input("Number of tokens created (or press Enter for 0): ").strip()
            profit = input("Total profit in AVAX (or press Enter for 0): ").strip()
            notes = input("Notes/reason for blacklist: ").strip()

            if not arena_name:
                arena_name = f"@grifter_{wallet[:8]}"

            try:
                tokens_count = int(tokens) if tokens else 0
                profit_avax = float(profit) if profit else 0.0
            except ValueError:
                tokens_count = 0
                profit_avax = 0.0

            entry = {
                "wallet_address": wallet,
                "arena_name": arena_name,
                "tokens_created": tokens_count,
                "total_profit_avax": profit_avax,
                "notes": notes or "Added from Dune Analytics"
            }

            data['known_grifters'].append(entry)

        # Save updated data
        with open('known_grifters.json', 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n✅ Successfully added {len(new_wallets)} wallet(s)")
        print(f"Total known grifters: {len(data['known_grifters'])}")
    else:
        print("\nNo new wallets added.")

    print("\n" + "="*70)


def quick_add_wallets():
    """
    Quick add multiple wallets without detailed info
    """
    print("\n" + "="*70)
    print("⚡ QUICK ADD WALLET ADDRESSES")
    print("="*70)
    print("\nPaste all wallet addresses (one per line):")
    print("Press Enter twice when done:\n")

    wallets = []
    empty_count = 0

    while empty_count < 2:
        line = input().strip()

        if not line:
            empty_count += 1
        else:
            empty_count = 0
            if line.startswith('0x') and len(line) == 42:
                wallets.append(line)

    if wallets:
        print(f"\n✅ Found {len(wallets)} valid addresses")

        # Load existing data
        try:
            with open('known_grifters.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {
                'description': 'Known malicious actors from Arena platform',
                'known_grifters': [],
                'additional_suspicious_wallets': []
            }

        # Add to additional suspicious wallets
        existing = set(w.lower() for w in data.get('additional_suspicious_wallets', []))

        added = 0
        for wallet in wallets:
            if wallet.lower() not in existing:
                if 'additional_suspicious_wallets' not in data:
                    data['additional_suspicious_wallets'] = []
                data['additional_suspicious_wallets'].append(wallet)
                added += 1

        # Save
        with open('known_grifters.json', 'w') as f:
            json.dump(data, f, indent=2)

        print(f"📝 Added {added} new wallet(s) to suspicious list")
        print(f"⚠️ Run the complete tracker to analyze these wallets")
    else:
        print("❌ No valid addresses found")


if __name__ == "__main__":
    print("\n🛡️ DUNE WALLET IMPORTER")
    print("="*70)
    print("\nChoose an option:")
    print("1. Add wallets with detailed info")
    print("2. Quick add (just addresses)")
    print("3. Exit")

    choice = input("\nSelect (1-3): ").strip()

    if choice == "1":
        add_wallets_from_dune()
    elif choice == "2":
        quick_add_wallets()
    else:
        print("Exiting...")

    print("\n✅ Done! You can now run arenaCompleteTracker.py to analyze all wallets.")