import streamlit as st
import pandas as pd
from utils.cache import load_season_history
from utils.charts import season_trend_line, goals_bar

st.title("Season Trends")
st.caption("Analyzing KC Current's historical performance trajectory in the NWSL.")

df = load_season_history()

if df.empty:
    st.warning("No historical data found. Please run the data pipeline.")
    st.stop()

# Ensure chronological order
df = df.sort_values("season").reset_index(drop=True)

# ── KPI Cards: Year-Over-Year Change ──────────────────────────────────────────
if len(df) >= 2:
    current  = df.iloc[-1]
    previous = df.iloc[-2]

    col1, col2, col3 = st.columns(3)

    pts_diff  = current['points'] - previous['points']
    pts_class = "positive" if pts_diff >= 0 else "negative"
    pts_sign  = "+" if pts_diff >= 0 else ""

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-label">Points (vs Last Season)</p>
            <p class="kpi-value">{current['points']} <span class="kpi-change {pts_class}">({pts_sign}{pts_diff})</span></p>
        </div>""", unsafe_allow_html=True)

    pos_diff  = previous['position'] - current['position']
    pos_class = "positive" if pos_diff >= 0 else "negative"
    pos_sign  = "▲" if pos_diff >= 0 else "▼"

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-label">League Position (vs Last Season)</p>
            <p class="kpi-value">#{current['position']} <span class="kpi-change {pos_class}">({pos_sign}{abs(pos_diff)})</span></p>
        </div>""", unsafe_allow_html=True)

    gd_diff  = current['goal_diff'] - previous['goal_diff']
    gd_class = "positive" if gd_diff >= 0 else "negative"
    gd_sign  = "+" if gd_diff >= 0 else ""

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <p class="kpi-label">Goal Difference (vs Last Season)</p>
            <p class="kpi-value">{current['goal_diff']:+} <span class="kpi-change {gd_class}">({gd_sign}{gd_diff})</span></p>
        </div>""", unsafe_allow_html=True)

# ── Trend Charts ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("Historical Trajectory")

col_a, col_b = st.columns(2)

with col_a:
    st.plotly_chart(season_trend_line(df, "points",   "Points per Season"),         use_container_width=True)
    st.plotly_chart(season_trend_line(df, "position", "League Finish Position"),     use_container_width=True)

with col_b:
    st.plotly_chart(season_trend_line(df, "goal_diff","Goal Difference per Season"), use_container_width=True)
    st.plotly_chart(season_trend_line(df, "wins",     "Total Wins per Season"),      use_container_width=True)

st.divider()
st.subheader("Goals Scored vs Conceded")

df_for_bar = df.copy()
df_for_bar["team_name"] = df_for_bar["season"]
bar_fig = goals_bar(df_for_bar)
bar_fig.update_layout(title_text="Goals Over Time", title_font=dict(size=18))
bar_fig.update_xaxes(title_text="Season", tickangle=0)
st.plotly_chart(bar_fig, use_container_width=True)

st.divider()
with st.expander("View Historical Data Table"):
    st.dataframe(df, use_container_width=True, hide_index=True)