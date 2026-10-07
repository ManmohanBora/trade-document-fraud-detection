"""
Streamlit + Plotly Compliance Dashboard.

Enterprise audit interface for multi-modal trade document fraud detection.
Displays audit logs, multi-modal evidence breakdowns, explainability charts,
and auditor review workflows.
"""

from __future__ import annotations

import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure page layout and metadata
st.set_page_config(
    page_title="Trade Document Compliance & Fraud Audit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for refined enterprise compliance aesthetic
st.markdown(
    """
    <style>
    :root {
        --primary-navy: #0F172A;
        --slate-blue: #1E293B;
        --teal-accent: #0D9488;
        --amber-warning: #D97706;
        --card-bg: #F8FAFC;
        --card-border: #E2E8F0;
    }
    .main {
        background-color: #F8FAFC;
    }
    .audit-card {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 1.2rem;
    }
    .badge-high {
        background-color: #FEF3C7;
        color: #92400E;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        border: 1px solid #FCD34D;
        display: inline-block;
    }
    .badge-medium {
        background-color: #FEF9C3;
        color: #854D0E;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        border: 1px solid #FDE047;
        display: inline-block;
    }
    .badge-low {
        background-color: #CCFBF1;
        color: #115E59;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        border: 1px solid #99F6E4;
        display: inline-block;
    }
    .disclaimer-box {
        background-color: #F0FDFA;
        border-left: 4px solid #0D9488;
        color: #134E4A;
        padding: 0.85rem 1.1rem;
        border-radius: 4px;
        font-size: 0.92rem;
        margin-top: 1rem;
    }
    .stMetric {
        background: white;
        padding: 12px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Section
st.title("🛡️ Multi-Modal Trade Compliance & Audit Dashboard")
st.caption("AI-Assisted Document Forensic Pipeline · Enterprise Compliance Engine v0.1.0")

# Auditor Disclaimer Notice
st.markdown(
    """
    <div class="disclaimer-box">
        <strong>⚖️ Human-in-the-Loop Advisory:</strong> AI-generated risk indicator—not proof of fraud. Final decision remains with the human auditor.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# Sample Datasets
SAMPLE_RECORDS = [
    {
        "audit_id": "AUD-2026-9014",
        "filename": "Invoice_001.pdf",
        "doc_type": "Commercial Invoice",
        "risk_score": 78,
        "risk_level": "High",
        "reasons": [
            "Suspicious visual alteration",
            "Amount inconsistency",
            "Unusual document layout",
        ],
        "invoice_no": "INV-89104-DE",
        "amount": 248500.00,
        "currency": "EUR",
        "hs_code": "8471.30",
        "container_no": "MSCU7829104",
        "reviewed": False,
        "uploaded_at": "2026-10-06 14:32:10",
        "visual_score": 82,
        "text_score": 74,
        "layout_score": 79,
    },
    {
        "audit_id": "AUD-2026-9012",
        "filename": "Bill_of_Lading_772.pdf",
        "doc_type": "Bill of Lading",
        "risk_score": 45,
        "risk_level": "Medium",
        "reasons": ["Unregistered carrier stamp format", "Date sequence anomaly"],
        "invoice_no": "BOL-9921-HK",
        "amount": 112000.00,
        "currency": "USD",
        "hs_code": "8517.62",
        "container_no": "CMAU3381920",
        "reviewed": True,
        "reviewed_by": "J. Vance (Senior Auditor)",
        "uploaded_at": "2026-10-06 13:15:40",
        "visual_score": 40,
        "text_score": 52,
        "layout_score": 42,
    },
    {
        "audit_id": "AUD-2026-9008",
        "filename": "Customs_Dec_409.pdf",
        "doc_type": "Customs Document",
        "risk_score": 14,
        "risk_level": "Low",
        "reasons": ["All multimodal criteria verified compliant"],
        "invoice_no": "CD-44019-SG",
        "amount": 45300.00,
        "currency": "SGD",
        "hs_code": "8473.30",
        "container_no": "EGLV5501928",
        "reviewed": True,
        "reviewed_by": "Automated Spot-Check",
        "uploaded_at": "2026-10-06 11:40:22",
        "visual_score": 10,
        "text_score": 18,
        "layout_score": 12,
    },
    {
        "audit_id": "AUD-2026-8994",
        "filename": "Commercial_Invoice_302.pdf",
        "doc_type": "Commercial Invoice",
        "risk_score": 28,
        "risk_level": "Low",
        "reasons": ["Minor OCR font degradation; cross-fields match"],
        "invoice_no": "INV-77310-US",
        "amount": 89000.00,
        "currency": "USD",
        "hs_code": "8481.80",
        "container_no": "HLXU9920145",
        "reviewed": True,
        "reviewed_by": "M. Al-Hashimi",
        "uploaded_at": "2026-10-06 09:21:05",
        "visual_score": 22,
        "text_score": 31,
        "layout_score": 25,
    },
]

df = pd.DataFrame(SAMPLE_RECORDS)

# Top KPI Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total Audited Documents", value=len(df), delta="+4 today")
with col2:
    high_count = len(df[df["risk_level"] == "High"])
    st.metric(label="High Risk Flags", value=high_count, delta="Requires Auditor Review", delta_color="inverse")
with col3:
    avg_score = int(df["risk_score"].mean())
    st.metric(label="Avg Composite Risk Score", value=f"{avg_score}/100")
with col4:
    pending_count = len(df[~df["reviewed"]])
    st.metric(label="Pending Human Review", value=pending_count, delta="1 Priority Queue", delta_color="inverse")

st.markdown("---")

# Main Content Layout: Left = Audit Queue & Analytics, Right = Detailed Document Inspector
left_col, right_col = st.columns([1.1, 0.9])

with left_col:
    st.subheader("📋 Pipeline Audit Records")
    
    # Filter Controls
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        risk_filter = st.selectbox("Filter Risk Level", ["All", "High", "Medium", "Low"])
    with f_col2:
        doc_filter = st.selectbox("Filter Document Type", ["All", "Commercial Invoice", "Bill of Lading", "Customs Document"])

    filtered_df = df.copy()
    if risk_filter != "All":
        filtered_df = filtered_df[filtered_df["risk_level"] == risk_filter]
    if doc_filter != "All":
        filtered_df = filtered_df[filtered_df["doc_type"] == doc_filter]

    # Display Table
    st.dataframe(
        filtered_df[["audit_id", "filename", "doc_type", "risk_score", "risk_level", "reviewed"]],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("📊 Multimodal Risk Distribution")
    # Plotly Visualizations
    tab_chart1, tab_chart2 = st.tabs(["Risk by Category", "Branch Correlation"])
    
    with tab_chart1:
        fig_bar = px.bar(
            df,
            x="filename",
            y=["visual_score", "text_score", "layout_score"],
            title="Evidence Decomposition per Document",
            barmode="group",
            labels={"value": "Risk Contribution", "variable": "Branch"},
            color_discrete_map={
                "visual_score": "#1E3A8A",
                "text_score": "#0D9488",
                "layout_score": "#D97706",
            },
        )
        fig_bar.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab_chart2:
        fig_radar = go.Figure()
        doc_selected = df[df["filename"] == "Invoice_001.pdf"].iloc[0]
        categories = ["Visual Alteration", "Layout Integrity", "NLP Extraction", "Stamp/Seal Match", "Cross-Entity Match"]
        fig_radar.add_trace(go.Scatterpolar(
            r=[85, 78, 65, 80, 72],
            theta=categories,
            fill="toself",
            name="Invoice_001.pdf",
            line_color="#D97706",
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=280,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

with right_col:
    st.subheader("🔍 Focused Document Inspector")
    
    selected_filename = st.selectbox(
        "Select Document to Inspect:",
        df["filename"].tolist(),
        index=0,  # Defaults to Invoice_001.pdf
    )

    doc_data = df[df["filename"] == selected_filename].iloc[0]

    # Exactly requested Audit-Result Card
    badge_class = f"badge-{doc_data['risk_level'].lower()}"
    reasons_formatted = " · ".join(doc_data["reasons"])

    st.markdown(
        f"""
        <div class="audit-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                <h4 style="margin: 0; color: #0F172A;">Document: {doc_data['filename']}</h4>
                <span class="{badge_class}">Risk Level: {doc_data['risk_level']}</span>
            </div>
            <div style="font-size: 1.15rem; font-weight: 700; color: #1E293B; margin-bottom: 0.6rem;">
                Risk Score: {doc_data['risk_score']}/100
            </div>
            <div style="color: #475569; font-size: 0.95rem; margin-bottom: 0.8rem;">
                <strong>Reasons:</strong> {reasons_formatted}
            </div>
            <div style="background-color: #F1F5F9; border-left: 3px solid #64748B; padding: 0.5rem 0.8rem; font-size: 0.85rem; color: #334155;">
                <em>AI-generated risk indicator—not proof of fraud. Final decision remains with the human auditor.</em>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Visual Document Preview with Forensic AI Overlay
    st.markdown("##### 📄 Document Forensic Viewer")
    doc_base_stem = doc_data['filename'].replace('.pdf', '')
    raw_img_path = Path("data/samples") / f"{doc_base_stem}.png"
    annotated_img_path = Path("data/samples") / f"{doc_base_stem}_forensic_annotated.png"

    view_mode = st.radio(
        "Display Mode:",
        ["Forensic AI Overlay (Altered Regions & Stamp)", "Original Document"],
        horizontal=True,
    )

    if view_mode.startswith("Forensic") and annotated_img_path.exists():
        st.image(str(annotated_img_path), caption=f"Forensic Detection Overlay: {doc_data['filename']}", use_container_width=True)
    elif raw_img_path.exists():
        st.image(str(raw_img_path), caption=f"Document Image: {doc_data['filename']}", use_container_width=True)
    else:
        st.info("Document raster preview available in `data/samples/`.")

    # Forensic Findings Accordion
    with st.expander("🔬 Multimodal Evidence Breakdown", expanded=True):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.markdown("**Image Analytics (OpenCV / YOLO / ResNet):**")
            st.markdown("- Signature: *Detected, low stroke continuity*")
            st.markdown("- Stamp/Seal: *Mismatched perimeter ring*")
            st.markdown("- ELA Tamper Heatmap: *Alteration in Total Box*")
        with col_e2:
            st.markdown("**NLP / LayoutLMv3 Extraction:**")
            st.markdown(f"- Invoice No: `{doc_data['invoice_no']}`")
            st.markdown(f"- Amount: `{doc_data['currency']} {doc_data['amount']:,.2f}`")
            st.markdown(f"- HS Code: `{doc_data['hs_code']}`")
            st.markdown(f"- Container: `{doc_data['container_no']}`")

    # Auditor Action Panel
    st.subheader("✍️ Auditor Sign-Off & Disposition")
    audit_notes = st.text_area("Auditor Examination Notes", placeholder="Enter official compliance observations here...")
    
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("✅ Approve Document", use_container_width=True):
            st.success("Document marked approved by human auditor.")
    with btn_col2:
        if st.button("⚠️ Request Secondary Review", use_container_width=True):
            st.warning("Flagged for secondary forensic verification.")
    with btn_col3:
        if st.button("🚫 Issue Discrepancy Notice", use_container_width=True):
            st.error("Compliance discrepancy notice dispatched to shipper.")
