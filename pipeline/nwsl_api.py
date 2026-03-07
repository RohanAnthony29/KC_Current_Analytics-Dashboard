# pipeline/nwsl_api.py
# Fetches KC Current player stats from the official NWSL website's hidden REST API.
#
# How this was discovered:
#   Open nwslsoccer.com/stats/players/all in Chrome DevTools → Network tab → XHR
#   The site calls:  https://api.nwslsoccer.com/v2/players/stats?...
#
# No API key required. Same data that powers the official stats pages.
#
# KC Current opta team ID: 2c1699409ff84c9eb491aeaca3d3edde
# Season opta IDs:
#   2024 → "2024" (confirmed from network requests)
#   2023 → "2023"
#   2022 → "2022"

import time, logging, requests, pandas as pd
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://api.nwslsoccer.com/v2"

HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept"          : "application/json",
    "Referer"         : "https://www.nwslsoccer.com/",
    "Origin"          : "https://www.nwslsoccer.com",
}

KC_TEAM_ID = "2c1699409ff84c9eb491aeaca3d3edde"
SEASONS    = ["2022", "2023", "2024"]

# Stat category slugs available from the NWSL API
STAT_CATEGORIES = {
    "general"   : "general",     # goals, assists, minutes, matches
    "shooting"  : "shooting",    # shots, shots on target
    "passing"   : "passing",     # passes, key passes
    "defending" : "defending",   # tackles, interceptions
    "goalkeeping": "goalkeeping" # saves, clean sheets
}


