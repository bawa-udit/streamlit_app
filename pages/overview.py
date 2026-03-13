import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_loader import load_raw, load_master

def show():
    tx, camp, prod, cust = load_raw()
    master = load_master()

    st.markdown("# 🏠 Overview")
    st.markdown("##### The business problem: discount-driven revenue is hiding a margin crisis and conditioning customers to never pay full price.")
    st.markdown("---")

    # ── Top KPIs ─────────────────────────────────────────────────
    total_rev       = tx["revenue"].sum()
    promo_rev       = tx[tx["is_promotional"]]["revenue"].sum()
    margin_promo    = tx[tx["is_promotional"]]["margin"].mean()
    margin_nonpromo = tx[~tx["is_promotional"]]["margin"].mean()
    erosion         = (margin_nonpromo - margin_promo) / margin_nonpromo * 100
    addicted_n      = (cust["discount_affinity_label"] == "Addicted").sum()
    atrisk_n        = (cust["discount_affinity_label"] == "At-Risk").sum()

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Revenue",      f"₹{total_rev/1e9:.2f}B")
    c2.metric("Promo Revenue Share", f"{promo_rev/total_rev*100:.1f}%", delta="↑ rising YoY", delta_color="inverse")
    c3.metric("Margin Erosion",      f"{erosion:.1f}%", delta="vs full-price orders", delta_color="inverse")
    c4.metric("Addicted Customers",  f"{addicted_n:,}", delta=f"{addicted_n/len(cust)*100:.1f}% of base", delta_color="inverse")
    c5.metric("At-Risk Customers",   f"{atrisk_n:,}",   delta=f"{atrisk_n/len(cust)*100:.1f}% of base",  delta_color="inverse")
    c6.metric("Avg Margin Loss/Promo Order", f"₹{margin_nonpromo-margin_promo:,.0f}", delta_color="inverse")

    st.markdown("---")

    col_l, col_r = st.columns([2, 1])

    # ── Monthly revenue stacked bar ───────────────────────────────
    with col_l:
        st.markdown("#### Monthly Revenue — Full Price vs Promotional")
        monthly = (
            tx.groupby(["month","is_promotional"])["revenue"]
            .sum().unstack(fill_value=0).reset_index().sort_values("month")
        )
        fig = go.Figure()
        fig.add_bar(x=monthly["month"], y=monthly[False]/1e6,
                    name="Full Price", marker_color="#2d6fff", opacity=0.85)
        fig.add_bar(x=monthly["month"], y=monthly[True]/1e6,
                    name="Promotional", marker_color="#00c9a7", opacity=0.8)
        fig.update_layout(
            barmode="stack", height=320,
            paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", font_size=11,
            legend=dict(bgcolor="#0d1117", bordercolor="#1e2d45"),
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(gridcolor="#1e2d45", tickangle=-30, nticks=12),
            yaxis=dict(gridcolor="#1e2d45", title="Revenue (₹M)"),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Affinity donut ────────────────────────────────────────────
    with col_r:
        st.markdown("#### Customer Discount Affinity")
        aff = cust["discount_affinity_label"].value_counts().reset_index()
        aff.columns = ["label","count"]
        fig2 = go.Figure(go.Pie(
            labels=aff["label"], values=aff["count"],
            hole=0.6,
            marker_colors=["#00c9a7","#ffb830","#ff4d6d"],
            textinfo="percent+label",
            textfont_size=12,
        ))
        fig2.update_layout(
            height=320, paper_bgcolor="#080c14",
            font_color="#8899bb",
            showlegend=False,
            margin=dict(l=0,r=0,t=10,b=0),
            annotations=[dict(text=f"5,000<br>customers", x=0.5, y=0.5,
                              font_size=13, font_color="#c8d4f0", showarrow=False)]
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    col_a, col_b, col_c = st.columns(3)

    # ── Margin comparison bar ─────────────────────────────────────
    with col_a:
        st.markdown("#### Promo vs Full-Price Margin (₹)")
        fig3 = go.Figure(go.Bar(
            x=["Full Price", "Promotional"],
            y=[margin_nonpromo, margin_promo],
            marker_color=["#2d6fff","#ff4d6d"],
            text=[f"₹{margin_nonpromo:,.0f}", f"₹{margin_promo:,.0f}"],
            textposition="outside", textfont_color="#c8d4f0",
        ))
        fig3.update_layout(
            height=280, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(gridcolor="#1e2d45", range=[0, margin_nonpromo*1.3]),
            xaxis=dict(gridcolor="#1e2d45"),
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Revenue by category ───────────────────────────────────────
    with col_b:
        st.markdown("#### Revenue by Category (₹M)")
        cat_rev = master.groupby("category")["revenue"].sum().sort_values() / 1e6
        fig4 = go.Figure(go.Bar(
            y=cat_rev.index, x=cat_rev.values,
            orientation="h",
            marker_color=["#00c9a7","#2d6fff","#ffb830","#ff4d6d","#8b5cf6"],
            text=[f"₹{v:.0f}M" for v in cat_rev.values],
            textposition="outside", textfont_color="#c8d4f0",
        ))
        fig4.update_layout(
            height=280, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(gridcolor="#1e2d45", range=[0, cat_rev.max()*1.25]),
            yaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Promo share YoY ───────────────────────────────────────────
    with col_c:
        st.markdown("#### Promo Revenue Share by Year")
        py = tx.groupby(["year","is_promotional"])["revenue"].sum().unstack(fill_value=0)
        py["share"] = py[True] / (py[True] + py[False]) * 100
        py = py.reset_index()
        fig5 = go.Figure(go.Bar(
            x=py["year"].astype(str), y=py["share"].round(1),
            marker_color=["#2d6fff","#00c9a7","#ffb830","#ff4d6d"],
            text=[f"{v:.1f}%" for v in py["share"]],
            textposition="outside", textfont_color="#c8d4f0",
        ))
        fig5.add_hline(y=py["share"].mean(), line_dash="dash",
                       line_color="#ff4d6d", opacity=0.6,
                       annotation_text=f"Avg {py['share'].mean():.1f}%",
                       annotation_font_color="#ff7a94")
        fig5.update_layout(
            height=280, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(gridcolor="#1e2d45", range=[0, py["share"].max()*1.3]),
            xaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ── Blind spots callout ───────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ⚠️ What Traditional Dashboards Miss")
    b1,b2,b3,b4 = st.columns(4)
    blindspots = [
        ("📉","Margin Erosion",      f"₹{margin_nonpromo-margin_promo:,.0f} lost per promo order — invisible when only tracking revenue"),
        ("🔄","Discount Addiction",  f"{addicted_n+atrisk_n:,} customers ({(addicted_n+atrisk_n)/len(cust)*100:.0f}%) conditioned to wait for deals"),
        ("😴","Campaign Fatigue",    "Conversion rates decline with each campaign repetition — companies compensate with bigger discounts"),
        ("🔮","Future Demand Loss",  "Addicted customers reduce full-price buying permanently — long-term revenue ceiling collapses"),
    ]
    for col, (icon, title, body) in zip([b1,b2,b3,b4], blindspots):
        col.markdown(f"""
        <div style='background:#0d1117;border:1px solid #1e2d45;border-left:3px solid #ff4d6d;
                    border-radius:8px;padding:14px;height:130px'>
            <div style='font-size:20px;margin-bottom:6px'>{icon}</div>
            <div style='font-size:12px;font-weight:700;color:#ff7a94;margin-bottom:6px'>{title}</div>
            <div style='font-size:11px;color:#5c7194;line-height:1.5'>{body}</div>
        </div>
        """, unsafe_allow_html=True)
