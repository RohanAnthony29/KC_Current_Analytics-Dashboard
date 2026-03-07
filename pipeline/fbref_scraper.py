# pipeline/fbref_scraper.py
# Scrapes KC Current player stats from FBref for 2022, 2023, 2024
#
# Squad ID : 6f666306  (KC Current — confirmed from fbref.com)
# NWSL comp: c182
# URLs:
#   https://fbref.com/en/squads/6f666306/2024/c182/Kansas-City-Current-Stats-NWSL
#   https://fbref.com/en/squads/6f666306/2023/c182/Kansas-City-Current-Stats-NWSL
#   https://fbref.com/en/squads/6f666306/2022/c182/Kansas-City-Current-Stats-NWSL
#
# FBref often blocks rapid requests — we add delays + rotate headers.
# Tables returned by pd.read_html (index):
#   0 = Standard stats  (goals, assists, xG, minutes, position)
#   1 = Shooting        (shots, SoT, xG per shot)
#   2 = Passing         (pass %, progressive passes)
#   3 = Defensive       (tackles, interceptions, blocks)

import time, logging, requests, pandas as pd
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SQUAD_ID = "6f666306"
SEASONS  = [2022, 2023, 2024]

# FBref is strict about User-Agent — mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://fbref.com/",
}

def fbref_url(season: int) -> str:
    """NWSL-specific stats URL — more reliable than the all-comps URL."""
    return (f"https://fbref.com/en/squads/{SQUAD_ID}"
            f"/{season}/c182/Kansas-City-Current-Stats-NWSL")


def fetch_html(url: str, retries=3) -> str | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            log.info(f"  GET {url}  →  {r.status_code}")
            return r.text
        except requests.RequestException as e:
            log.warning(f"  Attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                wait = 5 * (attempt + 1)   # 5s, 10s back-off
                log.info(f"  Waiting {wait}s before retry...")
                time.sleep(wait)
    return None


def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten FBref's multi-level column headers into single strings."""
    if isinstance(df.columns, pd.MultiIndex):
        cols = []
        for top, bot in df.columns:
            top = str(top).strip()
            bot = str(bot).strip()
            # FBref puts the real name in the bottom level when top is 'Unnamed'
            if "Unnamed" in top:
                cols.append(bot.lower().replace(" ", "_"))
            elif "Unnamed" in bot or bot == "":
                cols.append(top.lower().replace(" ", "_"))
            else:
                cols.append(f"{top}_{bot}".lower().replace(" ", "_"))
        df.columns = cols
    else:
        df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
    return df


def _clean_standard(df: pd.DataFrame, season: int) -> pd.DataFrame:
    """Clean the standard stats table (table index 0)."""
    df = _flatten_cols(df.copy())

    # Drop header-repeat rows and totals
    if "player" in df.columns:
        df = df[df["player"].notna()]
        df = df[~df["player"].isin(["Player", "Squad Total", "Opponent Total"])]
        df = df[~df["player"].str.startswith("Unnamed", na=True)]

    # Rename common FBref column variants to our standard names
    rename = {
        "pos":         "position",
        "age":         "age",
        "mp":          "matches_played",
        "starts":      "starts",
        "min":         "minutes",
        "90s":         "nineties",
        "gls":         "goals",
        "ast":         "assists",
        "g+a":         "goals_assists",
        "g-pk":        "non_pen_goals",
        "pk":          "pen_scored",
        "pkatt":       "pen_att",
        "crdy":        "yellow_cards",
        "crdr":        "red_cards",
        "xg":          "xg",
        "npxg":        "npxg",
        "xag":         "xag",
        "npxg+xag":    "npxg_xag",
        "prgc":        "progressive_carries",
        "prgp":        "progressive_passes",
        "prgr":        "progressive_receptions",
        # Sometimes columns appear with suffixes after flattening
        "performance_gls":   "goals",
        "performance_ast":   "assists",
        "performance_g+a":   "goals_assists",
        "performance_xg":    "xg",
        "performance_xag":   "xag",
        "performance_npxg":  "npxg",
        "expected_xg":       "xg",
        "expected_xag":      "xag",
        "expected_npxg":     "npxg",
        "expected_npxg+xag": "npxg_xag",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Coerce numerics
    num_cols = ["goals", "assists", "xg", "npxg", "xag", "minutes",
                "matches_played", "starts", "nineties", "yellow_cards", "red_cards",
                "non_pen_goals", "pen_scored", "pen_att",
                "progressive_carries", "progressive_passes"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill numeric nulls
    num_present = df.select_dtypes(include="number").columns
    df[num_present] = df[num_present].fillna(0)

    # Derived metrics
    if "goals" in df.columns and "xg" in df.columns:
        df["goals_above_xg"] = (df["goals"] - df["xg"]).round(2)
    if "minutes" in df.columns:
        nineties = (df["minutes"] / 90).replace(0, 1)
        for col, out in [("goals","goals_p90"),("assists","assists_p90"),("xg","xg_p90")]:
            if col in df.columns:
                df[out] = (df[col] / nineties).round(2)

    # Position full names
    pos_map = {"FW":"Forward","MF":"Midfielder","DF":"Defender","GK":"Goalkeeper"}
    if "position" in df.columns:
        df["position_full"] = df["position"].apply(
            lambda p: next((v for k,v in pos_map.items() if k in str(p)), str(p)))

    df["season"]     = str(season)
    df["fetched_at"] = datetime.now(timezone.utc).isoformat()
    return df.reset_index(drop=True)


def fetch_player_stats(season: int) -> pd.DataFrame:
    """Scrape + clean player stats for one season."""
    url  = fbref_url(season)
    html = fetch_html(url)

    if html is None:
        log.error(f"  Could not fetch FBref page for season {season}")
        return pd.DataFrame()

    # Save raw HTML
    try:
        from utils.constants import RAW_DIR
        (RAW_DIR / f"fbref_{season}.html").write_text(html, encoding="utf-8")
    except Exception:
        pass

    try:
        tables = pd.read_html(html, flavor="lxml")
        log.info(f"  FBref {season}: found {len(tables)} tables")
    except Exception as e:
        log.error(f"  pd.read_html failed for season {season}: {e}")
        return pd.DataFrame()

    if not tables:
        log.warning(f"  No tables found for season {season}")
        return pd.DataFrame()

    df = _clean_standard(tables[0], season)
    if "player" not in df.columns or df.empty:
        log.warning(f"  Standard table missing 'player' column for season {season}")
        return pd.DataFrame()

    log.info(f"  Season {season}: {len(df)} players scraped")
    return df


def fetch_all_seasons(seasons=None, delay=4) -> pd.DataFrame:
    """
    Fetch player stats for all seasons and combine into one DataFrame.
    delay: seconds to wait between requests (FBref rate-limits)
    """
    seasons = seasons or SEASONS
    frames  = []
    for i, season in enumerate(seasons):
        if i > 0:
            log.info(f"  Waiting {delay}s before next request...")
            time.sleep(delay)
        df = fetch_player_stats(season)
        if not df.empty:
            frames.append(df)
        else:
            log.warning(f"  No data returned for season {season}")

    if not frames:
        log.error("  No player stats fetched for any season")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["player","season"], keep="first")
    log.info(f"  Total player-seasons: {len(combined)}")
    return combined


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.constants import PROC_DIR

    df = fetch_all_seasons()
    if not df.empty:
        out = PROC_DIR / "player_stats.csv"
        df.to_csv(out, index=False)
        log.info(f"✅ Saved {out}  ({len(df)} rows)")
        print(df[["player","season","goals","assists","xg","minutes"]].to_string())
    else:
        log.error("No data to save")
