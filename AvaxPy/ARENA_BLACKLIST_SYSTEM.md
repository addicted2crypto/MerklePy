# 🛡️ Arena Community Safety Blacklist System

## Overview

A comprehensive Python-based system for tracking and blacklisting malicious token creators on the Arena platform (Avalanche C-Chain). This system protects the community by identifying users who:

- Create multiple tokens just to dump on buyers
- Profit off the community without waiting for others to profit
- Sell before token bonding completes
- Use multiple wallets to hide their dumps
- Consistently harm innocent buyers

## 🎯 Core Features

### 1. **Multi-Source Data Integration**
- ✅ On-chain transaction analysis via Snowtrace API
- ✅ Arena factory contract monitoring
- ✅ Dune Analytics grifter list integration
- ✅ Historical profit tracking with USD conversion
- ✅ Secondary wallet detection for hidden dumps

### 2. **Violation Detection**
The system detects and tracks these malicious behaviors:

| Violation Type | Description | Detection Method |
|----------------|-------------|------------------|
| **Serial Rugger** | Creates 3+ tokens to rug | Token deployment count analysis |
| **Quick Dumper** | Dumps within 5 minutes of launch | Time-based transaction analysis |
| **Pre-Bond Seller** | Sells before Dexscreener bonding | Bonding period violation check |
| **Self Pumper** | Buys >5 AVAX of own token | Deployer buy transaction tracking |
| **Liquidity Drainer** | Removes >80% of liquidity | Liquidity pool analysis |
| **Profit Only** | Never holds for community | Pattern analysis across tokens |
| **Sybil Network** | Uses multiple wallets | Wallet clustering & transfers |

### 3. **Community Damage Metrics**
- **Victim Count**: Unique wallets that lost money
- **Total Losses**: AVAX and USD value destroyed
- **Average Loss per Victim**: Impact per buyer
- **Rug Score**: 0-100 rating (higher = worse)
- **Time to Dump**: Average minutes before creator exit

### 4. **Output Formats**

#### JSON Blacklist (Machine-Readable)
```json
{
  "wallet_address": "0x123...",
  "arena_name": "@serial_rugger",
  "risk_score": 95,
  "violations": [...],
  "metrics": {
    "tokens_deployed": 2847,
    "unique_victims": 523,
    "total_losses_avax": 234.57
  }
}
```

#### Markdown Report (Human-Readable)
- Formatted reports with evidence
- Violation breakdowns
- Victim statistics
- Timestamped proof

#### CSV Export (Data Analysis)
- Excel-compatible format
- Historical tracking
- Trend analysis

## 📁 System Components

### Core Scripts

1. **`arenaBlacklistTracker.py`** (NEW)
   - Enhanced violation detection
   - Community damage metrics
   - Arena username mapping
   - Evidence collection system

2. **`arenaCompleteTracker.py`** (NEW)
   - Master integration system
   - Combines all data sources
   - Risk scoring algorithm
   - Bot-friendly exports

3. **`arenaProxyProfitTracker.py`** (EXISTING)
   - Factory deployment detection
   - Profit/loss calculations
   - Secondary wallet tracking
   - USD conversion with historical prices

4. **`arenaShitBagTracker.py`** (EXISTING)
   - Serial deployer detection
   - Pattern analysis
   - Basic blacklist management

### Supporting Files

5. **`known_grifters.json`**
   - Known bad actors from Dune Analytics
   - Manual addition support
   - Arena username mapping

6. **`add_dune_wallets.py`**
   - Helper to import Dune data
   - Interactive wallet addition
   - Quick bulk import mode

## 🚀 Installation & Setup

### Prerequisites

```bash
# Install required packages
pip install web3 requests

# Get Snowtrace API key
# Visit: https://snowtrace.io
# Create account and generate free API key
```

### Configuration

1. Edit the scripts and add your Snowtrace API key:
```python
API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with actual key
```

2. Add wallet addresses from Dune Analytics:
```bash
# Run the import helper
python add_dune_wallets.py

# Choose option 2 for quick import
# Paste wallet addresses from:
# https://dune.com/couchdicks/arenatrade-top-grifters
```

## 📊 Usage Examples

### Basic Usage - Analyze Known Grifters

```bash
python arenaCompleteTracker.py
```

This will:
1. Load known grifters from Dune data
2. Perform complete analysis on each wallet
3. Calculate risk scores
4. Generate blacklist with evidence
5. Export in multiple formats

### Add Wallets from Dune