def fetch(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            # Added verify=False to bypass NWSL's expired SSL cert
            r = requests.get(url, headers=HEADERS, params=params, timeout=15, verify=False)
            r.raise_for_status()
            log.info(f"  GET {r.url}  →  {r.status_code}")
            return r.json()
        except requests.RequestException as e:
            log.warning(f"  Attempt {attempt+1}/{retries} failed: {e}")
            if attempt == retries - 1:
                return None
            time.sleep(3 * (attempt + 1))
    return None


def fetch_player_stats_season(season: str) -> pd.DataFrame:
    """
    Fetch all KC Current player stats for a season from the official NWSL API.
    Tries multiple known endpoint patterns and merges results.
    """
    log.info(f"Fetching NWSL API player stats — season {season}...")

    # Pattern 1: /players/stats filtered by team + season
    data = fetch(f"{BASE_URL}/players/stats", params={
        "season_opta_id" : season,
        "team_opta_id"   : KC_TEAM_ID,
        "limit"          : 100,
    })

    if data and _has_player_data(data):
        return _parse_player_stats(data, season)

    # Pattern 2: /stats/players with different param names
    data = fetch(f"{BASE_URL}/stats/players", params={
        "season"  : season,
        "team"    : KC_TEAM_ID,
        "limit"   : 100,
    })

    if data and _has_player_data(data):
        return _parse_player_stats(data, season)

    # Pattern 3: team-specific endpoint
    data = fetch(f"{BASE_URL}/teams/{KC_TEAM_ID}/players/stats", params={
        "season_opta_id": season,
    })

    if data and _has_player_data(data):
        return _parse_player_stats(data, season)

    log.warning(f"  NWSL API returned no player data for season {season}")
    return pd.DataFrame()


def _has_player_data(data) -> bool:
    if not data:
        return False
    if isinstance(data, list) and len(data) > 0:
        return True
    if isinstance(data, dict):
        for key in ("players", "data", "stats", "results", "items"):
            if key in data and data[key]:
                return True
    return False


def _parse_player_stats(data, season: str) -> pd.DataFrame:
    """Parse whatever shape the NWSL API returns into our standard DataFrame."""
    rows = []

    # Unwrap list-of-dicts or dict-with-list
    players = data
    if isinstance(data, dict):
        for key in ("players", "data", "stats", "results", "items"):
            if key in data:
                players = data[key]
                break

    if not isinstance(players, list):
        log.warning(f"  Unexpected data shape: {type(data)}")
        return pd.DataFrame()

    for p in players:
        stats = p.get("stats", p)   # sometimes stats are at top level
        player_info = p.get("player", p)

        name = (player_info.get("name") or
                player_info.get("full_name") or
                f"{player_info.get('first_name','')} {player_info.get('last_name','')}".strip() or
                p.get("name", "Unknown"))

        position = (player_info.get("primary_position") or
                    player_info.get("position") or
                    p.get("position", ""))

        rows.append({
            "player"   : name,
            "position" : _normalize_position(position),
            "season"   : season,
            "matches"  : _safe_int(stats, ["appearances","matches_played","games_played","mp"]),
            "minutes"  : _safe_int(stats, ["minutes_played","mins_played","minutes","min"]),
            "goals"    : _safe_int(stats, ["goals","goal"]),
            "assists"  : _safe_int(stats, ["goal_assists","assists","assist"]),
            "shots"    : _safe_int(stats, ["total_scoring_att","shots","shots_total"]),
            "shots_on_target": _safe_int(stats, ["ontarget_scoring_att","shots_on_target","sot"]),
            "yellow_cards"   : _safe_int(stats, ["yellow_card","yellow_cards"]),
            "red_cards"      : _safe_int(stats, ["red_card","red_cards"]),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Clean & derive metrics
    df = df[df["player"] != "Unknown"].copy()
    df = df[df["minutes"] > 0].copy()

    nineties = (df["minutes"] / 90).replace(0, 1)
    df["goals_p90"]   = (df["goals"]   / nineties).round(2)
    df["assists_p90"] = (df["assists"] / nineties).round(2)
    df["position_full"] = df["position"].apply(_position_full)
    df["fetched_at"]    = datetime.now(timezone.utc).isoformat()

    log.info(f"  Season {season}: {len(df)} players parsed")
    return df


def _safe_int(d: dict, keys: list) -> int:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return int(float(v))
            except (ValueError, TypeError):
                pass
    return 0


def _normalize_position(pos: str) -> str:
    pos = str(pos).upper()
    if any(x in pos for x in ["FORWARD","FWD","FW","STRIKER","ST","CF","LW","RW"]):
        return "FW"
    if any(x in pos for x in ["MIDFIELDER","MID","MF","CM","AM","DM"]):
        return "MF"
    if any(x in pos for x in ["DEFENDER","DEF","DF","CB","LB","RB","WB"]):
        return "DF"
    if any(x in pos for x in ["GOALKEEPER","GK","KEEPER"]):
        return "GK"
    return pos[:2] if pos else ""


def _position_full(pos: str) -> str:
    return {"FW":"Forward","MF":"Midfielder","DF":"Defender","GK":"Goalkeeper"}.get(pos, pos)


def fetch_all_seasons(seasons=None) -> pd.DataFrame:
    seasons = seasons or SEASONS
    frames  = []
    for i, season in enumerate(seasons):
        if i > 0:
            time.sleep(2)
        df = fetch_player_stats_season(season)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["player","season"], keep="first")
    log.info(f"Total: {len(combined)} player-season rows across {len(frames)} seasons")
    return combined


# ── Probe the API to find the right endpoint ─────────────────────────────────
def probe_api():
    """
    Run this to discover which endpoints the NWSL API actually exposes.
    Prints every URL tried and the response shape.
    Call from command line: python pipeline/nwsl_api.py --probe
    """
    log.info("Probing NWSL API endpoints...")

    endpoints_to_try = [
        # Players/stats variants
        (f"{BASE_URL}/players/stats",
         {"season_opta_id":"2024","team_opta_id":KC_TEAM_ID,"limit":5}),
        (f"{BASE_URL}/stats/players",
         {"season":"2024","team":KC_TEAM_ID,"limit":5}),
        (f"{BASE_URL}/teams/{KC_TEAM_ID}/players/stats",
         {"season_opta_id":"2024"}),
        (f"{BASE_URL}/players",
         {"season_opta_id":"2024","team_opta_id":KC_TEAM_ID}),
        # Game stats — can aggregate per player across a season
        (f"{BASE_URL}/games",
         {"season_opta_id":"2024","team_opta_id":KC_TEAM_ID,"limit":5}),
        # Standings/seasons
        (f"{BASE_URL}/standings",
         {"season_opta_id":"2024"}),
        (f"{BASE_URL}/seasons", {}),
        (f"{BASE_URL}/competitions", {}),
    ]

    for url, params in endpoints_to_try:
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=10)
            status = r.status_code
            try:
                body = r.json()
                if isinstance(body, list):
                    shape = f"list[{len(body)}]"
                    if body:
                        shape += f"  keys={list(body[0].keys())[:6]}"
                elif isinstance(body, dict):
                    shape = f"dict  keys={list(body.keys())[:8]}"
                else:
                    shape = str(type(body))
            except Exception:
                shape = f"non-JSON  ({len(r.text)} chars)"

            flag = "✅" if status == 200 else "❌"
            log.info(f"  {flag} {status}  {r.url}")
            if status == 200:
                log.info(f"       Shape: {shape}")
        except Exception as e:
            log.warning(f"  ❌ ERROR  {url}  —  {e}")
        time.sleep(1)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, __import__("pathlib").Path(__file__).parent.parent.__str__())

    if "--probe" in sys.argv:
        probe_api()
    else:
        from utils.constants import PROC_DIR
        df = fetch_all_seasons()
        if not df.empty:
            out = PROC_DIR / "player_stats.csv"
            df.to_csv(out, index=False)
            log.info(f"✅ Saved {out}  ({len(df)} rows)")
            print(df[["player","season","goals","assists","minutes"]].to_string())
        else:
            log.warning("No data fetched — run with --probe to diagnose endpoints")
