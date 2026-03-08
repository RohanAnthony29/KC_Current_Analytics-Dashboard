import streamlit as st
import base64, os
import pandas as pd
from utils.cache import load_standings, load_schedule, get_available_seasons
from utils.charts import standings_bar, goals_bar, results_timeline
from utils.constants import COLORS

# ── Background image ───────────────────────────────────────────────────────────
bg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "team_bg.jpeg")
with open(bg_path, "rb") as f:
    bg_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.82), rgba(255,255,255,0.88)),
                          url("data:image/jpeg;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
</style>
""", unsafe_allow_html=True)

st.title("Team Overview")
st.caption("Season KPIs, form guide, and league position.")

with st.spinner("Loading..."):
    standings = load_standings()
    schedule_all = load_schedule()

if standings.empty and schedule_all.empty:
    st.warning("No data found. Run: `python run_pipeline.py`")
    st.stop()

# ── Season selector ────────────────────────────────────────────────────────────
seasons = get_available_seasons(schedule_all)
fcol1, _, _, _ = st.columns([1, 1, 2, 2])
with fcol1:
    sel_season = st.selectbox("Season", ["All"] + seasons, index=1 if seasons else 0)
schedule = load_schedule(sel_season) if sel_season != "All" else schedule_all


# ── KPI scorecards (computed from season-filtered schedule) ───────────────────
st.subheader("Season at a Glance")
completed = schedule[schedule["result"].isin(["W","D","L"])] if not schedule.empty and "result" in schedule.columns else pd.DataFrame()

if not completed.empty:
    wins   = (completed["result"] == "W").sum()
    draws  = (completed["result"] == "D").sum()
    losses = (completed["result"] == "L").sum()
    gf     = completed["kc_goals"].sum()  if "kc_goals"  in completed.columns else 0
    ga     = completed["opp_goals"].sum() if "opp_goals" in completed.columns else 0
    pts    = wins * 3 + draws

    # Only use standings for league position (current season only)
    position = "—"
    if not standings.empty and "is_kc" in standings.columns and (sel_season == "All" or str(sel_season) == str(seasons[0] if seasons else "")):
        kc_row = standings[standings["is_kc"] == True]
        if not kc_row.empty:
            position = f"#{int(kc_row.iloc[0].get('position', '?'))}"

    c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
    c1.metric("Position",      position)
    c2.metric("Points",        int(pts))
    c3.metric("Wins",          int(wins))
    c4.metric("Draws",         int(draws))
    c5.metric("Losses",        int(losses))
    c6.metric("Goals For",     int(gf))
    c7.metric("Goals Against", int(ga))
else:
    st.info("No match data for this season — run `python run_pipeline.py`")


st.divider()

# ── Last 5 results ─────────────────────────────────────────────────────────────
label = f"— {sel_season}" if sel_season != "All" else ""
st.subheader(f"Last 5 Results {label}")
if not schedule.empty and "result" in schedule.columns:
    last5 = schedule[schedule["result"].isin(["W","D","L"])].tail(5)
    if not last5.empty:
        color_map = {"W": COLORS["win"], "D": COLORS["draw"], "L": COLORS["loss"]}
        label_map = {"W": "WIN", "D": "DRAW", "L": "LOSS"}
        cols = st.columns(len(last5))
        for col, (_, r) in zip(cols, last5.iterrows()):
            result = r.get("result", "?")
            score  = f"{int(r.get('kc_goals',0))}–{int(r.get('opp_goals',0))}"
            col.markdown(f"""
<div style='background:{color_map.get(result,"#ccc")};border-radius:4px;
padding:18px 12px;text-align:center;color:white;border-top:4px solid rgba(255,255,255,0.3);'>
<p style='font-family:Oswald,sans-serif;font-size:1.4rem;font-weight:700;
letter-spacing:1px;margin:0;text-transform:uppercase;'>{label_map.get(result,"?")}</p>
<p style='font-family:Oswald,sans-serif;font-size:1.2rem;font-weight:600;margin:4px 0;'>{score}</p>
<p style='font-size:0.78rem;margin:0;opacity:0.9;font-weight:600;'>{r.get("opponent","")}</p>
<p style='font-size:0.7rem;margin:0;opacity:0.7;'>{r.get("home_away","")}</p>
</div>""", unsafe_allow_html=True)
    else:
        st.info("No completed matches found.")
else:
    st.info("Schedule data not available.")

st.divider()

# ── Charts ─────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("NWSL Standings")
    if not standings.empty:
        st.plotly_chart(standings_bar(standings), use_container_width=True)
with col_right:
    st.subheader("Goals For vs Against")
    if not standings.empty and "goals_for" in standings.columns:
        st.plotly_chart(goals_bar(standings.head(8)), use_container_width=True)

st.subheader("Match Goal Difference Over Season")
if not schedule.empty and "result" in schedule.columns:
    completed = schedule[schedule["result"].isin(["W","D","L"])]
    if not completed.empty:
        st.plotly_chart(results_timeline(completed), use_container_width=True)
