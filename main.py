import json
import os
import traceback
from datetime import date

import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

URL = "https://www.bigfishgames.com/pc-bestsellers.html?sort_by=sales_rank_weekly&sort_dir=DESC&page=1"

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
            print(f"Found {count} elements for {selector}")

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
    print("First 10 scraped names:")
    for n in names[:10]:
        print(f"- {n}")

    return names[:100]

def write_to_sheet(game_names):
    print("Reading Google secrets...")
    raw_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    service_account_info = json.loads(raw_json)
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(creds)

    print("Opening spreadsheet file...")
    sh = client.open_by_key(sheet_id)
    print(f"Spreadsheet title: {sh.title}")

    print("Available tabs:")
    for ws in sh.worksheets():
        print(f"- {ws.title}")

    print("Opening Raw Data tab...")
    raw_ws = sh.worksheet("Raw Data")

    print("Clearing and writing Raw Data...")
    raw_rows = [["Game Name"]] + [[name] for name in game_names]
    raw_ws.clear()
    raw_ws.update(range_name="A1", values=raw_rows)
    print(f"Wrote {len(raw_rows)-1} game names to Raw Data")

    print("Opening Data Archive tab...")
    archive_ws = sh.worksheet("Data Archive")

    today = date.today().isoformat()
    print(f"Today is {today}")

    print("Reading existing archive values...")
    existing_values = archive_ws.get_all_values()
    print(f"Existing row count in Data Archive: {len(existing_values)}")

    rows_to_add = []
    if len(existing_values) == 0:
        rows_to_add.append(["Position", "Game Name", "Date"])
    elif len(existing_values) > 0:
        rows_to_add.append(["", "", ""])  # blank row before each new batch
    
    for i, name in enumerate(game_names, start=1):
        rows_to_add.append([i, name, today])

    next_row = len(existing_values) + 1
    required_last_row = next_row + len(rows_to_add) - 1
    
    if archive_ws.row_count < required_last_row:
        rows_needed = required_last_row - archive_ws.row_count
        print(f"Adding {rows_needed} rows to Data Archive...")
        archive_ws.add_rows(rows_needed)
    
    print(f"Writing {len(rows_to_add)} rows to Data Archive starting at row {next_row}...")
    archive_ws.update(range_name=f"A{next_row}", values=rows_to_add)

    print("Done writing both tabs.")

if __name__ == "__main__":
    try:
        games = scrape_game_names()
        if not games:
            raise Exception("No game names were scraped.")
        write_to_sheet(games)
        print("Script finished successfully.")
    except Exception as e:
        print("ERROR:")
        print(str(e))
        traceback.print_exc()
        raise
