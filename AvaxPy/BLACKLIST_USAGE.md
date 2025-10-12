# Arena ShitBag Tracker - Blacklist Usage Guide

## Overview
The `arenaShitBagTracker.py` script now includes powerful serial deployer detection that automatically blacklists wallets deploying 50+ tokens with heavy profits.

## New Features Added

### 1. Serial Deployer Analysis
Detects and blacklists wallets that:
- Deployed **50+ tokens** (configurable)
- Made **10+ AVAX profit** from those tokens (configurable)

### 2. Batch Analysis
Analyze multiple wallets at once with detailed reporting.

### 3. Automatic Blacklisting
Wallets meeting the criteria are automatically added to the blacklist with:
- Total tokens deployed count
- Total AVAX profit
- List of profitable tokens (evidence)
- Timestamp of when flagged

## How to Use

### Testing Your 3 Wallet Addresses

```python
from arenaShitBagTracker import DeployerTokenTracker

# Initialize
RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
API_KEY = "YOUR_SNOWTRACE_API_KEY"
tracker = DeployerTokenTracker(RPC_URL, API_KEY)

# Your 3 test wallets
test_wallets = [
    "0xYOUR_WALLET_1",
    "0xYOUR_WALLET_2",
    "0xYOUR_WALLET_3"
]

# Run batch analysis
# These wallets deployed 50+ tokens each, so they should be flagged
results = tracker.batch_analyze_deployers(
    test_wallets,
    min_tokens=50,      # Minimum tokens threshold
    min_profit=10       # Minimum AVAX profit threshold
)

# Check results
print(f"Blacklisted: {tracker.get_blacklist_count()} wallets")

# Export to CSV
tracker.export_blacklist()
```

### Analyze a Single Wallet

```python
tracker.analyze_serial_deployer(
    "0xWALLET_ADDRESS",
    min_tokens=50,
    min_profit=10
)
```

### Check if Wallet is Blacklisted

```python
if tracker.is_blacklisted("0xWALLET_ADDRESS"):
    print("This wallet is blacklisted!")
```

## Blacklist Criteria

A wallet is automatically blacklisted if it meets **BOTH** conditions:

1. **Token Count**: Deployed ≥ 50 tokens (ERC20 contracts)
2. **Profit**: Made ≥ 10 AVAX in total profit from those tokens

You can adjust these thresholds:
```python
tracker.analyze_serial_deployer(
    wallet,
    min_tokens=100,     # Stricter: require 100+ tokens
    min_profit=50       # Stricter: require 50+ AVAX profit
)
```

## Output Format

### Console Output
```
============================================================
[ANALYZING SERIAL DEPLOYER] 0xABC123...
============================================================
[INFO] Total contracts deployed: 75
[INFO] Analyzing profit from 75 tokens...
  Analyzing token 1/75: 0xDEF456...
  ...

[RESULTS]
  Tokens deployed: 75
  Profitable tokens: 42
  Total profit: 125.4567 AVAX

[BLACKLISTED] 0xABC123...
  Reason: Serial deployer: 75 tokens deployed, 125.46 AVAX profit
```

### Blacklist JSON Structure
```json
{
  "wallets": [
    {
      "address": "0xabc123...",
      "reason": "Serial deployer: 75 tokens deployed, 125.46 AVAX profit",
      "evidence": {
        "deployer": "0xabc123...",
        "total_contracts_deployed": 75,
        "profitable_tokens": 42,
        "total_profit_avax": 125.4567,
        "sample_profitable_tokens": [...],
        "pattern": "serial_deployer_with_profit",
        "threshold_tokens": 50,
        "threshold_profit": 10
      },
      "timestamp": "2025-10-09T12:34:56",
      "flagged_by": "arenaShitBagTracker"
    }
  ]
}
```

### CSV Export
Exports to timestamped CSV file:
- `blacklist_export_YYYYMMDD_HHMMSS.csv`

Columns:
- address
- reason
- timestamp
- pattern

## API Requirements

Get a free API key from [snowtrace.io](https://snowtrace.io/apis)

**Rate Limits**: Script includes automatic delays (0.2s per token, 1s per wallet) to avoid hitting API limits.

## Example Workflow

```python
# 1. Initialize tracker
tracker = DeployerTokenTracker(RPC_URL, API_KEY)

# 2. Test your 3 serial deployer wallets
test_wallets = ["0xWALLET1", "0xWALLET2", "0xWALLET3"]
tracker.batch_analyze_deployers(test_wallets, min_tokens=50, min_profit=10)

# 3. Check blacklist
print(f"Total blacklisted: {tracker.get_blacklist_count()}")

# 4. View details
for entry in tracker.wallet_blacklist['wallets']:
    print(f"{entry['address']}: {entry['reason']}")

# 5. Export for sharing
tracker.export_blacklist()
```

## Advanced Usage

### Combine Multiple Detection Methods

```python
# Method 1: Serial deployer detection
tracker.analyze_serial_deployer(wallet, min_tokens=50, min_profit=10)

# Method 2: Selling into buy volume detection
tracker.track_token_deployer(token_address)

# Both methods will add to the same blacklist
```

### Custom Thresholds for Different Scenarios

```python
# Strict mode - only flag serious offenders
tracker.batch_analyze_deployers(wallets, min_tokens=100, min_profit=100)

# Permissive mode - flag more wallets
tracker.batch_analyze_deployers(wallets, min_tokens=25, min_profit=5)
```

## Notes

- **Performance**: Analyzing 50+ tokens per wallet can take several minutes due to API calls
- **Accuracy**: Profit calculation is based on token transfer values - may not be 100% accurate for complex trading patterns
- **Rate Limiting**: Built-in delays prevent API throttling
- **Persistence**: Blacklist automatically saved to `wallet_blacklist.json` after each addition

## Expected Results for Your Test Wallets

If your 3 wallets each deployed 50+ tokens and profited heavily:
- All 3 should be automatically flagged
- Each entry will show exact token count and AVAX profit
- Evidence includes up to 10 sample profitable tokens
- Blacklist saved to JSON and exportable to CSV
