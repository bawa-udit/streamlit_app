import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_loader import load_master, load_raw

def show():
    master = load_master()
    tx, camp, prod, cust = load_raw()

    st.markdown("# 🔍 Discount Addiction Explorer")
    st.markdown("##### Drill into addiction by city tier, segment, product, age, and channel. Every chart responds to your filters.")
    st.markdown("---")

    # ── SIDEBAR FILTERS ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Explorer Filters")

        city_tiers = st.multiselect(
            "City Tier", ["Tier 1","Tier 2","Tier 3"],
            default=["Tier 1","Tier 2","Tier 3"]
        )
        segments = st.multiselect(
            "Customer Segment", ["Premium","Regular","Budget"],
            default=["Premium","Regular","Budget"]
        )
        categories = st.multiselect(
            "Product Category", sorted(master["category"].dropna().unique()),
            default=sorted(master["category"].dropna().unique())
        )
        affinities = st.multiselect(
            "Affinity Label", ["Healthy","At-Risk","Addicted"],
            default=["Healthy","At-Risk","Addicted"]
        )
        age_range = st.slider("Age Range", 18, 70, (18, 70))
        exposure_range = st.slider("Campaign Exposure Count", 0, 50, (0, 50))
        discount_range = st.slider("Discount % Range", 0.0, 35.0, (0.0, 35.0))
        year_filter = st.multiselect(
            "Year", [2021,2022,2023,2024], default=[2021,2022,2023,2024]
        )

    # ── APPLY FILTERS ─────────────────────────────────────────────
    df = master.copy()
    df = df[
        df["city_tier"].isin(city_tiers) &
        df["segment"].isin(segments) &
        df["category"].isin(categories) &
        df["discount_affinity_label"].isin(affinities) &
        df["age"].between(age_range[0], age_range[1]) &
        df["campaign_exposure_count"].between(exposure_range[0], exposure_range[1]) &
        df["discount_pct"].between(discount_range[0], discount_range[1]) &
        df["year"].isin(year_filter)
    ]

    if df.empty:
        st.warning("No data matches your filters. Please adjust the sidebar.")
        return

    # ── FILTER KPIs ───────────────────────────────────────────────
    total_cust_filtered = df["customer_id"].nunique()
    add_rate = (df[df["discount_affinity_label"]=="Addicted"]["customer_id"].nunique() / total_cust_filtered * 100) if total_cust_filtered else 0
    fp_rate  = df["purchased_at_full_price"].mean() * 100
    avg_disc = df[df["discount_pct"]>0]["discount_pct"].mean()
    avg_margin_f = df["margin"].mean()

    st.markdown(f"**{total_cust_filtered:,} unique customers** match your current filters")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Addicted %",       f"{add_rate:.1f}%")
    c2.metric("Full-Price Rate",  f"{fp_rate:.1f}%")
    c3.metric("Avg Discount",     f"{avg_disc:.1f}%")
    c4.metric("Avg Margin",       f"₹{avg_margin_f:,.0f}")

    st.markdown("---")

    # ── TABS ─────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📍 By Region & Segment",
        "📦 By Product",
        "👤 By Demographics",
        "📊 Addiction Heatmap"
    ])

    # ══ TAB 1: REGION & SEGMENT ═══════════════════════════════════
    with tab1:
        col_l, col_r = st.columns(2)

        # Addiction % by city tier
        with col_l:
            st.markdown("#### Addicted + At-Risk % by City Tier")
            tier_aff = (
                df.groupby(["city_tier","discount_affinity_label"])["customer_id"]
                .nunique().reset_index()
            )
            tier_total = df.groupby("city_tier")["customer_id"].nunique().reset_index()
            tier_total.columns = ["city_tier","total"]
            tier_aff = tier_aff.merge(tier_total, on="city_tier")
            tier_aff["pct"] = tier_aff["customer_id"] / tier_aff["total"] * 100

            colors = {"Healthy":"#00c9a7","At-Risk":"#ffb830","Addicted":"#ff4d6d"}
            fig = go.Figure()
            for aff in ["Healthy","At-Risk","Addicted"]:
                sub = tier_aff[tier_aff["discount_affinity_label"]==aff]
                fig.add_bar(
                    x=sub["city_tier"], y=sub["pct"].round(1),
                    name=aff, marker_color=colors[aff],
                    text=sub["pct"].round(1).astype(str)+"%",
                    textposition="inside",
                )
            fig.update_layout(
                barmode="stack", height=320,
                paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
                margin=dict(l=0,r=0,t=10,b=0),
                yaxis=dict(gridcolor="#1e2d45", title="% of customers"),
                xaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Full-price rate by segment + affinity
        with col_r:
            st.markdown("#### Full-Price Purchase Rate by Segment")
            seg_fp = (
                df.groupby(["segment","discount_affinity_label"])["purchased_at_full_price"]
                .mean().reset_index()
            )
            seg_fp["pct"] = seg_fp["purchased_at_full_price"] * 100
            fig2 = px.bar(
                seg_fp, x="segment", y="pct", color="discount_affinity_label",
                barmode="group", color_discrete_map=colors,
                labels={"pct":"Full-Price Rate (%)","segment":"Segment","discount_affinity_label":"Affinity"},
                height=320,
            )
            fig2.update_layout(
                paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
                margin=dict(l=0,r=0,t=10,b=0),
                yaxis=dict(gridcolor="#1e2d45"),
                xaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Margin by city tier + affinity
        st.markdown("#### Avg Transaction Margin by City Tier & Affinity (₹)")
        tier_margin = df.groupby(["city_tier","discount_affinity_label"])["margin"].mean().reset_index()
        fig3 = px.bar(
            tier_margin, x="city_tier", y="margin", color="discount_affinity_label",
            barmode="group", color_discrete_map=colors,
            labels={"margin":"Avg Margin (₹)","city_tier":"City Tier","discount_affinity_label":"Affinity"},
            height=280,
        )
        fig3.update_layout(
            paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(gridcolor="#1e2d45", tickprefix="₹"),
            xaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ══ TAB 2: PRODUCT ════════════════════════════════════════════
    with tab2:
        st.markdown("#### Top Products Where Customers Refuse to Pay Full Price")
        st.caption("These are your most at-risk products — customers have been conditioned to only buy them on discount.")

        n_products = st.slider("Show top N products", 5, 30, 15)

        prod_stats = (
            df.groupby(["product_id","product_name","category","sub_category"]).agg(
                total_txns        = ("transaction_id",          "count"),
                full_price_txns   = ("purchased_at_full_price", "sum"),
                avg_discount      = ("discount_pct",            "mean"),
                avg_margin        = ("margin",                  "mean"),
                total_revenue     = ("revenue",                 "sum"),
                addicted_txns     = ("discount_affinity_label", lambda x: (x=="Addicted").sum()),
            ).reset_index()
        )
        prod_stats["full_price_rate"]  = prod_stats["full_price_txns"] / prod_stats["total_txns"]
        prod_stats["addicted_pct"]     = prod_stats["addicted_txns"] / prod_stats["total_txns"] * 100

        # Filter to products with enough transactions
        prod_stats = prod_stats[prod_stats["total_txns"] >= 50]
        worst = prod_stats.sort_values("full_price_rate").head(n_products)

        col_l, col_r = st.columns([3,2])

        with col_l:
            fig4 = go.Figure()
            fig4.add_bar(
                y=worst["product_name"],
                x=worst["full_price_rate"] * 100,
                orientation="h",
                marker=dict(
                    color=worst["full_price_rate"]*100,
                    colorscale=[[0,"#ff4d6d"],[0.5,"#ffb830"],[1,"#00c9a7"]],
                    showscale=True,
                    colorbar=dict(title="FP Rate %", tickfont_color="#8899bb", title_font_color="#8899bb"),
                ),
                text=[f"{v:.1f}%" for v in worst["full_price_rate"]*100],
                textposition="outside",
                textfont_color="#c8d4f0",
                customdata=worst[["category","avg_discount","addicted_pct","total_txns"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Category: %{customdata[0]}<br>"
                    "Full-Price Rate: %{x:.1f}%<br>"
                    "Avg Discount: %{customdata[1]:.1f}%<br>"
                    "Addicted Buyers: %{customdata[2]:.1f}%<br>"
                    "Total Txns: %{customdata[3]}<extra></extra>"
                ),
            )
            fig4.update_layout(
                height=max(320, n_products*28),
                paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
                xaxis=dict(gridcolor="#1e2d45", title="Full-Price Purchase Rate (%)"),
                yaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig4, use_container_width=True)

        with col_r:
            st.markdown("#### Category Breakdown of At-Risk Products")
            cat_worst = worst.groupby("category")["product_name"].count().reset_index()
            cat_worst.columns = ["category","count"]
            fig5 = go.Figure(go.Pie(
                labels=cat_worst["category"], values=cat_worst["count"],
                hole=0.5,
                marker_colors=["#2d6fff","#00c9a7","#ffb830","#ff4d6d","#8b5cf6"],
                textinfo="label+percent",
            ))
            fig5.update_layout(
                height=280, paper_bgcolor="#080c14", font_color="#8899bb",
                showlegend=False, margin=dict(l=0,r=0,t=10,b=0),
            )
            st.plotly_chart(fig5, use_container_width=True)

            st.markdown("#### Addicted Buyer % vs Full-Price Rate")
            fig6 = px.scatter(
                worst, x="full_price_rate", y="addicted_pct",
                size="total_txns", color="category",
                hover_name="product_name",
                labels={
                    "full_price_rate":"Full-Price Rate",
                    "addicted_pct":"Addicted Buyer %",
                    "total_txns":"Transaction Volume",
                },
                color_discrete_sequence=["#2d6fff","#00c9a7","#ffb830","#ff4d6d","#8b5cf6"],
                height=260,
            )
            fig6.update_layout(
                paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb",
                legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
                margin=dict(l=0,r=0,t=10,b=0),
                xaxis=dict(gridcolor="#1e2d45", tickformat=".0%"),
                yaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig6, use_container_width=True)

        # Product table
        st.markdown("#### Detailed Product Table")
        display_df = worst[[
            "product_name","category","sub_category",
            "total_txns","full_price_rate","avg_discount",
            "avg_margin","addicted_pct","total_revenue"
        ]].copy()
        display_df["full_price_rate"] = (display_df["full_price_rate"]*100).round(1).astype(str) + "%"
        display_df["avg_discount"]    = display_df["avg_discount"].round(1).astype(str) + "%"
        display_df["avg_margin"]      = "₹" + display_df["avg_margin"].round(0).astype(int).astype(str)
        display_df["addicted_pct"]    = display_df["addicted_pct"].round(1).astype(str) + "%"
        display_df["total_revenue"]   = "₹" + (display_df["total_revenue"]/1e6).round(2).astype(str) + "M"
        display_df.columns = ["Product","Category","Sub-Category","Txns","FP Rate","Avg Disc","Avg Margin","Addicted %","Revenue"]
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True, height=320)

    # ══ TAB 3: DEMOGRAPHICS ═══════════════════════════════════════
    with tab3:
        col_l, col_r = st.columns(2)

        # Age vs full-price rate scatter
        with col_l:
            st.markdown("#### Age vs Full-Price Purchase Rate")
            age_fp = df.groupby("age").agg(
                full_price_rate = ("purchased_at_full_price","mean"),
                avg_discount    = ("discount_pct","mean"),
                customer_count  = ("customer_id","nunique"),
            ).reset_index()
            age_fp["full_price_rate_pct"] = age_fp["full_price_rate"] * 100

            fig7 = go.Figure()
            fig7.add_scatter(
                x=age_fp["age"], y=age_fp["full_price_rate_pct"],
                mode="markers+lines",
                marker=dict(
                    size=8, color=age_fp["full_price_rate_pct"],
                    colorscale=[[0,"#ff4d6d"],[0.5,"#ffb830"],[1,"#00c9a7"]],
                    showscale=True,
                    colorbar=dict(title="FP Rate %", tickfont_color="#8899bb", title_font_color="#8899bb"),
                ),
                line=dict(color="#2d6fff", width=1.5),
                hovertemplate="Age: %{x}<br>FP Rate: %{y:.1f}%<extra></extra>",
            )
            fig7.update_layout(
                height=300, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
                xaxis=dict(gridcolor="#1e2d45", title="Age"),
                yaxis=dict(gridcolor="#1e2d45", title="Full-Price Rate (%)"),
            )
            st.plotly_chart(fig7, use_container_width=True)

        # Channel vs addiction
        with col_r:
            st.markdown("#### Addiction Distribution by Preferred Channel")
            chan_aff = df.groupby(["preferred_channel","discount_affinity_label"])["customer_id"].nunique().reset_index()
            chan_total = df.groupby("preferred_channel")["customer_id"].nunique().reset_index()
            chan_total.columns = ["preferred_channel","total"]
            chan_aff = chan_aff.merge(chan_total, on="preferred_channel")
            chan_aff["pct"] = chan_aff["customer_id"] / chan_aff["total"] * 100

            colors = {"Healthy":"#00c9a7","At-Risk":"#ffb830","Addicted":"#ff4d6d"}
            fig8 = go.Figure()
            for aff in ["Healthy","At-Risk","Addicted"]:
                sub = chan_aff[chan_aff["discount_affinity_label"]==aff]
                fig8.add_bar(x=sub["preferred_channel"], y=sub["pct"].round(1),
                             name=aff, marker_color=colors[aff])
            fig8.update_layout(
                barmode="stack", height=300,
                paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
                margin=dict(l=0,r=0,t=10,b=0),
                yaxis=dict(gridcolor="#1e2d45", title="% customers"),
                xaxis=dict(gridcolor="#1e2d45"),
            )
            st.plotly_chart(fig8, use_container_width=True)

        # Loyalty tier vs addiction
        st.markdown("#### Full-Price Rate by Loyalty Tier & Segment")
        loy_seg = df.groupby(["loyalty_tier","segment"])["purchased_at_full_price"].mean().reset_index()
        loy_seg["pct"] = loy_seg["purchased_at_full_price"] * 100
        fig9 = px.bar(
            loy_seg, x="loyalty_tier", y="pct", color="segment",
            barmode="group",
            color_discrete_map={"Premium":"#2d6fff","Regular":"#00c9a7","Budget":"#ffb830"},
            labels={"pct":"Full-Price Rate (%)","loyalty_tier":"Loyalty Tier"},
            height=280,
            category_orders={"loyalty_tier":["Gold","Silver","Bronze"]},
        )
        fig9.update_layout(
            paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
            margin=dict(l=0,r=0,t=10,b=0),
            yaxis=dict(gridcolor="#1e2d45"),
            xaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig9, use_container_width=True)

    # ══ TAB 4: HEATMAP ════════════════════════════════════════════
    with tab4:
        st.markdown("#### Addiction Heatmap — City Tier × Segment")
        st.caption("Cell value = % of customers in that group classified as Addicted")

        pivot_metric = st.selectbox(
            "Metric to show",
            ["Addicted %","At-Risk %","Full-Price Rate %","Avg Discount %","Avg Margin ₹"]
        )

        def compute_pivot(m, dff):
            if m == "Addicted %":
                grp = dff.groupby(["city_tier","segment"]).apply(
                    lambda x: (x["discount_affinity_label"]=="Addicted").mean()*100
                ).reset_index(name="val")
            elif m == "At-Risk %":
                grp = dff.groupby(["city_tier","segment"]).apply(
                    lambda x: (x["discount_affinity_label"]=="At-Risk").mean()*100
                ).reset_index(name="val")
            elif m == "Full-Price Rate %":
                grp = dff.groupby(["city_tier","segment"])["purchased_at_full_price"].mean().reset_index(name="val")
                grp["val"] *= 100
            elif m == "Avg Discount %":
                grp = dff.groupby(["city_tier","segment"])["discount_pct"].mean().reset_index(name="val")
            else:
                grp = dff.groupby(["city_tier","segment"])["margin"].mean().reset_index(name="val")
            pivot = grp.pivot(index="city_tier", columns="segment", values="val").round(1)
            return pivot

        pivot = compute_pivot(pivot_metric, df)

        colorscale = "RdYlGn" if "Full-Price" in pivot_metric or "Margin" in pivot_metric else "RdYlGn_r"
        fmt = ".0f" if "₹" in pivot_metric else ".1f"

        fig10 = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale=colorscale,
            text=pivot.values.round(1),
            texttemplate="%{text}",
            textfont_size=14,
            hoverongaps=False,
        ))
        fig10.update_layout(
            height=320, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(title="Customer Segment"),
            yaxis=dict(title="City Tier"),
        )
        st.plotly_chart(fig10, use_container_width=True)

        # Category × Affinity heatmap
        st.markdown("#### Addiction Heatmap — Product Category × Affinity")
        cat_aff = df.groupby(["category","discount_affinity_label"])["purchased_at_full_price"].mean().reset_index()
        cat_aff["pct"] = cat_aff["purchased_at_full_price"] * 100
        pivot2 = cat_aff.pivot(index="category", columns="discount_affinity_label", values="pct").round(1)
        fig11 = go.Figure(go.Heatmap(
            z=pivot2.values,
            x=pivot2.columns.tolist(),
            y=pivot2.index.tolist(),
            colorscale="RdYlGn",
            text=pivot2.values.round(1),
            texttemplate="%{text}%",
            textfont_size=13,
        ))
        fig11.update_layout(
            height=300, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(title="Affinity Label"),
            yaxis=dict(title="Category"),
        )
        st.plotly_chart(fig11, use_container_width=True)
