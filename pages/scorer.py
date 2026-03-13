import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_loader import load_customer_features, load_master

# ── Train model once, cache it ────────────────────────────────────
@st.cache_resource
def train_model():
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    from xgboost import XGBClassifier

    cf = load_customer_features()
    FEAT = [
        "total_transactions","avg_order_value","avg_margin",
        "avg_discount_pct","max_discount_pct",
        "promo_dependency_ratio","full_price_rate","margin_erosion_ratio",
        "avg_days_between_purchases","avg_campaign_exposure","max_campaign_exposure",
        "recency_days","purchase_frequency","discount_hunger_score",
        "age","price_sensitivity_score",
        "city_tier_enc","segment_enc","loyalty_tier_enc","channel_enc",
    ]
    X = cf[FEAT].fillna(0)
    y = cf["affinity_encoded"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model = XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="mlogloss", random_state=42, verbosity=0,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred,
                                    target_names=["Healthy","At-Risk","Addicted"],
                                    output_dict=True)
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_test, y_pred)
    fi = pd.Series(model.feature_importances_, index=FEAT).sort_values(ascending=False)
    return model, cf, FEAT, report, cm, fi

def score_customer(model, feat_vals, feat_names):
    x = pd.DataFrame([feat_vals], columns=feat_names)
    proba = model.predict_proba(x)[0]
    pred  = model.predict(x)[0]
    score = float(proba[2]*1.0 + proba[1]*0.5)
    label = {0:"Healthy",1:"At-Risk",2:"Addicted"}[pred]
    return score, label, proba

