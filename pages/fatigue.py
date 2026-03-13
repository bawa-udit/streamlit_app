import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_loader import load_fatigue_data, load_raw

COLORS = {
    "Flash Sale":     "#2d6fff",
    "Seasonal":       "#00c9a7",
    "Email Blast":    "#ffb830",
    "Loyalty Reward": "#8b5cf6",
    "Clearance":      "#ff4d6d",
}

def show():
    fat  = load_fatigue_data()
    tx, camp, prod, cust = load_raw()

    st.markdown("# 📉 Promotion Fatigue Curves")
    st.markdown("##### The same campaign type repeated too many times converts fewer customers — and companies compensate by offering bigger discounts, making it worse.")
    st.markdown("---")

    # ── Sidebar filters ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📉 Fatigue Filters")
        selected_types = st.multiselect(
            "Campaign Types",
            list(fat.keys()),
            default=list(fat.keys()),
        )
        show_raw    = st.checkbox("Show raw data points", value=False)
        show_smooth = st.checkbox("Show smoothed trend line", value=True)

    if not selected_types:
        st.warning("Select at least one campaign type.")
        return

    # ── Summary metric cards ──────────────────────────────────────
    cols = st.columns(len(selected_types))
    for col, ctype in zip(cols, selected_types):
        v = fat[ctype]
        decay = v["decay_pct"]
        arrow = "↓" if decay > 5 else "↑" if decay < -5 else "→"
        delta_color = "inverse" if decay > 5 else "normal" if decay < -5 else "off"
        col.metric(
            label=ctype,
            value=f"{v['first5_conv']}% → {v['last5_conv']}%",
            delta=f"{arrow} {abs(decay):.1f}% decay  |  +{v['disc_escalation']}pp discount",
            delta_color=delta_color,
        )

    st.markdown("---")

    # ── MAIN CHARTS ───────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📉 Conversion Decay",
        "💸 Discount Escalation",
        "🔁 Vicious Cycle Deep Dive"
    ])

    # ══ TAB 1: Conversion Rate ════════════════════════════════════
    with tab1:
        col_l, col_r = st.columns([3,1])

        with col_l:
            st.markdown("#### Conversion Rate vs Campaign Repetition Number")
            st.caption("Each point = one campaign run. Downward trend = fatigue is real.")
            fig = go.Figure()
            for ctype in selected_types:
                v = fat[ctype]
                color = COLORS.get(ctype,"#888")
                if show_raw:
                    fig.add_scatter(
                        x=v["x"], y=v["conv_raw"],
                        mode="markers", name=f"{ctype} (raw)",
                        marker=dict(color=color, size=5, opacity=0.35),
                        showlegend=True,
                    )
                if show_smooth:
                    fig.add_scatter(
                        x=v["x"], y=v["conv_smooth"],
                        mode="lines", name=ctype,
                        line=dict(color=color, width=2.5),
                        fill="tozeroy", fillcolor=color.replace("#","rgba(").rstrip(")") if color.startswith("#") else color,
                    )
                    # Trend annotation
                    slope = v["slope_conv"]
                    direction = "↓ Decaying" if slope < -0.05 else "↑ Growing" if slope > 0.05 else "→ Stable"
                    fig.add_annotation(
                        x=v["x"][-1], y=v["conv_smooth"][-1],
                        text=f"  {direction} ({slope:+.2f}%/run)",
                        showarrow=False, font=dict(size=10, color=color),
                        xanchor="left",
                    )

            fig.update_layout(
                height=380, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb",
                legend=dict(bgcolor="#0d1117", bordercolor="#1e2d45"),
                margin=dict(l=0,r=60,t=10,b=0),
                xaxis=dict(gridcolor="#1e2d45", title="Campaign Repetition # (nth time this type ran)"),
                yaxis=dict(gridcolor="#1e2d45", title="Conversion Rate (%)"),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### First 5 vs Last 5")
            for ctype in selected_types:
                v = fat[ctype]
                color = COLORS.get(ctype,"#888")
                decay = v["decay_pct"]
                sign  = "📉" if decay > 5 else "📈" if decay < -5 else "➡️"
                st.markdown(f"""
                <div style='background:#0d1117;border:1px solid #1e2d45;
                            border-left:3px solid {color};border-radius:6px;
                            padding:10px 12px;margin-bottom:8px'>
                    <div style='font-size:11px;font-weight:700;color:{color};margin-bottom:4px'>{sign} {ctype}</div>
                    <div style='font-size:11px;color:#8899bb'>
                        First 5: <b style='color:#c8d4f0'>{v["first5_conv"]}%</b><br>
                        Last 5:  <b style='color:{"#ff7a94" if decay>5 else "#00f5cc"}'>{v["last5_conv"]}%</b><br>
                        Decay:   <b style='color:{"#ff7a94" if decay>5 else "#ffd47a"}'>{abs(decay):.1f}%</b><br>
                        Runs:    <b style='color:#c8d4f0'>{v["n"]}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Bar chart: First 5 vs Last 5 side by side
        st.markdown("#### First 5 vs Last 5 Campaigns — Head to Head")
        ctypes_sel  = selected_types
        first5_vals = [fat[c]["first5_conv"] for c in ctypes_sel]
        last5_vals  = [fat[c]["last5_conv"]  for c in ctypes_sel]

        fig2 = go.Figure()
        fig2.add_bar(x=ctypes_sel, y=first5_vals, name="First 5 Campaigns",
                     marker_color="#00c9a7", text=[f"{v}%" for v in first5_vals],
                     textposition="outside", textfont_color="#c8d4f0")
        fig2.add_bar(x=ctypes_sel, y=last5_vals,  name="Last 5 Campaigns",
                     marker_color="#ff4d6d",  text=[f"{v}%" for v in last5_vals],
                     textposition="outside", textfont_color="#c8d4f0")
        for i, (f, l, ct) in enumerate(zip(first5_vals, last5_vals, ctypes_sel)):
            diff = f - l
            if abs(diff) > 1:
                fig2.add_annotation(
                    x=ct, y=max(f, l) + 2,
                    text=f"{'↓' if diff>0 else '↑'}{abs(diff):.1f}pp",
                    showarrow=False,
                    font=dict(size=11, color="#ff7a94" if diff > 0 else "#00f5cc"),
                )
        fig2.update_layout(
            barmode="group", height=320,
            paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
            margin=dict(l=0,r=0,t=30,b=0),
            yaxis=dict(gridcolor="#1e2d45", title="Avg Conversion Rate (%)"),
            xaxis=dict(gridcolor="#1e2d45"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ══ TAB 2: Discount Escalation ════════════════════════════════
    with tab2:
        st.markdown("#### Discount % Offered vs Campaign Repetition Number")
        st.caption("As conversion falls, marketers raise the discount to compensate — training customers to expect bigger deals.")
        fig3 = go.Figure()
        for ctype in selected_types:
            v = fat[ctype]
            color = COLORS.get(ctype,"#888")
            if show_raw:
                fig3.add_scatter(
                    x=v["x"], y=[fat[ctype]["disc_smooth"][min(i,len(v["disc_smooth"])-1)] for i in range(len(v["x"]))],
                    mode="markers", name=f"{ctype} (raw)",
                    marker=dict(color=color, size=5, opacity=0.3),
                )
            if show_smooth:
                fig3.add_scatter(
                    x=v["x"], y=v["disc_smooth"],
                    mode="lines", name=ctype,
                    line=dict(color=color, width=2.5),
                )
        fig3.update_layout(
            height=360, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
            font_color="#8899bb", legend=dict(bgcolor="#0d1117",bordercolor="#1e2d45"),
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(gridcolor="#1e2d45", title="Campaign Repetition Number"),
            yaxis=dict(gridcolor="#1e2d45", title="Avg Discount % Offered"),
        )
        st.plotly_chart(fig3, use_container_width=True)

        # Escalation summary
        st.markdown("#### Discount Escalation Summary")
        cols_e = st.columns(len(selected_types))
        for col, ctype in zip(cols_e, selected_types):
            v = fat[ctype]
            color = COLORS.get(ctype,"#888")
            col.markdown(f"""
            <div style='background:#0d1117;border:1px solid #1e2d45;
                        border-top:3px solid {color};border-radius:8px;padding:14px;text-align:center'>
                <div style='font-size:11px;font-weight:700;color:{color};margin-bottom:8px'>{ctype}</div>
                <div style='font-size:22px;font-weight:700;color:#ffb830'>+{v["disc_escalation"]}pp</div>
                <div style='font-size:10px;color:#5c7194;margin-top:4px'>
                    {v["first5_disc"]}% → {v["last5_disc"]}%
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ══ TAB 3: Vicious Cycle ═════════════════════════════════════
    with tab3:
        vicious_type = st.selectbox("Select campaign type for deep dive", selected_types)
        v = fat[vicious_type]
        color = COLORS.get(vicious_type,"#888")

        col_l, col_r = st.columns([3,2])

        with col_l:
            st.markdown(f"#### {vicious_type} — Conversion Rate vs Discount % Over Time")
            st.caption("The vicious cycle: conversion falls → discount rises → customers expect discounts → conversion falls further")

            fig4 = go.Figure()
            fig4.add_scatter(
                x=v["x"], y=v["conv_smooth"],
                name="Conversion Rate", mode="lines",
                line=dict(color=color, width=2.5),
                fill="tozeroy", fillcolor=color+"22",
                yaxis="y1",
            )
            fig4.add_scatter(
                x=v["x"], y=v["disc_smooth"],
                name="Discount %", mode="lines",
                line=dict(color="#ff4d6d", width=2, dash="dash"),
                yaxis="y2",
            )
            fig4.update_layout(
                height=360, paper_bgcolor="#080c14", plot_bgcolor="#0d1117",
                font_color="#8899bb",
                legend=dict(bgcolor="#0d1117", bordercolor="#1e2d45"),
                margin=dict(l=0,r=60,t=10,b=0),
                xaxis=dict(gridcolor="#1e2d45", title="Campaign Number"),
                yaxis=dict(gridcolor="#1e2d45", title="Conversion Rate (%)", color=color),
                yaxis2=dict(
                    title="Discount %", color="#ff4d6d",
                    overlaying="y", side="right", gridcolor="#1e2d45"
                ),
            )
            st.plotly_chart(fig4, use_container_width=True)

        with col_r:
            st.markdown("#### The Vicious Cycle Explained")
            steps = [
                ("#2d6fff", "1. Campaign launches",           "Runs campaign type for the Nth time. Initial conversion is strong."),
                ("#ffb830", "2. Customers become familiar",   "Repeat exposure causes desensitisation. Fewer customers act urgently."),
                ("#ff4d6d", "3. Conversion rate falls",        f"Decay: {v['first5_conv']}% → {v['last5_conv']}% over {v['n']} runs."),
                ("#8b5cf6", "4. Company raises discount",      f"Discount escalates from {v['first5_disc']}% → {v['last5_disc']}% (+{v['disc_escalation']}pp)."),
                ("#00c9a7", "5. Customers learn to wait",      "Bigger discounts reward waiting. Customers now only buy on deal."),
                ("#ff4d6d", "6. Cycle repeats, worse",         "Next run needs an even bigger discount. Margin collapses permanently."),
            ]
            for clr, title, body in steps:
                st.markdown(f"""
                <div style='background:#0d1117;border-left:3px solid {clr};border-radius:5px;
                            padding:10px 12px;margin-bottom:7px'>
                    <div style='font-size:11px;font-weight:700;color:{clr};margin-bottom:3px'>{title}</div>
                    <div style='font-size:11px;color:#5c7194'>{body}</div>
                </div>
                """, unsafe_allow_html=True)

        # Statistical summary table
        st.markdown("---")
        st.markdown("#### Statistical Summary — All Campaign Types")
        rows = []
        for ct in list(fat.keys()):
            v2 = fat[ct]
            rows.append({
                "Campaign Type":     ct,
                "# Runs":            v2["n"],
                "Conv Slope/Run":    f"{v2['slope_conv']:+.3f}%",
                "p-value":           f"{v2['p_value']:.4f}",
                "Significant?":      "✅ Yes" if v2["p_value"] < 0.05 else "❌ No",
                "First 5 Conv":      f"{v2['first5_conv']}%",
                "Last 5 Conv":       f"{v2['last5_conv']}%",
                "Decay":             f"{v2['decay_pct']:+.1f}%",
                "Disc Escalation":   f"+{v2['disc_escalation']}pp",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
