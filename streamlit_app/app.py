import time
import os
import pandas as pd
from pymongo import MongoClient
import streamlit as st
import plotly.express as px

def get_client():
    uri = "mongodb://mongo:27017" if os.path.exists("/.dockerenv") else "mongodb://localhost:27017"
    return MongoClient(uri)

st.set_page_config(layout="wide", page_title="IoT Malware Dashboard")
st.title("IoT Malware - Live Dashboard")

# UI controls
limit = st.sidebar.slider("Max records to fetch", 1000, 20000, 8000, step=1000)
refresh_sec = st.sidebar.slider("Refresh (sec)", 1, 10, 2)

# Auto-refresh trigger
st_autorefresh = st.experimental_rerun if refresh_sec == 0 else None
st.query_params.update({"refresh": str(time.time())})

client = get_client()
col = client["iot_malware"]["predictions"]

status = st.empty()
chart_area = st.container()

cursor = col.find({}, sort=[("processing_time", -1)], limit=limit)
df = pd.DataFrame(list(cursor))

if df.empty:
    status.info("No data yet")
else:
    # normalize time
    if "processing_time" in df.columns:
        df["processing_time"] = pd.to_datetime(df["processing_time"])
    elif "timestamp" in df.columns:
        df["processing_time"] = pd.to_datetime(df["timestamp"])

    # prediction label
    if "predicted_label" not in df.columns and "prediction" in df.columns:
        df["predicted_label"] = df["prediction"].apply(lambda x: "Benign" if x == 0.0 else "Malicious")

    # counts
    counts = df["predicted_label"].value_counts().reset_index()
    counts.columns = ["label", "count"]

    with chart_area:
        c1, c2 = st.columns([2,3])
        c1.metric("Total records", len(df))

        # timeline chart
        per_min = df.set_index("processing_time").resample("1T").size().rename("count").reset_index()
        c2.line_chart(
            per_min.rename(columns={"processing_time":"index"})
                  .set_index("index")["count"],
            use_container_width=True
        )

        # No need for a key now
        st.plotly_chart(
            px.bar(counts, x="label", y="count", color="label"),
            use_container_width=True
        )

status.text(f"Last update: {pd.Timestamp.now().isoformat()}")
time.sleep(refresh_sec)