import requests
from bs4 import BeautifulSoup
import time

# Token ID (example)
TOKEN_ID = "0x3C5f68d2F72DEBBa4900c60f32EB8629876401f2"
EXPLORER_URL = f"https://snowtrace.io/token/{TOKEN_ID}"

def scrape_avalanche_explorer():
    try:
        res = requests.get(EXPLORER_URL)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Extract owner wallet
        owner = soup.find('span', text='Owner').find_next_sibling('span').text.strip()

        # Extract transactions
        txs = soup.find_all('tr', class_='tx-row')
        large_transfers = 0
        for tx in txs:
            value = tx.find('td', class_='tx-value').text.strip()
            if float(value) > 1000000000000000000:  # > 1 AVAX
                large_transfers += 1

        return {
            "owner": owner,
            "large_transfers": large_transfers,
            "total_txs": len(txs)
        }
    except Exception as e:
        return {"error": str(e)}

# Main loop
def main():
    while True:
        print("Scraping Avalanche Explorer...")
        data = scrape_avalanche_explorer()
        if "error" in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Owner: {data['owner']}")
            print(f"Large transfers: {data['large_transfers']}")
            if data['large_transfers'] > 5:
                print("🚨 RUG DETECTED: 5+ large transfers")
            else:
                print("✅ Safe: No rug detected")
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    main()