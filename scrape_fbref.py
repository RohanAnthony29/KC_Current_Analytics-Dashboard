"""
Scrape FBref KC Current player stats using undetected-chromedriver.
This bypasses Cloudflare by using a patched ChromeDriver that looks like a real browser.
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time, os, sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
PROC_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")

URLS = {
    "2024": "https://fbref.com/en/squads/6f666306/2024/Kansas-City-Current-Stats",
    "2023": "https://fbref.com/en/squads/6f666306/2023/Kansas-City-Current-Stats",
}

def scrape_season(driver, url, season):
    """Navigate to FBref and extract the Standard Stats table."""
    print(f"\n{'='*50}")
    print(f"Scraping season {season}...")
    print(f"URL: {url}")
    
    driver.get(url)
    
    # Wait for the page to load past Cloudflare
    time.sleep(8)
    
    # Check if we got past Cloudflare
    title = driver.title
    print(f"Page title: {title}")
    
    if "Just a moment" in title or "Cloudflare" in title:
        print("  ⏳ Still on Cloudflare challenge, waiting longer...")
        time.sleep(15)
        title = driver.title
        print(f"  Page title after wait: {title}")
    
    if "Kansas City" not in title and "Stats" not in title:
        print(f"  ❌ Failed to load page. Title: {title}")
        # Save whatever HTML we got for debugging
        html_path = os.path.join(DATA_DIR, f"fbref_{season}_debug.html")
        with open(html_path, "w") as f:
            f.write(driver.page_source)
        print(f"  Saved debug HTML to {html_path}")
        return pd.DataFrame()
    
    print("  ✅ Page loaded successfully!")
    
    # Save the full HTML
    html_path = os.path.join(DATA_DIR, f"fbref_{season}.html")
    with open(html_path, "w") as f:
        f.write(driver.page_source)
    print(f"  Saved HTML to {html_path}")
    
    # Try to extract the stats table using JavaScript
    try:
        result = driver.execute_script("""
            var table = document.querySelector('#stats_standard_combined') || 
                        document.querySelector('#stats_standard_11160') ||
                        document.querySelector('table.stats_table');
            if (!table) return JSON.stringify({error: 'No table found', tableCount: document.querySelectorAll('table').length});
            
            var headers = Array.from(table.querySelectorAll('thead tr:last-child th')).map(function(th) {
                return th.textContent.trim();
            });
            
            var rows = Array.from(table.querySelectorAll('tbody tr:not(.thead)')).map(function(tr) {
                return Array.from(tr.querySelectorAll('th, td')).map(function(td) {
                    return td.textContent.trim();
                });
            }).filter(function(row) {
                return row.length > 0 && row[0] !== '';
            });
            
            return JSON.stringify({headers: headers, rows: rows, rowCount: rows.length});
        """)
        
        import json
        data = json.loads(result)
        
        if "error" in data:
            print(f"  ❌ {data['error']}")
            return pd.DataFrame()
        
        print(f"  Found {data['rowCount']} player rows")
        print(f"  Headers: {data['headers'][:10]}...")
        
        df = pd.DataFrame(data["rows"], columns=data["headers"])
        df["season"] = season
        return df
        
    except Exception as e:
        print(f"  ❌ JavaScript extraction failed: {e}")
        return pd.DataFrame()


def main():
    print("Starting undetected Chrome browser...")
    
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    # Don't run headless — Cloudflare detects headless mode
    # options.add_argument("--headless")
    
    driver = uc.Chrome(options=options)
    
    all_frames = []
    
    try:
        for season, url in URLS.items():
            df = scrape_season(driver, url, season)
            if not df.empty:
                all_frames.append(df)
            time.sleep(3)  # Be polite between requests
        
        if all_frames:
            combined = pd.concat(all_frames, ignore_index=True)
            out_path = os.path.join(PROC_DIR, "player_stats_fbref.csv")
            combined.to_csv(out_path, index=False)
            print(f"\n✅ Saved {len(combined)} total rows to {out_path}")
        else:
            print("\n❌ No data scraped from any season.")
            
    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
