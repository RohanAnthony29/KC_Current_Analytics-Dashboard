import streamlit as st
import pandas as pd
import base64, os
from utils.cache import load_player_stats
from utils.charts import xg_scatter, top_scorers_bar, radar_chart
from utils.constants import COLORS

# ── Background image ───────────────────────────────────────────────────────────

bg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "team_stats_bg.png")
with open(bg_path, "rb") as f:
    bg_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.82), rgba(255,255,255,0.88)),
                          url("data:image/png;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    /* Solid white background on chart containers so BG doesn't bleed through */
    [data-testid="stPlotlyChart"],
    [data-testid="stPlotlyChart"] > div {{
        background: #FFFFFF !important;
        border-radius: 4px;
    }}
</style>
""", unsafe_allow_html=True)
st.title("Player Performance")
st.caption("Detailed analytics on player contributions, finishing, and playmaking.")

# Load Data
df = load_player_stats()

if df.empty:
    st.warning("No player data found. Please run the data pipeline.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
fcol1, fcol2, _, _ = st.columns([1, 1, 2, 2])
seasons = ["All", "2025", "2024"]
with fcol1:
    sel_season = st.selectbox("Season", seasons)
positions = ["All"] + sorted(df["position"].dropna().unique().tolist())
with fcol2:
    sel_position = st.selectbox("Position", positions)

# Apply filters
filtered_df = df.copy()
filtered_df["season"] = filtered_df["season"].astype(str)
if sel_season != "All":
    filtered_df = filtered_df[filtered_df["season"] == sel_season]
if sel_position != "All":
    filtered_df = filtered_df[filtered_df["position"] == sel_position]

st.markdown(f"**Showing {len(filtered_df)} players** matching filters.")
st.divider()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Total Goals</p>
        <p class="kpi-value">{int(filtered_df['goals'].sum())}</p>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Total xG</p>
        <p class="kpi-value">{filtered_df['xg'].sum():.1f}</p>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Goals vs xG</p>
        <p class="kpi-value">{(filtered_df['goals'].sum() - filtered_df['xg'].sum()):+.1f}</p>
    </div>""", unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Total Assists</p>
        <p class="kpi-value">{int(filtered_df['assists'].sum())}</p>
    </div>""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Finishing (xG vs Goals)", "Top Performers", "Player Comparison"])

with tab1:
    st.subheader("Clinical Finishing Analysis")
    st.markdown("Players above the diagonal line are outperforming their expected goals.")
    st.plotly_chart(xg_scatter(filtered_df), use_container_width=True)

with tab2:
    st.subheader("Top Contributors")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(top_scorers_bar(filtered_df, metric="goals", label="Goals", n=8), use_container_width=True)
    with colB:
        st.plotly_chart(top_scorers_bar(filtered_df, metric="assists", label="Assists", n=8), use_container_width=True)

with tab3:
    st.subheader("Head-to-Head Comparison")
    st.markdown("Select up to 3 players to compare their percentile performance across key metrics.")
    all_players = sorted(filtered_df["player"].unique())
    selected_players = st.multiselect("Select players to compare:", all_players, default=all_players[:2] if len(all_players) >= 2 else all_players)
    if len(selected_players) > 0:
        if len(selected_players) > 3:
            st.warning("Please select a maximum of 3 players for clarity.")
        st.plotly_chart(radar_chart(selected_players, filtered_df), use_container_width=True)
    else:
        st.info("Select at least one player to generate the radar chart.")

st.divider()
st.subheader("Raw Player Data")
st.dataframe(
    filtered_df.sort_values(by=["goals", "assists"], ascending=[False, False]),
    use_container_width=True,
    hide_index=True,
    column_config={
        "xg":                 st.column_config.NumberColumn("xG",          format="%.2f"),
        "npxg":               st.column_config.NumberColumn("npxG",        format="%.2f"),
        "goals_p90":          st.column_config.NumberColumn("Goals/90",    format="%.2f"),
        "assists_p90":        st.column_config.NumberColumn("Assists/90",  format="%.2f"),
        "xg_p90":             st.column_config.NumberColumn("xG/90",       format="%.2f"),
        "goals_above_xg":     st.column_config.NumberColumn("G - xG",      format="%+.2f"),
        "pass_completion_pct":st.column_config.NumberColumn("Pass %",      format="%d%%"),
    }
)