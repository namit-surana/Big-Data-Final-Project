# Real-Time IoT Malware Detection Pipeline
## NYU Big Data Final Project

---

## Project Overview
This project implements a real-time streaming pipeline for detecting malware in IoT network traffic using Apache Kafka, Apache Spark, and machine learning techniques.

**Dataset**: CTU-IoT-Malware-Capture datasets (12 files, 3.2GB total)
- Network connection logs from IoT devices
- Labeled with attack types (Malicious/Benign)
- Features: IPs, ports, protocols, bytes transferred, connection states, etc.

---

## Project Structure

```
/project-root
  ├── data/                  # Kaggle datasets (NOT in Git - 3.2GB)
  │   ├── CTU-IoT-Malware-Capture-1-1conn.log.labeled.csv (133MB)
  │   ├── CTU-IoT-Malware-Capture-3-1conn.log.labeled.csv (23MB) ← Currently using
  │   ├── CTU-IoT-Malware-Capture-35-1conn.log.labeled.csv (1.3GB)
  │   └── ... 9 more files
  ├── notebooks/             # Jupyter notebooks for analysis
  ├── src/                   # Python scripts
  │   ├── producer.py        # Kafka producer (streams data)
  │   └── requirements.txt   # Python dependencies
  ├── .gitignore             # Ignores /data and local files
  ├── docker-compose.yaml    # Infrastructure definition
  └── README.md              # This file
```

---

## Infrastructure Components

All services are running in Docker containers:

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **Zookeeper** | 2181 | ✅ Running | Kafka coordination |
| **Kafka** | 9092 | ✅ Running | Message broker for streaming |
| **Spark Master** | 8080, 7077 | ✅ Running | Distributed processing brain |
| **Spark Worker** | 8081 | ✅ Running | Processing worker node |
| **Jupyter Lab** | 8888 | ✅ Running | Interactive analysis environment |
| **MongoDB** | 27017 | ✅ Running | Results storage |

### Access Points:
- **Jupyter Lab**: http://localhost:8888 (password: `nyucs`)
- **Spark Master UI**: http://localhost:8080
- **Spark Worker UI**: http://localhost:8081

---

## ✅ What Has Been Completed

### Phase 1: Infrastructure Setup ✅
- [x] Created project directory structure
- [x] Set up Docker Compose with all required services
- [x] Fixed Kafka/Zookeeper image compatibility issues
- [x] All 6 containers running successfully
- [x] Verified network connectivity between services

### Phase 2: Data Streaming Pipeline ✅
- [x] Created Python producer script ([src/producer.py](src/producer.py))
- [x] Installed dependencies (kafka-python, pandas, openpyxl)
- [x] Configured producer for pipe-delimited CSV files
- [x] Successfully streamed **156,103 records** to Kafka
- [x] Verified data reception in Kafka (287K+ messages total)
- [x] Kafka topic `network-traffic` created and populated

### Data Quality Verification ✅
- [x] Confirmed JSON serialization working
- [x] All 23 columns present in streamed data
- [x] Labels preserved (Malicious/Benign)
- [x] Detailed attack type labels intact
- [x] Added simulated timestamp for real-time processing

---

## 🔄 What Is Still Remaining

### Phase 3: Spark Streaming Consumer
**Status**: Not Started

**Tasks**:
- [ ] Create Spark Structured Streaming consumer
- [ ] Connect Spark to Kafka topic `network-traffic`
- [ ] Parse JSON messages in Spark
- [ ] Implement real-time data transformations
- [ ] Handle data cleaning and feature engineering

**Files to Create**:
- `src/spark_consumer.py` - Main Spark streaming application
- `notebooks/01_spark_streaming_setup.ipynb` - Interactive development

### Phase 4: Feature Engineering
**Status**: Not Started