```bash
python add_dune_wallets.py

# Option 1: Detailed (with usernames and notes)
# Option 2: Quick add (just addresses)
```

### Check Single Wallet

```python
from arenaBlacklistTracker import ArenaBlacklistTracker

tracker = ArenaBlacklistTracker(RPC_URL, API_KEY)
status = tracker.check_wallet_status("0x123...")

if status['blacklisted']:
    print(f"⚠️ BLACKLISTED: {status['arena_name']}")
    print(f"Risk Score: {status['rug_score']}/100")
    print(f"Reasons: {status['reasons']}")
```

### Generate Reports

```python
tracker.export_blacklist_csv()  # CSV for Excel
tracker.generate_markdown_report()  # Human-readable
tracker.export_for_bots()  # Simple JSON for bots
```

## 📈 Risk Scoring Algorithm

The system uses a 0-100 risk score:

| Score | Risk Level | Action |
|-------|-----------|--------|
| 80-100 | 🔴 EXTREME | Never buy - confirmed scammer |
| 60-79 | 🟠 HIGH | Avoid - likely to rug |
| 40-59 | 🟡 MEDIUM | Caution - suspicious patterns |
| 20-39 | 🟢 LOW | Monitor - some red flags |
| 0-19 | ⚪ MINIMAL | Probably safe |

### Scoring Factors
- Known grifter list: +50 points
- Serial deployment (50+ tokens): +30 points
- High profit from dumps: +20 points
- Many victims (10+): +20 points
- Quick dumping pattern: +10 points
- Pre-bonding sells: +10 points

## 🔍 Detection Examples

### Example 1: Serial Rugger
```
Wallet: 0x2Fe0...273e
Arena Name: @serial_rugger_01
Tokens Created: 2,847
Victims: 523
Total Losses: 234.57 AVAX ($7,283)
Risk Score: 95/100
Status: ❌ BLACKLISTED
```

### Example 2: Quick Dumper
```
Wallet: 0x2eE6...9dF
Violation: Dumped 15.2 AVAX within 180 seconds
Pattern: Consistent across 89% of tokens
Risk Score: 82/100
Status: ❌ BLACKLISTED
```

## 📋 Output Files

After running the complete tracker:

1. **`arena_master_blacklist_*.json`**
   - Complete blacklist with all evidence
   - Risk scores and violation details
   - Arena usernames

2. **`arena_bot_blacklist_*.json`**
   - Simple address arrays for trading bots
   - Categorized by risk level
   - Easy integration

3. **`arena_blacklist_*.csv`**
   - Spreadsheet format
   - Sortable/filterable
   - Data analysis ready

4. **`arena_blacklist_report_*.md`**
   - Human-readable report
   - Formatted for sharing
   - Complete evidence included

## ⚠️ Important Notes

### Data Sources
- **On-chain data**: Real, verifiable, cannot be faked
- **Dune Analytics**: Community-sourced, may need verification
- **Arena usernames**: Currently mocked, needs Arena API integration

### Limitations
- Requires Snowtrace API key (free tier works)
- Rate limited to prevent API bans
- Historical price data from CoinGecko
- Arena username mapping needs official API

### Future Enhancements
- [ ] Real Arena API integration for usernames
- [ ] Dexscreener bonding verification
- [ ] Real-time monitoring daemon
- [ ] Web interface for easy access
- [ ] Community reporting system
- [ ] Appeal process for reformed actors

## 🤝 Contributing

To add new detection patterns:

1. Add violation type to `violation_types` dict
2. Implement detection in `analyze_token_lifecycle()`
3. Update risk scoring algorithm
4. Test with known bad actors
5. Submit pull request

## 📜 License

MIT License - Use for defensive security only.

## ⚡ Quick Start

```bash
# 1. Clone the repository
git clone [repository]

# 2. Install dependencies
pip install web3 requests

# 3. Add your API key
# Edit scripts and add: API_KEY = "YOUR_KEY"

# 4. Add Dune wallets
python add_dune_wallets.py

# 5. Run the tracker
python arenaCompleteTracker.py

# 6. Check outputs
# - arena_master_blacklist_*.json
# - arena_bot_blacklist_*.json
# - arena_blacklist_report_*.md
```

## 🆘 Support

- Report issues: Create GitHub issue
- Add bad actors: Use `add_dune_wallets.py`
- Request features: Submit enhancement request

---

**Remember**: This system is for **community protection only**. Always DYOR before buying any token, even if not blacklisted.

Stay safe, Arena community! 🛡️