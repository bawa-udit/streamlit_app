# Promotion Fatigue & Discount Addiction — Streamlit App

## Project Structure
```
streamlit_app/
├── app.py                  # Main entry point (navigation)
├── data_loader.py          # Cached data loading + feature engineering
├── requirements.txt        # All dependencies
├── pages/
│   ├── overview.py         # Page 1: KPI overview
│   ├── explorer.py         # Page 2: Addiction explorer (deep filters)
│   ├── fatigue.py          # Page 3: Fatigue curves
│   └── scorer.py           # Page 4: Live XGBoost customer scorer
└── data/
    ├── transactions.csv    # ← PUT YOUR DATA FILES HERE
    ├── campaigns.csv
    ├── products.csv
    └── customers.csv
```

## Setup (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Put your 4 CSV files in the data/ folder

# 3. Run
streamlit run app.py
```

## Deploy to Streamlit Community Cloud (Free)

1. Push this entire folder to a **public GitHub repo**
2. Go to https://share.streamlit.io
3. Click "New app"
4. Select your repo, branch = main, main file = app.py
5. Click Deploy — you get a shareable URL in ~2 minutes

**Important**: Your CSV data files must also be in the repo (in the `data/` folder).
If files are too large for GitHub (>100MB), use `st.cache_data` with a remote URL or
upload to Google Drive and load with `gdown`.

## Pages

| Page | What it does |
|------|-------------|
| 🏠 Overview | Revenue KPIs, margin erosion, affinity breakdown, blind spots |
| 🔍 Addiction Explorer | Filter by city, segment, product, age, channel — heatmaps, product rankings, drill-downs |
| 📉 Fatigue Curves | Conversion decay + discount escalation per campaign type, vicious cycle deep dive |
| 🎯 Customer Scorer | Look up any customer by ID or enter parameters manually — get live XGBoost addiction score + recommended action |
