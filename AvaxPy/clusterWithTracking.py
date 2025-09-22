
import logging
from decimal import Decimal
from typing import Tuple, Optional, List, Dict, Set
import requests
import networkx as nx
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


AVAX_RPC_URL = "https://api.avax.network/ext/bc/C/rpc"
TOKEN_ADDRESS = "0xC654721fBf1F374fd9FfA3385Bba2F4932A6af55"

RAW_CLUSTER = [
    "0x2Fe09e93aCbB8B0dA86C394335b8A92d3f5E273e",
    "0x2eE647714bF12c5B085B9aeD44f559825A57b9dF",
    "0x139d124813afCA73D7d71354bFe46DB3dA59702B",
    "0xF8d4dD1854bB60950305Af12Fd72B7a547734b12",
    
]


BLOCK_WINDOW = 50_000
EARLY_BUYER_LIMIT = 15

DEXSCREENER_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/{}"


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("avax_cluster_tracker")

w3 = Web3(Web3.HTTPProvider(AVAX_RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    logger.error("Cannot connect to AVAX RPC: %s", AVAX_RPC_URL)
    raise SystemExit(1)

TOKEN_ADDRESS = Web3.to_checksum_address(TOKEN_ADDRESS)
CLUSTER = [Web3.to_checksum_address(a) for a in RAW_CLUSTER]


ERC20_MIN_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "balance", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"anonymous": False, "inputs": [{"indexed": True, "name": "from", "type": "address"},
                                   {"indexed": True, "name": "to", "type": "address"},
                                   {"indexed": False, "name": "value", "type": "uint256"}],
     "name": "Transfer", "type": "event"},
]

token_contract = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_MIN_ABI)


def get_token_decimals(contract) -> int:
    try:
        return int(contract.functions.decimals().call())
    except Exception as e:
        logger.warning("decimals() failed, defaulting to 18: %s", e)
        return 18


def get_avax_balance(addr: str) -> Decimal:
    wei = w3.eth.get_balance(addr)
    return Decimal(w3.from_wei(wei, "ether"))


def get_token_balance(contract, addr: str, decimals: int) -> Decimal:
    raw = contract.functions.balanceOf(addr).call()
    return Decimal(raw) / Decimal(10 ** decimals)


def get_token_price_dexscreener(token_addr: str) -> Optional[Decimal]:
    try:
        resp = requests.get(DEXSCREENER_TOKEN_URL.format(token_addr), timeout=8)
        resp.raise_for_status()
        pairs = resp.json().get("pairs", [])
        for p in pairs:
            price = p.get("priceNative")
            if price:
                return Decimal(str(price))
        return None
    except Exception as e:
        logger.debug("Dexscreener price error: %s", e)
        return None