**Tasks**:
- [ ] Analyze dataset features (23 columns)
- [ ] Handle missing values (duration, bytes can be "-")
- [ ] Convert categorical features (proto, conn_state, etc.)
- [ ] Create time-based features from timestamps
- [ ] Normalize numerical features
- [ ] Feature selection for ML model

**Files to Create**:
- `notebooks/02_exploratory_analysis.ipynb` - EDA
- `notebooks/03_feature_engineering.ipynb` - Feature processing

### Phase 5: Machine Learning Model
**Status**: Not Started

**Tasks**:
- [ ] Train initial model on historical data
- [ ] Experiment with algorithms:
  - [ ] Random Forest
  - [ ] Gradient Boosting
  - [ ] Neural Networks
- [ ] Evaluate model performance (accuracy, F1-score, etc.)
- [ ] Handle class imbalance (if present)
- [ ] Save trained model for streaming

**Files to Create**:
- `notebooks/04_model_training.ipynb` - Model development
- `models/` - Directory for saved models

### Phase 6: Real-Time Prediction Pipeline
**Status**: Not Started

**Tasks**:
- [ ] Load trained model in Spark streaming
- [ ] Apply model to incoming data in real-time
- [ ] Generate predictions (Malicious/Benign)
- [ ] Calculate confidence scores
- [ ] Store predictions in MongoDB

**Files to Create**:
- `src/realtime_predictor.py` - Production streaming app

### Phase 7: Results Storage & Visualization
**Status**: Not Started

**Tasks**:
- [ ] Connect Spark to MongoDB
- [ ] Store predictions with metadata
- [ ] Create dashboard for monitoring:
  - [ ] Attack type distribution
  - [ ] Real-time alerts
  - [ ] Model performance metrics
- [ ] Export results for reporting

**Files to Create**:
- `notebooks/05_results_visualization.ipynb` - Dashboard
- `notebooks/06_final_report.ipynb` - Project summary

### Phase 8: Testing & Optimization
**Status**: Not Started

**Tasks**:
- [ ] Test with larger datasets (1.3GB file)
- [ ] Optimize Spark configuration
- [ ] Tune batch intervals for latency
- [ ] Benchmark throughput
- [ ] Handle backpressure and failures

---

## Quick Start Guide

### 1. Start the Infrastructure
```bash
docker-compose up -d
```

### 2. Verify All Containers Running
```bash
docker ps
```
You should see 6 containers with status "Up".

### 3. Run the Producer
```bash
python -u src/producer.py
```

This will stream data from `CTU-IoT-Malware-Capture-3` (23MB) to Kafka.

**To use a different dataset**, edit [src/producer.py](src/producer.py) line 10:
```python
DATA_FILE = "data/CTU-IoT-Malware-Capture-35-1conn.log.labeled.csv"  # Use larger dataset
```

### 4. Monitor Kafka Messages
```bash
docker exec finalproject-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic network-traffic \
  --max-messages 10
```

### 5. Access Jupyter Lab
1. Open http://localhost:8888
2. Enter password: `nyucs`
3. Navigate to `/work` to see your notebooks folder
4. Access data at `/data` (mounted from local)

---

## Data Schema

Each message in Kafka has the following structure:

```json
{
  "ts": 1526756261.8665,                    // Original timestamp
  "uid": "C9YvmJ3zxtuqxWxLW5",              // Unique connection ID
  "id.orig_h": "192.168.2.5",               // Source IP
  "id.orig_p": 38792.0,                     // Source port
  "id.resp_h": "200.168.87.203",            // Destination IP
  "id.resp_p": 59353.0,                     // Destination port
  "proto": "tcp",                           // Protocol
  "service": "-",                           // Service detected
  "duration": "2.998333",                   // Connection duration
  "orig_bytes": "0",                        // Bytes sent
  "resp_bytes": "0",                        // Bytes received
  "conn_state": "S0",                       // Connection state
  "history": "S",                           // Connection history flags
  "orig_pkts": 3.0,                         // Packets sent
  "orig_ip_bytes": 180.0,                   // IP bytes sent
  "resp_pkts": 0.0,                         // Packets received
  "resp_ip_bytes": 0.0,                     // IP bytes received
  "label": "Malicious",                     // ← TARGET LABEL
  "detailed-label": "PartOfAHorizontalPortScan",  // Attack type
  "timestamp_simulated": 1764778995.52718   // Simulated streaming time
}
```

