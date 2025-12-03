import time
import pandas as pd
import json
from kafka import KafkaProducer
import os

# --- CONFIGURATION ---
KAFKA_TOPIC = "network-traffic"
KAFKA_SERVER = "localhost:9092"
DATA_FILE = "data/CTU-IoT-Malware-Capture-3-1conn.log.labeled.csv"  # 23MB - good for testing
# Other options:
# "data/CTU-IoT-Malware-Capture-1-1conn.log.labeled.csv"  # 133MB
# "data/CTU-IoT-Malware-Capture-35-1conn.log.labeled.csv"  # 1.3GB - largest

# --- INITIALIZE KAFKA PRODUCER ---
print(f"Connecting to Kafka at {KAFKA_SERVER}...")
try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_SERVER],
        value_serializer=lambda x: json.dumps(x).encode('utf-8')  # Turn data into JSON bytes
    )
    print("Connected to Kafka!")
except Exception as e:
    print(f"Error connecting to Kafka: {e}")
    exit(1)

# --- READ DATA ---
print(f"Reading data from {DATA_FILE}...")
# Tip: If the file is huge, we read it in chunks to save RAM
# For 755MB, we can try reading it directly or use chunks if it's slow.
try:
    # These files are pipe-delimited (|) not comma-delimited
    df = pd.read_csv(DATA_FILE, sep='|')
    print(f"Data loaded! Found {len(df)} records.")
    print(f"Columns: {', '.join(df.columns[:5])}... (showing first 5)")
except Exception as e:
    print(f"Error reading file: {e}")
    exit(1)

# --- START STREAMING ---
print("Starting stream... Press Ctrl+C to stop.")

try:
    for index, row in df.iterrows():
        # 1. Convert row to dictionary
        record = row.to_dict()

        # 2. Add a 'live' timestamp (Simulating that this is happening NOW)
        record['timestamp_simulated'] = time.time()

        # 3. Send to Kafka
        producer.send(KAFKA_TOPIC, value=record)

        # 4. Print status every 1000 records so console isn't spammed
        if index % 1000 == 0:
            print(f"Sent {index} records...")

        # 5. Sleep to simulate real-time (Optional)
        # If you want it fast, comment this out.
        # If you want to watch it, keep it small (e.g., 0.01 seconds)
        # time.sleep(0.001)

    producer.flush()
    print("Finished streaming all data.")

except KeyboardInterrupt:
    print("Streaming stopped by user.")
