import time
import os
import pandas as pd
from pymongo import MongoClient
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def get_client():
    uri = "mongodb://mongo:27017" if os.path.exists("/.dockerenv") else "mongodb://localhost:27017"
    return MongoClient(uri)

# Page config
st.set_page_config(
    layout="wide",
    page_title="IoT Malware - Live Dashboard",
    page_icon="🔴"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .malicious {
        color: #ff4b4b;
        font-weight: bold;
    }
    .benign {
        color: #00cc66;
        font-weight: bold;
    }
    .live-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #ff4b4b;
        border-radius: 50%;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    </style>
""", unsafe_allow_html=True)

# Title with live indicator
col_title, col_indicator = st.columns([10, 1])
with col_title:
    st.title("🛡️ IoT Malware Detection - Real-Time Dashboard")
with col_indicator:
    st.markdown('<div class="live-indicator"></div> <span style="color:#ff4b4b;">LIVE</span>', unsafe_allow_html=True)

# Sidebar controls
st.sidebar.header("⚙️ Controls")
limit = st.sidebar.slider("📊 Max records to display", 1000, 20000, 5000, step=1000)
refresh_sec = st.sidebar.slider("🔄 Auto-refresh (seconds)", 1, 10, 2)
show_table = st.sidebar.checkbox("📋 Show live predictions table", value=True)
show_last_n = st.sidebar.slider("📝 Show last N predictions", 5, 50, 20)

# Connect to MongoDB
client = get_client()
col = client["iot_malware"]["predictions"]

# Fetch data
cursor = col.find({}).sort([("_id", -1)]).limit(limit)
df = pd.DataFrame(list(cursor))

if df.empty:
    st.warning("⏳ Waiting for data... Make sure the producer and predictor are running!")
    st.info("**How to start:**\n1. Run producer: `python src/producer.py`\n2. Run predictor in Jupyter terminal: `python realtime_predictor.py`")
    time.sleep(refresh_sec)
    st.rerun()
else:
    # Process timestamps
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Process predictions
    if "predicted_label" not in df.columns and "prediction" in df.columns:
        df["predicted_label"] = df["prediction"].apply(lambda x: "Benign" if x == 0.0 else "Malicious")

    # Calculate metrics
    total_records = len(df)
    malicious_count = (df["predicted_label"] == "Malicious").sum()
    benign_count = (df["predicted_label"] == "Benign").sum()
    malicious_rate = (malicious_count / total_records * 100) if total_records > 0 else 0

    # Calculate throughput (predictions in last minute)
    if "timestamp" in df.columns:
        recent_time = datetime.now() - timedelta(minutes=1)
        recent_records = df[df["timestamp"] > recent_time]
        throughput = len(recent_records)
    else:
        throughput = 0

    # Metrics Row
    st.markdown("### 📊 Real-Time Metrics")
    metric_cols = st.columns(5)

    with metric_cols[0]:
        st.metric(
            label="Total Predictions",
            value=f"{total_records:,}",
            delta=f"+{throughput}/min"
        )

    with metric_cols[1]:
        st.metric(
            label="🔴 Malicious",
            value=f"{malicious_count:,}",
            delta=f"{malicious_rate:.1f}%"
        )

    with metric_cols[2]:
        st.metric(
            label="✅ Benign",
            value=f"{benign_count:,}",
            delta=f"{100-malicious_rate:.1f}%"
        )

    with metric_cols[3]:
        st.metric(
            label="⚡ Throughput",
            value=f"{throughput}",
            delta="predictions/min"
        )

    with metric_cols[4]:
        st.metric(
            label="🎯 Detection Rate",
            value=f"{malicious_rate:.1f}%",
            delta="malicious traffic"
        )

    st.markdown("---")

    # Charts Row
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📈 Predictions Over Time")
        if "timestamp" in df.columns:
            # Resample by minute
            time_series = df.set_index("timestamp").resample("1T").size().reset_index(name="count")

            fig_time = go.Figure()
            fig_time.add_trace(go.Scatter(
                x=time_series["timestamp"],
                y=time_series["count"],
                mode='lines',
                name='Predictions',
                line=dict(color='#00d4ff', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 212, 255, 0.1)'
            ))

            fig_time.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                hovermode='x unified'
            )

            st.plotly_chart(fig_time, use_container_width=True)

    with chart_col2:
        st.markdown("### 🎯 Threat Distribution")

        counts = df["predicted_label"].value_counts().reset_index()
        counts.columns = ["label", "count"]

        fig_pie = go.Figure(data=[go.Pie(
            labels=counts["label"],
            values=counts["count"],
            hole=0.4,
            marker=dict(colors=['#00cc66', '#ff4b4b']),
            textinfo='label+percent',
            textfont=dict(size=14)
        )])

        fig_pie.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # Live Predictions Table
    if show_table:
        st.markdown(f"### 📋 Latest {show_last_n} Predictions (Live Feed)")

        # Get latest N predictions
        latest_df = df.head(show_last_n).copy()

        # Prepare display columns
        display_cols = []
        if "timestamp" in latest_df.columns:
            latest_df["Time"] = latest_df["timestamp"].dt.strftime("%H:%M:%S")
            display_cols.append("Time")

        if "id_orig_h" in latest_df.columns:
            latest_df["Source IP"] = latest_df["id_orig_h"]
            display_cols.append("Source IP")

        if "id_resp_h" in latest_df.columns:
            latest_df["Dest IP"] = latest_df["id_resp_h"]
            display_cols.append("Dest IP")

        if "proto" in latest_df.columns:
            latest_df["Protocol"] = latest_df["proto"]
            display_cols.append("Protocol")

        if "predicted_label" in latest_df.columns:
            latest_df["Prediction"] = latest_df["predicted_label"]
            display_cols.append("Prediction")

        if "probability" in latest_df.columns:
            # Extract confidence from probability array
            latest_df["Confidence"] = latest_df["probability"].apply(
                lambda x: f"{max(x)*100:.1f}%" if isinstance(x, list) else "N/A"
            )
            display_cols.append("Confidence")

        # Color-code the dataframe
        def highlight_prediction(row):
            if "Prediction" in row.index:
                if row["Prediction"] == "Malicious":
                    return ['background-color: rgba(255, 75, 75, 0.2)'] * len(row)
                else:
                    return ['background-color: rgba(0, 204, 102, 0.2)'] * len(row)
            return [''] * len(row)

        if display_cols:
            styled_df = latest_df[display_cols].style.apply(highlight_prediction, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)

    # Status bar
    st.markdown("---")
    status_col1, status_col2 = st.columns([3, 1])
    with status_col1:
        st.caption(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with status_col2:
        st.caption(f"🔄 Auto-refresh in {refresh_sec}s")

    # Auto-refresh
    time.sleep(refresh_sec)
    st.rerun()
