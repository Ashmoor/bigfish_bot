import json
import os
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

URL = "https://www.bigfishgames.com/pc-bestsellers.html?sort_by=sales_rank_weekly&sort_dir=DESC&page=1"
SHEET_NAME = "BigFish Games"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def scrape_game_names():
    print("Starting browser...")
    names = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Opening {URL}")
        page.goto(URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(8000)

        selectors = ["h3", "h2", "a[title]", "a"]
        seen = set()

        for selector in selectors:
            print(f"Trying selector: {selector}")
            elements = page.locator(selector)
            count = elements.count()
            print(f"Found {count} elements")

            for i in range(count):
                try:
                    text = elements.nth(i).inner_text().strip()
                except Exception:
                    continue

                if not text or len(text) < 3:
                    continue

                bad = {
                    "buy now", "free trial", "download", "learn more",
                    "sign in", "register", "search", "games"
                }
                if text.lower() in bad:
                    continue

                if text not in seen:
                    seen.add(text)
                    names.append(text)

        browser.close()

    print(f"Scraped {len(names)} names")
    return names[:100]

def write_to_sheet(game_names):
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(creds)

    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    sh = client.open_by_key(sheet_id)

    ws = sh.sheet1
    ws.clear()
    ws.update("A1", [["Game Name"]] + [[name] for name in game_names])

if __name__ == "__main__":
    games = scrape_game_names()
    write_to_sheet(games)
    print(f"Wrote {len(games)} game names.")
