import streamlit as st

st.set_page_config(
    page_title="Discount Addiction & Promotion Fatigue",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1e2d45;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #00c9a7;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #0d1117;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 16px;
}
[data-testid="metric-container"] label {
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #5c7194 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 700 !important;
}

/* Page background */
.stApp { background: #080c14; }

/* Headers */
h1 { font-size: 28px !important; font-weight: 700 !important; }
h2 { font-size: 18px !important; font-weight: 600 !important; color: #c8d4f0 !important; }
h3 { font-size: 14px !important; font-weight: 600 !important; color: #8899bb !important; }

/* Dividers */
hr { border-color: #1e2d45 !important; }

/* Tabs */
[data-testid="stTabs"] button {
    font-size: 13px !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ───────────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/200x40/080c14/00c9a7?text=RetailCo+ML", width=200)
st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")

pages = {
    "🏠  Overview": "overview",
    "🔍  Addiction Explorer": "explorer",
    "📉  Fatigue Curves": "fatigue",
    "🎯  Customer Scorer": "scorer",
}

selection = st.sidebar.radio(
    "", list(pages.keys()), label_visibility="collapsed"
)
page = pages[selection]

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size:10px;color:#3a4f6a;font-family:JetBrains Mono,monospace;line-height:1.8'>
200,000 transactions<br>
5,000 customers<br>
200 campaigns<br>
500 products<br>
Jan 2021 – Dec 2024
</div>
""", unsafe_allow_html=True)

# ── Route to pages ────────────────────────────────────────────────
if page == "overview":
    from pages import overview; overview.show()
elif page == "explorer":
    from pages import explorer; explorer.show()
elif page == "fatigue":
    from pages import fatigue; fatigue.show()
elif page == "scorer":
    from pages import scorer; scorer.show()
