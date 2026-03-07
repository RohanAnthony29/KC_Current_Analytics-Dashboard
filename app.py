# app.py — KC Current Analytics Dashboard entry point

import streamlit as st
import base64, os

st.set_page_config(
    page_title = "KC Current Dashboard",
    page_icon  = "assets/kc_logo.png",
    layout     = "wide",
)

# ── Load logo as base64 ────────────────────────────────────────────────────────
logo_path = os.path.join(os.path.dirname(__file__), "assets", "kc_logo.png")
with open(logo_path, "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()
logo_data_uri = f"data:image/png;base64,{logo_b64}"

# ── Global KC Current Theme CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

    /* Hide Streamlit native chrome */
    header[data-testid="stHeader"]       { display: none !important; }
    section[data-testid="stSidebar"]     { display: none !important; }
    div[data-testid="stNavigation"]      { display: none !important; }
    div[data-testid="stSidebarNav"]      { display: none !important; }
    div[data-testid="stSidebarNavItems"] { display: none !important; }
    .stAppHeader, .st-emotion-cache-18ni7ap, .st-emotion-cache-yfhhig { display: none !important; }

    /* Global font + background */
    .stApp {
        background: #FFFFFF;
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* Content area */
    .block-container {
        padding-top: 84px !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 1300px;
    }
    .stApp > header + div { padding-top: 0 !important; }

    /* Page title — bold italic uppercase like KC site */
    h1 {
        font-family: 'Oswald', 'Arial Black', sans-serif !important;
        font-weight: 700 !important;
        font-style: italic !important;
        text-transform: uppercase !important;
        color: #1A1A2E !important;
        font-size: 2.8rem !important;
        letter-spacing: 1px !important;
        margin-bottom: 0.1rem !important;
        border-bottom: 4px solid #007A8A;
        padding-bottom: 8px;
    }

    /* Section headings */
    h2, h3 {
        font-family: 'Oswald', 'Arial Black', sans-serif !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        color: #1A1A2E !important;
        letter-spacing: 0.5px !important;
    }

    /* Dividers */
    hr { border-color: #E8E8E8 !important; margin: 1.5rem 0 !important; }

    /* Selectbox labels */
    .stSelectbox label {
        font-family: 'Oswald', sans-serif !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.78rem !important;
        letter-spacing: 1.2px !important;
        color: #1A1A2E !important;
    }

    /* st.metric cards */
    [data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E8E8E8;
        border-top: 4px solid #007A8A;
        border-radius: 4px;
        padding: 14px 18px !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Oswald', sans-serif !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #007A8A !important;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: #666 !important;
    }

    /* Custom KPI cards (HTML) — dark navy like KC site tiles */
    .kpi-card {
        background: #0D2B3E;
        color: white;
        padding: 22px 20px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: #007A8A;
    }
    .kpi-value {
        font-family: 'Oswald', sans-serif !important;
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
        margin: 0 !important;
        line-height: 1.1 !important;
    }
    .kpi-label {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.72rem !important;
        color: rgba(255,255,255,0.6) !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin: 0 0 6px 0 !important;
    }
    .kpi-change.positive { color: #4DD0C4 !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    .kpi-change.negative { color: #FF6B6B !important; font-weight: 700 !important; font-size: 1.1rem !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-family: 'Oswald', sans-serif !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        font-size: 0.85rem !important;
    }
    .stTabs [aria-selected="true"] {
        color: #007A8A !important;
        border-bottom-color: #007A8A !important;
    }

    /* Dataframe */
    .stDataFrame { border: 1px solid #E8E8E8 !important; border-radius: 4px !important; }

    /* ── Fixed custom header bar ── */
    .custom-header {
        position: fixed;
        top: 0; left: 0; right: 0;
        z-index: 999999;
        background: #FFFFFF;
        border-bottom: 3px solid #007A8A;
        padding: 0 2.5rem;
        display: flex;
        align-items: center;
        height: 64px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    }
    .header-logo {
        width: 44px; height: 44px;
        border-radius: 4px;
        margin-right: 14px;
        object-fit: contain;
    }
    .header-brand {
        display: flex;
        flex-direction: column;
        margin-right: 3rem;
    }
    .header-team-name {
        font-family: 'Oswald', 'Arial Black', sans-serif;
        font-size: 1.05rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #1A1A2E;
        line-height: 1.2;
    }
    .header-subtitle {
        font-size: 0.65rem;
        color: #007A8A;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        line-height: 1.2;
    }
    .header-nav { display: flex; gap: 0; align-items: stretch; height: 64px; }
    .header-nav a {
        color: #333;
        text-decoration: none;
        font-family: 'Oswald', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        padding: 0 20px;
        display: flex;
        align-items: center;
        border-bottom: 3px solid transparent;
        transition: all 0.15s;
    }
    .header-nav a:hover {
        color: #007A8A;
        border-bottom-color: #007A8A;
        background: #F7FAFA;
    }
</style>
""", unsafe_allow_html=True)

# ── Custom header HTML ─────────────────────────────────────────────────────────
st.markdown(f"""
<div class="custom-header">
    <img src="{logo_data_uri}" class="header-logo" alt="KC Current">
    <div class="header-brand">
        <span class="header-team-name">Kansas City Current</span>
        <span class="header-subtitle">KC Baby!</span>
    </div>
    <div class="header-nav">
        <a href="/" target="_self">Home</a>
        <a href="/players" target="_self">Player Stats</a>
        <a href="/trends" target="_self">Trends</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Page routing ───────────────────────────────────────────────────────────────
pages = [
    st.Page("pages/1_Team_Overview.py",      title="Team Overview",      default=True),
    st.Page("pages/2_Player_Performance.py", title="Player Performance", url_path="players"),
    st.Page("pages/3_Season_Trends.py",      title="Season Trends",      url_path="trends"),
]

nav = st.navigation(pages, position="top")
nav.run()