**Key Features for ML**:
- Network metrics: bytes, packets, duration
- Connection patterns: state, history
- Protocol information
- **Target**: `label` (binary classification)

---

## Technologies Used

- **Apache Kafka**: Real-time message streaming
- **Apache Spark**: Distributed stream processing
- **PySpark**: Python API for Spark
- **Pandas**: Data manipulation
- **Scikit-learn**: Machine learning (planned)
- **Docker**: Container orchestration
- **Jupyter**: Interactive development
- **MongoDB**: Results storage

---

## Project Timeline

| Phase | Status | Estimated Time |
|-------|--------|----------------|
| Infrastructure Setup | ✅ Complete | - |
| Data Streaming | ✅ Complete | - |
| Spark Consumer | 🔄 Next | 2-3 hours |
| Feature Engineering | ⏳ Pending | 3-4 hours |
| Model Training | ⏳ Pending | 4-6 hours |
| Real-Time Prediction | ⏳ Pending | 3-4 hours |
| Visualization | ⏳ Pending | 2-3 hours |
| Testing & Optimization | ⏳ Pending | 2-3 hours |

---

## Troubleshooting

### Kafka Connection Issues
```bash
# Check Kafka logs
docker logs finalproject-kafka-1 --tail 50

# Restart Kafka
docker-compose restart kafka
```

### Producer Not Sending Data
```bash
# Run with verbose output
python -u src/producer.py

# Check if data file exists
ls -lh data/
```

### Container Issues
```bash
# Stop all containers
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Port Already in Use
```bash
# Find what's using port 9092
netstat -ano | findstr :9092

# Kill the process or change ports in docker-compose.yaml
```

---

## Next Steps

1. **Immediate**: Create Spark streaming consumer in Jupyter
2. **Short-term**: Feature engineering and EDA
3. **Mid-term**: Train ML model on historical data
4. **Long-term**: Deploy real-time prediction pipeline

---

## Dataset Information

**Source**: CTU-IoT-Malware-Capture
- 12 capture files containing network traffic from IoT malware
- Pipe-delimited CSV format
- Pre-labeled with attack types
- Total size: 3.2GB

**Attack Types Found**:
- PartOfAHorizontalPortScan
- C&C (Command & Control)
- DDoS attacks
- Normal/Benign traffic

---

## Contributors

**Student**: Namit
**Course**: NYU Big Data
**Project**: Real-Time IoT Malware Detection

---

## License

This is an academic project for NYU coursework.

---

## Appendix: Useful Commands

### Docker Management
```bash
# View all containers
docker ps -a

# View container logs
docker logs <container_name>

# Stop all services
docker-compose down

# Remove all volumes (WARNING: deletes data)
docker-compose down -v
```

### Kafka Commands
```bash
# List topics
docker exec finalproject-kafka-1 kafka-topics --list --bootstrap-server localhost:9092

# Describe topic
docker exec finalproject-kafka-1 kafka-topics --describe --topic network-traffic --bootstrap-server localhost:9092

# Check message count
docker exec finalproject-kafka-1 kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 --topic network-traffic --time -1

# Consume from beginning
docker exec finalproject-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic network-traffic \
  --from-beginning
```

### Python Environment
```bash
# Install dependencies
pip install -r src/requirements.txt

# Check installed packages
pip list | grep -E "kafka|pandas|pyspark"
```

---

**Last Updated**: December 3, 2025
**Status**: Infrastructure Complete, Ready for Analysis Phase
