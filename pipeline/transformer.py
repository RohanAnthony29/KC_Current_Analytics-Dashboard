# pipeline/transformer.py
import logging
import pandas as pd
from utils.constants import PROC_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def transform_standings(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["games_played"] = df["wins"] + df["draws"] + df["losses"]
    df["ppg"] = (df["points"] / df["games_played"].replace(0, 1)).round(2)
    df["is_kc"] = df["team_name"].str.contains("Kansas City", na=False)
    df = df.sort_values("points", ascending=False).reset_index(drop=True)
    df["position"] = df.index + 1
    return df


def transform_schedule(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    KC = "Kansas City Current"
    df["kc_goals"]  = df.apply(lambda r: r["home_score"] if r["home_team"] == KC else r["away_score"], axis=1)
    df["opp_goals"] = df.apply(lambda r: r["away_score"] if r["home_team"] == KC else r["home_score"], axis=1)
    df["opponent"]  = df.apply(lambda r: r["away_team"]  if r["home_team"] == KC else r["home_team"],  axis=1)
    df["home_away"] = df.apply(lambda r: "Home" if r["home_team"] == KC else "Away", axis=1)
    completed = df[df["completed"] == True].copy()
    return completed.sort_values("date").reset_index(drop=True)


def transform_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df = df.drop_duplicates(subset=["player", "season"], keep="first")
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].fillna(0)
    if "position" in df.columns:
        pos_map = {"FW": "Forward", "MF": "Midfielder", "DF": "Defender", "GK": "Goalkeeper"}
        df["position_full"] = df["position"].map(
            lambda p: next((v for k, v in pos_map.items() if k in str(p)), str(p)))
    if "minutes" in df.columns:
        nineties = (df["minutes"] / 90).replace(0, 1)
        if "goals"   in df.columns: df["goals_p90"]  = (df["goals"]   / nineties).round(2)
        if "assists" in df.columns: df["assists_p90"] = (df["assists"] / nineties).round(2)
        if "xg"      in df.columns: df["xg_p90"]      = (df["xg"]     / nineties).round(2)
    return df.reset_index(drop=True)


def transform_season_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    col0 = df.columns[0]
    df = df[df[col0].astype(str).str.match(r"20\d{2}")]
    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]
    rename = {"w":"wins","d":"draws","l":"losses","gf":"goals_for",
              "ga":"goals_against","pts":"points","pos":"position","finish":"position"}
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    for col in ["wins","draws","losses","goals_for","goals_against","points"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.reset_index(drop=True)


def save(df: pd.DataFrame, name: str):
    """Save DataFrame as CSV."""
    path = PROC_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    log.info(f"Saved {path}  ({len(df)} rows)")


if __name__ == "__main__":
    from pipeline.espn_api      import fetch_standings, fetch_schedule
    from pipeline.fbref_scraper import fetch_all_seasons

    log.info("Running transformer...")
    errors = []

    try:
        save(transform_standings(fetch_standings()), "standings")
    except Exception as e:
        log.error(f"Standings failed: {e}"); errors.append("standings")

    try:
        save(transform_schedule(fetch_schedule()), "schedule")
    except Exception as e:
        log.error(f"Schedule failed: {e}"); errors.append("schedule")

    try:
        save(transform_player_stats(fetch_all_seasons()), "player_stats")
    except Exception as e:
        log.error(f"Player stats failed: {e}"); errors.append("player_stats")

    if errors:
        log.warning(f"⚠️  Errors in: {errors}")
    log.info(f"✅ Done — {3 - len(errors)}/3 sources saved")