def find_contract_creation(token_addr: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Binary-search the first block where code(token_addr) != empty, then scan that block's txs
    to find the creation tx. Returns (deployer, tx_hash_hex, creation_block).
    """
    token_addr = Web3.to_checksum_address(token_addr)
    latest = w3.eth.block_number
    if not w3.eth.get_code(token_addr):
        return None, None, None

    low, high = 0, latest
    while low < high:
        mid = (low + high) // 2
        code_mid = w3.eth.get_code(token_addr, block_identifier=mid)
        if code_mid and len(code_mid) > 0:
            high = mid
        else:
            low = mid + 1
    creation_block = low
    block = w3.eth.get_block(creation_block, full_transactions=True)
    for tx in block.transactions:
        if tx.get("to") is None:
            try:
                receipt = w3.eth.get_transaction_receipt(tx.hash)
                if receipt.contractAddress and Web3.to_checksum_address(receipt.contractAddress) == token_addr:
                    return Web3.to_checksum_address(tx["from"]), receipt.transactionHash.hex(), creation_block
            except Exception:
                continue
    return None, None, creation_block


def get_early_buyers(token_addr: str, creation_block: int, window: int = 10_000, limit: int = 10) -> List[str]:
    """Return first unique buyer addresses seen in Transfer events after creation_block."""
    from_block = creation_block
    to_block = min(creation_block + window, w3.eth.block_number)
    try:
        event = token_contract.events.Transfer()
        logs = event.get_logs(from_block=from_block, to_block=to_block)
    except Exception as e:
        logger.warning("get_early_buyers get_logs failed: %s", e)
        return []

    buyers: List[str] = []
    for log in logs:
        to_addr = log["args"]["to"]
        if to_addr not in buyers:
            buyers.append(Web3.to_checksum_address(to_addr))
        if len(buyers) >= limit:
            break
    return buyers


def fetch_transfers(token_contract, from_block: int, to_block: int):
    """
    Fetch Transfer events for the token in [from_block, to_block].
    Returns list of dicts with 'from','to','value','blockNumber'.
    NOTE: large windows may return many logs -> consider using an indexer for long ranges.
    """
    try:
        ev = token_contract.events.Transfer()
        logs = ev.get_logs(from_block=from_block, to_block=to_block)
    except Exception as e:
        logger.error("fetch_transfers get_logs failed: %s", e)
        return []

    transfers = []
    for l in logs:
        transfers.append({
            "from": Web3.to_checksum_address(l["args"]["from"]),
            "to": Web3.to_checksum_address(l["args"]["to"]),
            "value": int(l["args"]["value"]),
            "block": int(l["blockNumber"])
        })
    return transfers



def build_transfer_graph(transfers: List[Dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    wallet_blocks: Dict[str, Set[int]] = {}

    for t in transfers:
        a = t["from"]
        b = t["to"]
        v = t["value"]
        blk = t["block"]

      
        if int(a, 16) == 0:
            continue

        if not G.has_node(a):
            G.add_node(a)
        if not G.has_node(b):
            G.add_node(b)

        if G.has_edge(a, b):
            G[a][b]["value"] += v
            G[a][b]["count"] += 1
            G[a][b]["blocks"].add(blk)
        else:
            G.add_edge(a, b, value=v, count=1, blocks={blk})

        wallet_blocks.setdefault(a, set()).add(blk)
        wallet_blocks.setdefault(b, set()).add(blk)


    G.graph["wallet_blocks"] = wallet_blocks
    return G


def compute_similarity_scores(G: nx.DiGraph, wallets: List[str], decimals: int) -> Dict[Tuple[str, str], float]:
    """
    For each pair of wallets in `wallets`, compute a similarity/probability score [0..1]
    that indicates how likely the two wallets are controlled by the same entity.
    Features used (simple heuristic):
      - Jaccard of counterparties (shared counterparties / union)
      - Direct transferred value between the pair (normalized)
      - Direct transfer count between the pair (normalized)
      - Same-block co-occurrence count (normalized)
    This returns pairwise scores.
    """
    
    wallet_partners: Dict[str, Set[str]] = {}
    wallet_blocks: Dict[str, Set[int]] = G.graph.get("wallet_blocks", {})

    for w in wallets:
        partners = set()
        if G.has_node(w):
            partners.update({n for n in G.successors(w)})
            partners.update({n for n in G.predecessors(w)})
        wallet_partners[w] = partners

    pairs = []
    raw_metrics = []
    for i in range(len(wallets)):
        for j in range(i + 1, len(wallets)):
            a, b = wallets[i], wallets[j]
            val_ab = G[a][b]["value"] if G.has_edge(a, b) else 0
            val_ba = G[b][a]["value"] if G.has_edge(b, a) else 0
            direct_value = val_ab + val_ba

            count_ab = G[a][b]["count"] if G.has_edge(a, b) else 0
            count_ba = G[b][a]["count"] if G.has_edge(b, a) else 0
            direct_count = count_ab + count_ba

        
            pa = wallet_partners.get(a, set())
            pb = wallet_partners.get(b, set())
            union = pa.union(pb)
            inter = pa.intersection(pb)
            jaccard = len(inter) / len(union) if union else 0.0

    
            blocks_a = wallet_blocks.get(a, set())
            blocks_b = wallet_blocks.get(b, set())
            same_block_count = len(blocks_a.intersection(blocks_b)) if blocks_a and blocks_b else 0

            pairs.append((a, b, direct_value, direct_count, jaccard, same_block_count))
            raw_metrics.append((direct_value, direct_count, jaccard, same_block_count))

    if not raw_metrics:
        return {}

    max_direct_value = max(m[0] for m in raw_metrics) or 1
    max_direct_count = max(m[1] for m in raw_metrics) or 1
    max_jaccard = 1 
    max_same_block = max(m[3] for m in raw_metrics) or 1

    scores = {}
    for (a, b, direct_value, direct_count, jaccard, same_block_count) in pairs:
     
        nv = direct_value / max_direct_value
        nc = direct_count / max_direct_count
        nj = jaccard 
        ns = same_block_count / max_same_block

     
        score = (0.35 * nj) + (0.35 * nv) + (0.2 * nc) + (0.1 * ns)
        score = max(0.0, min(1.0, score))
        scores[(a, b)] = score
        scores[(b, a)] = score 

    return scores



def human_readable_value(raw: int, decimals: int) -> Decimal:
    return Decimal(raw) / Decimal(10 ** decimals)


def run_full_report():
    decimals = get_token_decimals(token_contract)
    deployer, tx_hash, creation_block = find_contract_creation(TOKEN_ADDRESS)
    logger.info("Token decimals=%s, creation_block=%s, deployer=%s", decimals, creation_block, deployer)

   
    expanded = CLUSTER.copy()
    if deployer:
        expanded.append(deployer)
        early = get_early_buyers(TOKEN_ADDRESS, creation_block, window=BLOCK_WINDOW, limit=EARLY_BUYER_LIMIT)
        logger.info("Early buyers discovered: %d", len(early))
        expanded.extend(early)
    expanded = list(dict.fromkeys(expanded)) 

    total_avax, total_token = Decimal(0), Decimal(0)
    rows = []
    for w in expanded:
        try:
            av = get_avax_balance(w)
            tk = get_token_balance(token_contract, w, decimals)
            rows.append((w, av, tk))
            total_avax += av
            total_token += tk
        except Exception as e:
            logger.warning("Failed fetch balance for %s: %s", w, e)

    rows.sort(key=lambda r: r[2], reverse=True)
    print("\n--- Balances (expanded cluster) ---")
    for w, av, tk in rows:
        print(f"{w[:8]}...{w[-6:]} | AVAX: {av:.4f} | Token: {tk:.6f}")

    print(f"\nTotals: AVAX={total_avax:.4f}, Token={total_token:.6f}")

    from_block = creation_block
    to_block = min(creation_block + BLOCK_WINDOW, w3.eth.block_number)
    logger.info("Fetching transfers from %s to %s", from_block, to_block)
    transfers = fetch_transfers(token_contract, from_block, to_block)
    logger.info("Fetched %d transfers", len(transfers))

    G = build_transfer_graph(transfers)

    scores = compute_similarity_scores(G, expanded, decimals)

    if not scores:
        print("\nNo pairwise similarity scores (no transfer data for range).")
        return

    print("\n--- Pairwise similarity scores (0..100%) ---")
    printed = set()
    for (a, b), s in scores.items():
        if (b, a) in printed:
            continue
        if a == b:
            continue
        print(f"{a[:8]}... {b[:8]}... => {s*100:.1f}%")
        printed.add((a, b))
        printed.add((b, a))

   
    agg = {}
    for w in expanded:
        vals = []
        for w2 in expanded:
            if w != w2:
                vals.append(scores.get((w, w2), 0.0))
        agg_score = (sum(vals) / len(vals)) if vals else 0.0
        agg[w] = agg_score

    print("\n--- Per-wallet aggregated probability (0..100%) ---")
    for w, sc in sorted(agg.items(), key=lambda x: x[1], reverse=True):
        print(f"{w[:8]}... => {sc*100:.2f}%")


    threshold = 0.4  
    suggestions = []
    for w in agg:
       
        vals = [scores.get((w, c), 0.0) for c in CLUSTER if c != w]
        avg_to_manual = (sum(vals) / len(vals)) if vals else 0.0
        if avg_to_manual >= threshold and w not in CLUSTER:
            suggestions.append((w, avg_to_manual))
    if suggestions:
        print("\n--- Suggested wallets to consider adding to your manual cluster ---")
        for w, v in sorted(suggestions, key=lambda x: x[1], reverse=True):
            print(f"{w[:8]}... => avg similarity {v*100:.1f}%")

    
    return {
        "rows": rows,
        "totals": {"avax": total_avax, "token": total_token},
        "transfers_count": len(transfers),
        "graph": G,
        "pair_scores": scores,
        "agg_scores": agg,
        "suggestions": suggestions,
    }


if __name__ == "__main__":
  
    run_full_report()
