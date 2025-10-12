# Arena Proxy Profit Tracker

Comprehensive tool for tracking token deployments and profits through the Arena proxy deployer on Avalanche C-Chain.

## Overview

This tracker analyzes wallet addresses that deploy tokens through the Arena proxy (`0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c`) to:

1. **Track all token deployments** - Identifies every token contract deployed by target wallets
2. **Calculate profits in AVAX and USD** - Tracks buys and sells with historical AVAX/USD conversion
3. **Detect secondary wallet dumps** - Finds hidden token transfers to secondary wallets used for concealed selling
4. **Flag buy limit violations** - Identifies deployers who bought >5 AVAX worth and dumped
5. **Generate blacklist entries** - Creates evidence-based blacklist entries for serial deployers

## Features

### Core Tracking
- ✅ Token deployment detection via contract creation transactions
- ✅ Buy/sell transaction analysis with AVAX amounts
- ✅ USD profit calculation using historical AVAX prices from CoinGecko
- ✅ Secondary wallet detection (transfers from deployer to low-activity wallets)
- ✅ Aggregated profit metrics across all deployments

### Advanced Detection
- ✅ **Secondary wallet tracking**: Detects when deployers transfer tokens to other wallets to hide dumps
- ✅ **Buy limit violations**: Flags deployers who bought >5 AVAX and dumped for profit
- ✅ **Multi-wallet aggregation**: Combines metrics across multiple deployer wallets
- ✅ **Success rate calculation**: Percentage of profitable vs unprofitable tokens

### Future Enhancements
- ⏳ **Dexscreener bonding check**: Verify if token bonded before deployer dumped (requires API integration)
- ⏳ **Social media tracking**: Track Twitter spaces and influencer posts during launches
- ⏳ **Liquidity drain detection**: Identify when dumps drained significant liquidity

## Installation

### Requirements
```bash
pip install web3 requests
```

### Configuration

