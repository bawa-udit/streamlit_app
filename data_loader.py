import pandas as pd
import numpy as np
import streamlit as st
from scipy.ndimage import uniform_filter1d
from scipy import stats as scipy_stats

# ── Raw data loader (cached) ──────────────────────────────────────
@st.cache_data
def load_raw():
    tx   = pd.read_csv("data/transactions.csv")
    camp = pd.read_csv("data/campaigns.csv")
    prod = pd.read_csv("data/products.csv")
    cust = pd.read_csv("data/customers.csv")
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
    tx["year"]  = tx["transaction_date"].dt.year
    tx["month"] = tx["transaction_date"].dt.to_period("M").astype(str)
    return tx, camp, prod, cust

# ── Master merged dataframe (cached) ─────────────────────────────
@st.cache_data
def load_master():
    tx, camp, prod, cust = load_raw()
    m = tx.merge(
        cust[["customer_id","age","gender","city_tier","segment",
              "price_sensitivity_score","loyalty_tier",
              "preferred_channel","discount_affinity_label"]],
        on="customer_id", how="left"
    )
    m = m.merge(
        prod[["product_id","product_name","category","sub_category","brand_tier"]],
        on="product_id", how="left"
    )
    m = m.merge(
        camp[["campaign_id","campaign_type","campaign_number_of_type","channel"]]
            .rename(columns={"channel":"campaign_channel"}),
        on="campaign_id", how="left"
    )
    return m

# ── Customer feature table (for scorer) ──────────────────────────
@st.cache_data
def load_customer_features():
    tx, camp, prod, cust = load_raw()

    cf = tx.groupby("customer_id").agg(
        total_transactions          = ("transaction_id",          "count"),
        total_revenue               = ("revenue",                 "sum"),
        avg_order_value             = ("revenue",                 "mean"),
        avg_margin                  = ("margin",                  "mean"),
        avg_discount_pct            = ("discount_pct",            "mean"),
        max_discount_pct            = ("discount_pct",            "max"),
        promo_transactions          = ("is_promotional",          "sum"),
        full_price_transactions     = ("purchased_at_full_price", "sum"),
        avg_days_between_purchases  = ("days_since_last_purchase","mean"),
        avg_campaign_exposure       = ("campaign_exposure_count", "mean"),
        max_campaign_exposure       = ("campaign_exposure_count", "max"),
        last_purchase_date          = ("transaction_date",        "max"),
        first_purchase_date         = ("transaction_date",        "min"),
    ).reset_index()

    avg_fp_margin = tx[~tx["is_promotional"]]["margin"].mean()
    cf["promo_dependency_ratio"] = (cf["promo_transactions"] / cf["total_transactions"]).round(4)
    cf["full_price_rate"]        = (cf["full_price_transactions"] / cf["total_transactions"]).round(4)
    cf["margin_erosion_ratio"]   = (1 - cf["avg_margin"] / avg_fp_margin).clip(0, 1).round(4)
    cf["customer_lifetime_days"] = (cf["last_purchase_date"] - cf["first_purchase_date"]).dt.days
    cf["purchase_frequency"]     = (
        cf["total_transactions"] / (cf["customer_lifetime_days"] / 30).clip(lower=1)
    ).round(4)
    snapshot = tx["transaction_date"].max()
    cf["recency_days"]           = (snapshot - cf["last_purchase_date"]).dt.days
    cf["discount_hunger_score"]  = (
        0.5 * cf["promo_dependency_ratio"] + 0.5 * (cf["avg_discount_pct"] / 100)
    ).round(4)
    cf.drop(columns=["last_purchase_date","first_purchase_date"], inplace=True)

    cf = cf.merge(
        cust[["customer_id","age","gender","city_tier","segment",
              "price_sensitivity_score","loyalty_tier",
              "preferred_channel","discount_affinity_label"]],
        on="customer_id", how="left"
    )
    cf["city_tier_enc"]    = cf["city_tier"].map({"Tier 1":1,"Tier 2":2,"Tier 3":3})
    cf["segment_enc"]      = cf["segment"].map({"Premium":1,"Regular":2,"Budget":3})
    cf["loyalty_tier_enc"] = cf["loyalty_tier"].map({"Gold":1,"Silver":2,"Bronze":3})
    cf["channel_enc"]      = cf["preferred_channel"].map({"App":1,"Website":2,"In-Store":3})
    cf["affinity_encoded"] = cf["discount_affinity_label"].map({"Healthy":0,"At-Risk":1,"Addicted":2})
    return cf

# ── Fatigue stats (cached) ────────────────────────────────────────
@st.cache_data
def load_fatigue_data():
    tx, camp, prod, cust = load_raw()
    camp_tx = (
        tx[tx["campaign_id"].notna()]
        .groupby("campaign_id")["transaction_id"].count()
        .reset_index().rename(columns={"transaction_id":"tx_count"})
    )
    ct = camp.merge(camp_tx, on="campaign_id", how="left").fillna(0)
    ct["conversion_rate"] = (ct["tx_count"] / ct["reach"] * 100).round(3)

    results = {}
    for ctype in camp["campaign_type"].unique():
        sub = ct[ct["campaign_type"] == ctype].sort_values("campaign_number_of_type")
        if len(sub) < 5:
            continue
        x    = sub["campaign_number_of_type"].values
        conv = sub["conversion_rate"].values
        disc = sub["discount_pct"].values
        slope_c, _, _, p_c, _ = scipy_stats.linregress(x, conv)
        slope_d, _, _, p_d, _ = scipy_stats.linregress(x, disc)
        sz = min(7, max(3, len(conv)//6))
        conv_s = uniform_filter1d(conv, size=sz).round(3).tolist()
        disc_s = uniform_filter1d(disc, size=sz).round(3).tolist()
        f5c, l5c = round(np.mean(conv_s[:5]),2), round(np.mean(conv_s[-5:]),2)
        f5d, l5d = round(np.mean(disc_s[:5]),2), round(np.mean(disc_s[-5:]),2)
        decay = round((f5c - l5c) / f5c * 100, 1) if f5c > 0 else 0
        results[ctype] = {
            "n": len(sub), "slope_conv": round(float(slope_c),4),
            "p_value": round(float(p_c),4),
            "first5_conv": f5c, "last5_conv": l5c, "decay_pct": decay,
            "first5_disc": f5d, "last5_disc": l5d,
            "disc_escalation": round(l5d - f5d, 1),
            "x": x.tolist(), "conv_raw": conv.round(2).tolist(),
            "conv_smooth": conv_s, "disc_smooth": disc_s,
        }
    return results
