# utils/constants.py
# Single source of truth for all URLs, IDs, and brand colours

# ── ESPN ────────────────────────────────────────────────────────────────────
ESPN_BASE      = "https://site.api.espn.com/apis/site/v2/sports/soccer/nwsl"
KC_TEAM_ID     = "21"
ESPN_HEADERS   = {"User-Agent": "Mozilla/5.0"}

ESPN_ENDPOINTS = {
    "scoreboard" : f"{ESPN_BASE}/scoreboard",
    "standings"  : f"{ESPN_BASE}/standings",
    "team"       : f"{ESPN_BASE}/teams/{KC_TEAM_ID}",
    "schedule"   : f"{ESPN_BASE}/teams/{KC_TEAM_ID}/schedule",
    "statistics" : f"{ESPN_BASE}/teams/{KC_TEAM_ID}/statistics",
}

# ── FBref ────────────────────────────────────────────────────────────────────
FBREF_BASE      = "https://fbref.com/en/squads/6f666306"
FBREF_SEASONS   = ["2024", "2023", "2022", "2021"]
FBREF_HEADERS   = {"User-Agent": "Mozilla/5.0 (compatible; kc-dashboard/1.0)"}

def fbref_url(season: str) -> str:
    return f"{FBREF_BASE}/{season}/Kansas-City-Current-Stats"

# ── Wikipedia ────────────────────────────────────────────────────────────────
WIKI_URL = "https://en.wikipedia.org/wiki/Kansas_City_Current"

# ── Brand colours ────────────────────────────────────────────────────────────
COLORS = {
    "teal"      : "#007A8A",
    "navy"      : "#1A1A2E",
    "gold"      : "#C8A200",
    "light"     : "#F0F8FA",
    "white"     : "#FFFFFF",
    "win"       : "#007A8A",
    "draw"      : "#C8A200",
    "loss"      : "#C62828",
}

# ── Data paths ───────────────────────────────────────────────────────────────
from pathlib import Path
ROOT      = Path(__file__).resolve().parent.parent
RAW_DIR   = ROOT / "data" / "raw"
PROC_DIR  = ROOT / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)