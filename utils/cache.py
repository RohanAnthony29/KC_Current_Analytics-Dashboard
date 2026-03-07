# utils/cache.py
import streamlit as st
import pandas as pd
from utils.constants import PROC_DIR


def _load(name: str) -> pd.DataFrame:
    path = PROC_DIR / f"{name}.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_standings() -> pd.DataFrame:
    """Latest season standings (used for league table views)."""
    return _load("standings")


@st.cache_data(ttl=3600, show_spinner=False)
def load_standings_all() -> pd.DataFrame:
    """All seasons standings — for multi-season comparisons."""
    df = _load("standings_all_seasons")
    if df.empty:
        df = _load("standings")   # fallback
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_schedule(season: str = "all") -> pd.DataFrame:
    df = _load("schedule")
    if not df.empty:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        if season != "all" and "season" in df.columns:
            df = df[df["season"].astype(str) == str(season)]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_player_stats(season: str = "all") -> pd.DataFrame:
    df = _load("player_stats")
    if not df.empty and season != "all" and "season" in df.columns:
        df = df[df["season"].astype(str) == str(season)]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def load_season_history() -> pd.DataFrame:
    return _load("season_history")


def get_available_seasons(df: pd.DataFrame) -> list:
    """Return sorted unique seasons from a DataFrame."""
    if df.empty or "season" not in df.columns:
        return []
    return sorted(df["season"].astype(str).unique().tolist(), reverse=True)


def clear_all_caches():
    load_standings.clear()
    load_standings_all.clear()
    load_schedule.clear()
    load_player_stats.clear()
    load_season_history.clear()
