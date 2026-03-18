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

from datetime import date
import gspread

def write_to_sheet(game_names):
    print("Reading Google secrets...")
    raw_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    service_account_info = json.loads(raw_json)
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(creds)

    print("Opening sheet...")
    sh = client.open_by_key(sheet_id)

    # --- RAW DATA TAB: replace every run ---
    try:
        raw_ws = sh.worksheet("Raw Data")
    except gspread.WorksheetNotFound:
        raw_ws = sh.sheet1
        raw_ws.update_title("Raw Data")

    raw_ws.clear()
    raw_ws.update("A1", [["Game Name"]] + [[name] for name in game_names])

    # --- DATA ARCHIVE TAB: append every run ---
    try:
        archive_ws = sh.worksheet("Data Archive")
    except gspread.WorksheetNotFound:
        archive_ws = sh.add_worksheet(title="Data Archive", rows=2000, cols=3)

    today = date.today().isoformat()

    # If the sheet is empty, add headers first
    existing_values = archive_ws.get_all_values()
    if not existing_values:
        archive_ws.update("A1", [["Position", "Game Name", "Date"]])

    # Build the new batch: 100 rows + 1 blank row
    rows_to_add = []
    for i, name in enumerate(game_names, start=1):
        rows_to_add.append([i, name, today])

    rows_to_add.append(["", "", ""])  # blank row after each daily batch

    archive_ws.append_rows(rows_to_add, value_input_option="RAW")

    print("Done writing Raw Data and appending Data Archive")