1. **Get a Snowtrace API Key**
   - Visit [Snowtrace.io](https://snowtrace.io)
   - Create account and generate API key
   - Free tier is sufficient for most use cases

2. **Update Configuration**
   Edit `arenaProxyProfitTracker.py`:
   ```python
   API_KEY = "YOUR_SNOWTRACE_API_KEY"  # Replace with your actual key

   # Target wallets from your RAW_CLUSTER
   TARGET_WALLETS = [
       "0xb5b005c1d3e90c73375331f65bc52793c7d29325",  # Wallet 5
       "0x4aa0bf91f6e482e4048e3759f77ae806cd4cfb14",  # Wallet 6
   ]
   ```

## Usage

### Basic Usage

Run the tracker:
```bash
python arenaProxyProfitTracker.py
```

This will:
1. Scan all token deployments for each target wallet
2. Analyze buy/sell transactions for each token
3. Calculate profits in AVAX and USD
4. Detect secondary wallets used for dumps
5. Generate comprehensive reports
6. Export results to JSON
7. Create blacklist entries for qualifying wallets

### Output Files

- **JSON Report**: `arena_profit_report_YYYYMMDD_HHMMSS.json`
  - Complete analysis data
  - Individual token breakdown
  - Buy/sell transaction details
  - Secondary wallet information

### Example Output

```
######################################################################
# ARENA PROXY PROFIT TRACKER
# Analyzing 2 wallets
# Arena Proxy: 0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c
######################################################################

======================================================================
ANALYZING WALLET: 0xb5b005c1d3e90c73375331f65bc52793c7d29325
======================================================================

[SCANNING] Finding deployed tokens for 0xb5b005c1...
[INFO] Found 3450 total transactions
  ✓ Found token: 0x1234abcd... (Block: 12345678)
  ✓ Found token: 0x5678efgh... (Block: 12345890)
  ...
[RESULT] Total tokens deployed: 2847

[PROFIT ANALYSIS] Analyzing 2847 tokens...

  [1/2847] Token: 0x1234abcd...
    [ANALYZING] Token 0x1234abcd...
    [TRACKING] Looking for secondary wallets...
      → Found potential secondary: 0x9876zyxw... (47 txs)
      [SECONDARY] Analyzing 0x9876zyxw...
      Buys: 3 | Sells: 5 + 2 secondary
      Profit: 12.4567 AVAX ($387.23 USD)
      Secondary Profit: 3.2100 AVAX ($99.87 USD)

======================================================================
WALLET SUMMARY: 0xb5b005c1...
======================================================================
  Tokens Deployed:       2847
  Tokens Analyzed:       2847
  Profitable Tokens:     1523
  Total Profit:          234.5678 AVAX ($7,283.45 USD)
  Avg Profit/Token:      0.0824 AVAX ($2.56 USD)
  Success Rate:          53.5%
  Secondary Wallets:     127
======================================================================

######################################################################
# COMBINED SUMMARY - ALL WALLETS
######################################################################
  Wallets Analyzed:          2
  Total Tokens Deployed:     5234
  Total Tokens Analyzed:     5234
  Total Profitable Tokens:   2891
  COMBINED PROFIT:           456.7890 AVAX ($14,187.23 USD)
  Avg Profit per Wallet:     228.3945 AVAX ($7,093.62 USD)
  Overall Success Rate:      55.2%
  Total Secondary Wallets:   243
######################################################################

======================================================================
BLACKLIST EVALUATION
======================================================================

[BLACKLIST] 0xb5b005c1d3e90c73375331f65bc52793c7d29325
  Reason: Arena deployer: 2847 tokens deployed, $7283.45 USD profit (234.57 AVAX)
  Secondary Wallets Used: 127

======================================================================
CHECKING BUY LIMIT VIOLATIONS (>5 AVAX)
======================================================================

[VIOLATION] 0xb5b005c1...
  Token: 0x1234abcd...
  Bought: 8.50 AVAX (limit: 5.0)
  Sold: 12.34 AVAX
  Profit: 3.84 AVAX ($119.23)
  Secondary dumps: 1

Total violations found: 47

======================================================================
TOP 10 MOST PROFITABLE TOKENS - 0xb5b005c1...
======================================================================

1. Token: 0x1234abcdef1234567890abcdef1234567890abcd
   Deployed: 2024-03-15T14:23:45
   Buys: 3 | Sells: 5 (Primary)
   Secondary Sells: 2 via 1 wallets
   Spent: 2.5000 AVAX ($77.50)
   Received: 15.2340 AVAX ($472.55)
   PROFIT: 12.7340 AVAX ($395.05)

2. Token: 0x5678efgh5678901234ijklmn5678901234ijklmn
   Deployed: 2024-03-14T09:12:33
   Buys: 2 | Sells: 3 (Primary)
   Spent: 1.2000 AVAX ($37.20)
   Received: 8.9870 AVAX ($278.60)
   PROFIT: 7.7870 AVAX ($241.40)

...

======================================================================
ANALYSIS COMPLETE
======================================================================

Blacklist Entries: 2
Buy Limit Violations: 47

Note: Dexscreener bonding check not yet implemented.
      Currently flagging dumps that recovered 80%+ of buy value.
======================================================================
```

## Understanding the Metrics

### Profit Calculation
- **AVAX Profit** = (Total AVAX Received from Sells) - (Total AVAX Spent on Buys)
- **USD Profit** = Calculated using historical AVAX/USD prices at transaction times
- **Secondary Profits** = Profits from tokens sold via secondary wallets (included in totals)

### Success Rate
- **Success Rate** = (Profitable Tokens / Total Tokens Analyzed) × 100
- A token is "profitable" if AVAX profit > 0

### Buy Limit Violations
- Flags tokens where deployer bought >5 AVAX worth
- Only counts if they dumped ≥80% of the buy value
- Indicates deployer was buying their own ticker to pump before dumping

### Secondary Wallet Detection
- Looks for token transfers from deployer to low-activity wallets (<100 transactions)
- Tracks sales from those wallets to capture hidden dumps
- Common tactic: Deploy → Buy → Transfer to alt → Dump from alt to hide identity

## Blacklist Criteria

Wallets are automatically flagged for blacklisting if they meet ANY of these criteria:

1. **High Token Count**: Deployed ≥2500 tokens (configurable)
2. **High Profit**: Made ≥$50 USD profit combined (configurable)
3. **Secondary Wallet Usage**: Using multiple wallets to hide dumps

### Blacklist Entry Format
```json
{
  "address": "0xb5b005c1d3e90c73375331f65bc52793c7d29325",
  "reason": "Arena deployer: 2847 tokens deployed, $7283.45 USD profit (234.57 AVAX)",
  "evidence": {
    "tokens_deployed": 2847,
    "tokens_analyzed": 2847,
    "profitable_tokens": 1523,
    "total_profit_avax": 234.5678,
    "total_profit_usd": 7283.45,
    "success_rate": 53.5,
    "secondary_wallets_used": 127,
    "pattern": "arena_serial_deployer",
    "arena_proxy": "0xc605c2cf66ee98ea925b1bb4fea584b71c00cc4c"
  },
  "timestamp": "2024-03-20T15:30:45.123456",
  "flagged_by": "ArenaProxyProfitTracker"
}
```

## Customization

### Adjust Blacklist Thresholds
```python
blacklist_entries = tracker.generate_blacklist_entries(
    min_tokens=5000,      # Minimum token deployments
    min_profit_usd=100.0  # Minimum USD profit
)
```

### Change Buy Limit
```python
buy_violations = tracker.check_buy_limit_violations(
    min_buy_limit=10.0  # Flag buys >10 AVAX instead of 5
)
```

### Analyze Different Wallets
```python
TARGET_WALLETS = [
    "0xYourWalletAddress1",
    "0xYourWalletAddress2",
    # Add more wallets...
]
```

## API Rate Limits

### Snowtrace API
- Free tier: 5 calls/second, 100,000 calls/day
- Script includes automatic rate limiting (0.1-0.3s delays)
- For 5000+ tokens, expect ~2-4 hours runtime

### CoinGecko API
- Free tier: 10-50 calls/minute
- Prices are cached by day to minimize calls
- Falls back to current price if historical data unavailable

## Integration with Blacklist System

To integrate with existing `arenaShitBagTracker.py`:

```python
from arenaShitBagTracker import DeployerTokenTracker
from arenaProxyProfitTracker import ArenaProxyProfitTracker

# Initialize both trackers
arena_tracker = ArenaProxyProfitTracker(RPC_URL, API_KEY, ARENA_PROXY)
blacklist_tracker = DeployerTokenTracker(RPC_URL, API_KEY)

# Run analysis
results = arena_tracker.analyze_multiple_wallets(TARGET_WALLETS)

# Generate blacklist entries
entries = arena_tracker.generate_blacklist_entries(min_tokens=2500, min_profit_usd=50.0)

# Add to main blacklist
for entry in entries:
    blacklist_tracker.add_to_blacklist(
        entry['address'],
        entry['reason'],
        entry['evidence']
    )
```

## Troubleshooting

### "No token deployments found"
- Check wallet address is correct and checksummed
- Verify wallet actually deployed contracts
- Check Snowtrace API key is valid

### "Could not fetch AVAX price"
- CoinGecko API may be rate limited
- Script will fall back to current price (~$30)
- Historical prices are cached to reduce calls

### "Error fetching transactions"
- Snowtrace API rate limit reached (wait 1 minute)
- API key invalid or expired
- Network connectivity issues

### Script runs slowly
- Normal for wallets with thousands of deployments
- Each token requires multiple API calls
- Rate limiting prevents API bans
- For 5000 tokens: expect 2-4 hours

## Future Enhancements

### Planned Features
1. **Dexscreener Bonding Integration**
   - Check if token bonded to Dexscreener before deployer dumped
   - Requires Dexscreener API or on-chain bonding contract analysis

2. **Social Media Tracking**
   - Track Twitter/X spaces during token launches
   - Monitor influencer posts and shills
   - Correlate social activity with dumps

3. **Liquidity Analysis**
   - Calculate % of liquidity drained by deployer sells
   - Flag catastrophic liquidity removal events
   - Track liquidity provider (LP) positions

4. **Real-time Monitoring**
   - Watch for new deployments from flagged wallets
   - Alert on suspicious activity
   - Live profit tracking

## Contributing

To add new detection patterns or features:

1. Fork the repository
2. Add your feature to `ArenaProxyProfitTracker` class
3. Update this README with usage examples
4. Test with known deployer wallets
5. Submit pull request

## License

MIT License - Use freely for defensive security and research purposes only.

## Disclaimer

This tool is for **defensive security research only**. Do not use for malicious purposes, harassment, or doxxing. Analyze publicly available blockchain data responsibly.

---

**Author**: Claude Code
**Version**: 1.0
**Last Updated**: 2025-10-09
