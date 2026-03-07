# pipeline/validator.py
# Data quality checks — runs after transformer, feeds Pipeline Status page

import logging
import pandas as pd
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def validate_dataframe(df: pd.DataFrame, source: str,
                        expected_min_rows: int = 5,
                        required_columns: list = None) -> dict:
    """
    Run standard quality checks on any ingested DataFrame.
    Returns a validation report dict consumed by the Pipeline Status page.
    """
    report = {
        "source"        : source,
        "row_count"     : len(df),
        "col_count"     : len(df.columns),
        "null_pct"      : round(df.isnull().mean().mean() * 100, 2) if not df.empty else 100.0,
        "duplicates"    : int(df.duplicated().sum()) if not df.empty else 0,
        "status"        : "OK",
        "issues"        : [],
        "checked_at"    : datetime.now(timezone.utc).isoformat(),
    }

    # ── Checks ──────────────────────────────────────────────────────────────
    if df.empty:
        report["status"] = "ERROR"
        report["issues"].append("DataFrame is empty")
        return report

    if report["row_count"] < expected_min_rows:
        report["status"] = "WARN"
        report["issues"].append(f"Low row count: {report['row_count']} (expected ≥{expected_min_rows})")

    if report["null_pct"] > 30:
        report["status"] = "WARN"
        report["issues"].append(f"High null rate: {report['null_pct']}%")

    if report["duplicates"] > 0:
        report["status"] = "WARN"
        report["issues"].append(f"{report['duplicates']} duplicate rows detected")

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            report["status"] = "ERROR"
            report["issues"].append(f"Missing required columns: {missing}")

    if report["status"] == "OK":
        log.info(f"[{source}] ✅ Validation passed — {report['row_count']} rows")
    else:
        log.warning(f"[{source}] ⚠️  Validation {report['status']}: {report['issues']}")

    return report


def validate_all(dataframes: dict) -> list:
    """
    Validate multiple DataFrames at once.
    dataframes: { "source_name": (df, min_rows, required_cols), ... }
    Returns list of report dicts.
    """
    reports = []
    specs = {
        "standings"   : (10, ["team_name", "wins", "losses", "points"]),
        "schedule"    : (5,  ["date", "opponent", "result"]),
        "player_stats": (5,  ["player", "goals", "assists"]),
    }
    for name, df in dataframes.items():
        min_rows, req_cols = specs.get(name, (5, []))
        reports.append(validate_dataframe(df, name, min_rows, req_cols))
    return reports


def status_emoji(status: str) -> str:
    return {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(status, "❓")


if __name__ == "__main__":
    from utils.constants import PROC_DIR
    # using CSV storage

    for name in ["standings", "schedule", "player_stats"]:
        path = PROC_DIR / f"{name}.csv"
        if path.exists():
            df = pd.read_csv(path)
            report = validate_dataframe(df, name)
            print(f"\n{status_emoji(report['status'])} {name}")
            print(f"   Rows: {report['row_count']}  |  Nulls: {report['null_pct']}%  |  Dupes: {report['duplicates']}")
            if report["issues"]:
                for issue in report["issues"]:
                    print(f"   ⚠  {issue}")
        else:
            print(f"❌ {name}.csv not found — run transformer.py first")