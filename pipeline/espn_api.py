# pipeline/espn_api.py
# ESPN API — historical NWSL data
#
# IMPORTANT: ESPN NWSL uses SPLIT-SEASON slugs:
#   2024 season  →  ?season=2024  (maps to 2023-24 calendar year)
#   2023 season  →  ?season=2023
#   2022 season  →  ?season=2022
#
# League slug: usa.nwsl
# Base URL:    https://site.api.espn.com/apis/site/v2/sports/soccer/usa.nwsl

import json, time, logging, requests, pandas as pd
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE    = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.nwsl"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; kc-dashboard/1.0)"}
SEASONS = [2022, 2023, 2024]


def fetch(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=12)
            r.raise_for_status()
            log.info(f"  GET {r.url}  →  {r.status_code}")
            return r.json()
        except requests.RequestException as e:
            log.warning(f"  Attempt {attempt+1}/{retries} failed: {e}")
            if attempt == retries - 1:
                return {}
            time.sleep(2 ** attempt)
    return {}


def fetch_teams():
    """List all NWSL teams — run once to confirm KC team ID."""
    data  = fetch(f"{BASE}/teams")
    teams = (data.get("sports", [{}])[0]
                 .get("leagues", [{}])[0]
                 .get("teams", []))
    rows = []
    for t in teams:
        team = t.get("team", {})
        kc   = " ← KC CURRENT" if "Kansas City" in str(team.get("displayName","")) else ""
        log.info(f"  id={str(team.get('id','?')):>5}  {team.get('displayName')}{kc}")
        rows.append({"team_id": team.get("id"), "team_name": team.get("displayName"),
                     "abbrev": team.get("abbreviation")})
    return pd.DataFrame(rows)


def fetch_standings(season: int) -> pd.DataFrame:
    log.info(f"Fetching standings  season={season}...")
    data = fetch(f"{BASE}/standings", params={"season": season})

    # Save raw for debugging
    try:
        from utils.constants import RAW_DIR
        (RAW_DIR / f"standings_{season}_raw.json").write_text(
            json.dumps(data, indent=2))
    except Exception:
        pass

    rows = []
    try:
        children = data.get("children", [])
        entries  = children[0].get("standings", {}).get("entries", []) if children else []
        if not entries:
            entries = data.get("standings", {}).get("entries", [])

        for entry in entries:
            team  = entry.get("team", {})
            stats = {s["name"]: s["value"] for s in entry.get("stats", [])}
            rows.append({
                "season"        : season,
                "team_id"       : team.get("id"),
                "team_name"     : team.get("displayName"),
                "abbrev"        : team.get("abbreviation"),
                "wins"          : int(stats.get("wins",                  0)),
                "draws"         : int(stats.get("ties",                  0)),
                "losses"        : int(stats.get("losses",                0)),
                "points"        : int(stats.get("points",                0)),
                "goals_for"     : int(stats.get("pointsFor",             stats.get("goalsFor",      0))),
                "goals_against" : int(stats.get("pointsAgainst",         stats.get("goalsAgainst",  0))),
                "goal_diff"     : int(stats.get("pointDifferential",     stats.get("goalDifference",0))),
                "games_played"  : int(stats.get("gamesPlayed",           0)),
                "fetched_at"    : datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        log.error(f"  Standings parse error season={season}: {e}")

    if not rows:
        log.warning(f"  No standings entries for season={season}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["ppg"]   = (df["points"] / df["games_played"].replace(0, 1)).round(2)
    df["is_kc"] = df["team_name"].str.contains("Kansas City", na=False)
    df = df.sort_values("points", ascending=False).reset_index(drop=True)
    df["position"] = df.index + 1
    log.info(f"  → {len(df)} teams")
    return df


def fetch_schedule(team_id: str, season: int) -> pd.DataFrame:
    log.info(f"Fetching schedule  team_id={team_id}  season={season}...")
    data = fetch(f"{BASE}/teams/{team_id}/schedule", params={"season": season})

    try:
        from utils.constants import RAW_DIR
        (RAW_DIR / f"schedule_{season}_raw.json").write_text(
            json.dumps(data, indent=2))
    except Exception:
        pass

    rows = []
    KC   = "Kansas City Current"
    try:
        for event in data.get("events", []):
            comp        = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            by_ha       = {t["homeAway"]: t for t in competitors}
            home        = by_ha.get("home", {})
            away        = by_ha.get("away", {})
            status      = event.get("status", {}).get("type", {})
            completed   = status.get("completed", False)

            home_name = home.get("team", {}).get("displayName", "")
            away_name = away.get("team", {}).get("displayName", "")
            is_home   = (home_name == KC)
            opponent  = away_name if is_home else home_name

            try:
                hs = int(home.get("score") or 0)
                as_ = int(away.get("score") or 0)
            except (ValueError, TypeError):
                hs = as_ = None

            kc_g  = (hs  if is_home else as_) if completed and hs is not None else None
            opp_g = (as_ if is_home else hs)  if completed and hs is not None else None

            if completed and kc_g is not None:
                result = "W" if kc_g > opp_g else "D" if kc_g == opp_g else "L"
            else:
                result = "TBD"

            rows.append({
                "match_id"   : event.get("id"),
                "date"       : event.get("date"),
                "season"     : season,
                "home_team"  : home_name,
                "away_team"  : away_name,
                "home_away"  : "Home" if is_home else "Away",
                "opponent"   : opponent,
                "kc_goals"   : kc_g,
                "opp_goals"  : opp_g,
                "result"     : result,
                "completed"  : completed,
                "venue"      : comp.get("venue", {}).get("fullName", ""),
                "attendance" : comp.get("attendance"),
            })
    except Exception as e:
        log.error(f"  Schedule parse error season={season}: {e}")

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        df = df[df["completed"] == True].sort_values("date").reset_index(drop=True)
    log.info(f"  → {len(df)} completed matches")
    return df
