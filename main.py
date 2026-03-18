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
    names = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(5000)

        # Try common title selectors
        selectors = [
            "h3",
            "h2",
            "a[title]",
            "a",
        ]

        seen = set()

        for selector in selectors:
            elements = page.locator(selector)
            count = elements.count()

            for i in range(count):
                try:
                    text = elements.nth(i).inner_text().strip()
                except:
                    continue

                if not text:
                    continue
                if len(text) < 3:
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

    # Keep first 100 likely titles
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