def show():
    st.markdown("# 🎯 Customer Addiction Scorer")
    st.markdown("##### Look up any existing customer by ID, or manually enter behavioural parameters to get a real-time addiction probability score from the trained XGBoost model.")
    st.markdown("---")

    with st.spinner("Loading trained XGBoost model..."):
        model, cf, FEAT, report, cm, fi = train_model()

    master = load_master()

    # ── Model performance summary ─────────────────────────────────
    acc = report["accuracy"]
    with st.expander(f"📊 Model Performance — Accuracy: {acc*100:.1f}% | Click to expand", expanded=False):
        col1, col2, col3 = st.columns(3)
        for label, col in zip(["Healthy","At-Risk","Addicted"],[col1,col2,col3]):
            r = report[label]
            col.markdown(f"""
            <div style='background:#0d1117;border:1px solid #1e2d45;border-radius:8px;padding:14px'>
                <div style='font-size:12px;font-weight:700;color:#c8d4f0;margin-bottom:10px'>{label}</div>
                <div style='font-size:11px;color:#8899bb;line-height:1.8'>
                    Precision: <b style='color:#c8d4f0'>{r["precision"]*100:.1f}%</b><br>
                    Recall:    <b style='color:#c8d4f0'>{r["recall"]*100:.1f}%</b><br>
                    F1-Score:  <b style='color:#c8d4f0'>{r["f1-score"]*100:.1f}%</b><br>
                    Support:   <b style='color:#c8d4f0'>{int(r["support"])}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### Feature Importance (Top 10)")
        fig_fi = go.Figure(go.Bar(
            y=fi.head(10).index[::-1],
            x=fi.head(10).values[::-1],
            orientation="h",
            marker=dict(
                color=fi.head(10).values[::-1],
                colorscale=[[0,"#2d6fff"],[0.5,"#ffb830"],[1,"#ff4d6d"]],
            ),
            text=[f"{v:.4f}" for v in fi.head(10).values[::-1]],
            textposition="outside", textfont_color="#c8d4f0",
        ))
        fig_fi.update_layout(
            height=300, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(gridcolor="#1e2d45"), yaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig_fi, use_container_width=True)

    st.markdown("---")

    # ── Input mode ────────────────────────────────────────────────
    mode = st.radio(
        "How do you want to score?",
        ["🔎 Look up existing customer by ID", "✏️ Enter parameters manually"],
        horizontal=True,
    )

    st.markdown("")

    feat_vals = None

    # ══ MODE 1: LOOKUP ════════════════════════════════════════════
    if "Look up" in mode:
        all_ids = sorted(cf["customer_id"].tolist())
        cust_id = st.selectbox("Select Customer ID", all_ids, index=0)

        if cust_id:
            row = cf[cf["customer_id"] == cust_id].iloc[0]
            feat_vals = {f: row[f] for f in FEAT}

            # Show customer profile
            col_info, col_gauge = st.columns([1,1])
            with col_info:
                st.markdown("#### Customer Profile")
                info_cols = st.columns(3)
                info_cols[0].metric("Segment",     row.get("segment","—"))
                info_cols[1].metric("City Tier",   row.get("city_tier","—"))
                info_cols[2].metric("Loyalty",     row.get("loyalty_tier","—"))
                info_cols2 = st.columns(3)
                info_cols2[0].metric("Age",        int(row.get("age",0)))
                info_cols2[1].metric("Channel",    row.get("preferred_channel","—"))
                info_cols2[2].metric("True Label", row.get("discount_affinity_label","—"))

                st.markdown("#### Behavioural Features")
                beh_col1, beh_col2 = st.columns(2)
                beh_col1.metric("Promo Dependency", f"{row['promo_dependency_ratio']*100:.1f}%")
                beh_col2.metric("Full-Price Rate",  f"{row['full_price_rate']*100:.1f}%")
                beh_col1.metric("Avg Discount Rcvd",f"{row['avg_discount_pct']:.1f}%")
                beh_col2.metric("Margin Erosion",   f"{row['margin_erosion_ratio']*100:.1f}%")
                beh_col1.metric("Avg Campaign Exp", f"{row['avg_campaign_exposure']:.1f}")
                beh_col2.metric("Discount Hunger",  f"{row['discount_hunger_score']:.3f}")

    # ══ MODE 2: MANUAL INPUT ═════════════════════════════════════
    else:
        st.markdown("#### Enter Customer Behaviour Parameters")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Demographic**")
            age = st.slider("Age", 18, 70, 35)
            segment = st.selectbox("Segment", ["Premium","Regular","Budget"])
            city_tier = st.selectbox("City Tier", ["Tier 1","Tier 2","Tier 3"])
            loyalty = st.selectbox("Loyalty Tier", ["Gold","Silver","Bronze"])
            channel = st.selectbox("Channel", ["App","Website","In-Store"])
            price_sens = st.slider("Price Sensitivity Score", 1, 10, 5)

        with col2:
            st.markdown("**Purchase Behaviour**")
            total_txns     = st.slider("Total Transactions",    1,    150,  40)
            promo_dep      = st.slider("Promo Dependency Ratio",0.0,  1.0,  0.4, step=0.01)
            avg_disc       = st.slider("Avg Discount Received (%)", 0.0, 35.0, 10.0, step=0.5)
            max_disc       = st.slider("Max Discount Received (%)", 0.0, 35.0, 20.0, step=0.5)
            avg_aov        = st.number_input("Avg Order Value (₹)", 500, 200000, 15000, step=1000)
            avg_margin     = st.number_input("Avg Margin (₹)",      100,  50000,  4000, step=500)

        with col3:
            st.markdown("**Engagement Signals**")
            recency        = st.slider("Recency (days since last purchase)", 0, 365, 30)
            avg_exp        = st.slider("Avg Campaign Exposure",  0, 50, 10)
            max_exp        = st.slider("Max Campaign Exposure",  0, 50, 20)
            avg_days_gap   = st.slider("Avg Days Between Purchases", 0, 100, 20)

        # Derived
        full_price_rate    = 1.0 - promo_dep
        margin_erosion     = max(0.0, 1.0 - avg_margin / 5897)  # baseline from data
        purchase_freq      = total_txns / max(1, (365 - recency) / 30)
        disc_hunger        = 0.5 * promo_dep + 0.5 * (avg_disc / 100)
        city_enc   = {"Tier 1":1,"Tier 2":2,"Tier 3":3}[city_tier]
        seg_enc    = {"Premium":1,"Regular":2,"Budget":3}[segment]
        loy_enc    = {"Gold":1,"Silver":2,"Bronze":3}[loyalty]
        chan_enc   = {"App":1,"Website":2,"In-Store":3}[channel]

        feat_vals = {
            "total_transactions":        total_txns,
            "avg_order_value":           avg_aov,
            "avg_margin":                avg_margin,
            "avg_discount_pct":          avg_disc,
            "max_discount_pct":          max_disc,
            "promo_dependency_ratio":    promo_dep,
            "full_price_rate":           full_price_rate,
            "margin_erosion_ratio":      margin_erosion,
            "avg_days_between_purchases":avg_days_gap,
            "avg_campaign_exposure":     avg_exp,
            "max_campaign_exposure":     max_exp,
            "recency_days":              recency,
            "purchase_frequency":        purchase_freq,
            "discount_hunger_score":     disc_hunger,
            "age":                       age,
            "price_sensitivity_score":   price_sens,
            "city_tier_enc":             city_enc,
            "segment_enc":               seg_enc,
            "loyalty_tier_enc":          loy_enc,
            "channel_enc":               chan_enc,
        }
        col_gauge = st

    # ── SCORE ─────────────────────────────────────────────────────
    if feat_vals:
        score, label, proba = score_customer(model, feat_vals, FEAT)

        label_color = {"Healthy":"#00c9a7","At-Risk":"#ffb830","Addicted":"#ff4d6d"}.get(label,"#888")
        label_emoji = {"Healthy":"✅","At-Risk":"⚠️","Addicted":"🔴"}.get(label,"")

        st.markdown("---")
        st.markdown("### 🎯 Addiction Score Result")

        res_col1, res_col2, res_col3 = st.columns([1,2,2])

        with res_col1:
            st.markdown(f"""
            <div style='background:#0d1117;border:2px solid {label_color};border-radius:12px;
                        padding:24px;text-align:center'>
                <div style='font-size:48px;margin-bottom:8px'>{label_emoji}</div>
                <div style='font-family:JetBrains Mono,monospace;font-size:44px;font-weight:700;
                            color:{label_color};line-height:1'>{score:.3f}</div>
                <div style='font-size:12px;color:#8899bb;margin-top:4px'>Addiction Score (0–1)</div>
                <div style='font-size:18px;font-weight:700;color:{label_color};margin-top:12px'>{label}</div>
            </div>
            """, unsafe_allow_html=True)

        with res_col2:
            st.markdown("#### Class Probabilities")
            labels_list = ["Healthy","At-Risk","Addicted"]
            clrs = ["#00c9a7","#ffb830","#ff4d6d"]
            fig_p = go.Figure()
            fig_p.add_bar(
                x=labels_list, y=[p*100 for p in proba],
                marker_color=clrs,
                text=[f"{p*100:.1f}%" for p in proba],
                textposition="outside", textfont_color="#c8d4f0",
            )
            fig_p.update_layout(
                height=260, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", margin=dict(l=0,r=0,t=30,b=0),
                yaxis=dict(gridcolor="#1e2d45", title="Probability (%)", range=[0,115]),
                xaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig_p, use_container_width=True)

        with res_col3:
            st.markdown("#### Recommended Action")
            actions = {
                "Healthy": {
                    "color":"#00c9a7",
                    "icon": "✅",
                    "title":"Protect & Reward — Do Not Discount",
                    "actions": [
                        "Offer exclusive early access rather than discounts",
                        "Enrol in premium loyalty tier if not already there",
                        "Use as benchmark segment for campaign measurement",
                        "Monitor: any campaign exposure score increase is a warning sign",
                    ]
                },
                "At-Risk": {
                    "color":"#ffb830",
                    "icon": "⚠️",
                    "title":"Intervene Now — Before Full Addiction Sets In",
                    "actions": [
                        "Pause discount eligibility for next 2 campaigns",
                        "Replace price incentive with free shipping or bundling",
                        "Personalise offers based on browsing — not price",
                        "Track full-price rate monthly; target >50%",
                    ]
                },
                "Addicted": {
                    "color":"#ff4d6d",
                    "icon": "🔴",
                    "title":"Recovery Mode — De-addiction Strategy Required",
                    "actions": [
                        "Exclude from all broad discount campaigns immediately",
                        "Introduce 'value edition' products at lower price points",
                        "Re-train with non-price anchors: service, exclusivity, brand",
                        "Expect short-term revenue dip; track margin recovery instead",
                    ]
                },
            }
            act = actions[label]
            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid {act["color"]}44;
                        border-left:3px solid {act["color"]};border-radius:8px;padding:16px'>
                <div style='font-size:13px;font-weight:700;color:{act["color"]};margin-bottom:10px'>
                    {act["icon"]} {act["title"]}
                </div>
                {''.join([f'<div style="font-size:11px;color:#8899bb;margin-bottom:6px;padding-left:8px">• {a}</div>' for a in act["actions"]])}
            </div>
            """, unsafe_allow_html=True)

        # ── Customer cohort comparison ────────────────────────────
        st.markdown("---")
        st.markdown("#### How This Customer Compares to the Full Population")
        comp_metrics = [
            ("Promo Dependency", feat_vals["promo_dependency_ratio"], cf["promo_dependency_ratio"].mean(), cf["promo_dependency_ratio"].quantile(0.75), False),
            ("Full-Price Rate",  feat_vals["full_price_rate"],        cf["full_price_rate"].mean(),        cf["full_price_rate"].quantile(0.25),         True),
            ("Avg Discount %",   feat_vals["avg_discount_pct"]/100,   cf["avg_discount_pct"].mean()/100,   cf["avg_discount_pct"].quantile(0.75)/100,    False),
            ("Campaign Exposure",feat_vals["avg_campaign_exposure"]/50,cf["avg_campaign_exposure"].mean()/50,cf["avg_campaign_exposure"].quantile(0.75)/50,False),
        ]
        comp_cols = st.columns(4)
        for col, (name, this_val, pop_mean, danger_thresh, invert) in zip(comp_cols, comp_metrics):
            pct = this_val * 100
            pop_pct = pop_mean * 100
            danger_pct = danger_thresh * 100
            diff = pct - pop_pct
            is_bad = (diff > 0 and not invert) or (diff < 0 and invert)
            col.metric(
                name,
                f"{pct:.1f}%",
                delta=f"{diff:+.1f}pp vs avg",
                delta_color="inverse" if is_bad else "normal",
            )
