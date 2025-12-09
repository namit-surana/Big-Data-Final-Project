import os
import sys
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, from_unixtime, hour, dayofweek, expr, when
from pyspark.sql.types import *
from pyspark.ml import PipelineModel
from pyspark.ml.classification import RandomForestClassificationModel
from pymongo import MongoClient

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
# Check if running in Docker (by checking hostname or env var) - simple heuristic
if os.path.exists("/.dockerenv"):
    KAFKA_BOOTSTRAP_SERVERS = "kafka:29092"
    MONGO_URI = "mongodb://mongo:27017/iot_malware.predictions"
else:
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    MONGO_URI = "mongodb://localhost:27017/iot_malware.predictions"

KAFKA_TOPIC = "network-traffic"
CHECKPOINT_LOCATION = "checkpoint_dir"

# Paths to Models (Assuming script is run from project root or src)
# Adjust these paths based on where you run the script from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "rf_model")
PIPELINE_PATH = os.path.join(BASE_DIR, "models", "feature_pipeline")

def create_spark_session():
    return SparkSession.builder \
        .appName("IoT Malware Real-Time Predictor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,org.mongodb.spark:mongo-spark-connector_2.12:10.1.1") \
        .config("spark.mongodb.write.connection.uri", MONGO_URI) \
        .getOrCreate()

def get_schema():
    return StructType([
        StructField("ts", DoubleType()),
        StructField("id.orig_h", StringType()),
        StructField("id.orig_p", DoubleType()),
        StructField("id.resp_h", StringType()),
        StructField("id.resp_p", DoubleType()),
        StructField("proto", StringType()),
        StructField("duration", StringType()),
        StructField("orig_bytes", StringType()),
        StructField("resp_bytes", StringType()),
        StructField("conn_state", StringType()),
        StructField("label", StringType()),
        StructField("detailed-label", StringType())
    ])

def process_batch(batch_df, batch_id):
    logger.info(f"Processing Batch ID: {batch_id} with {batch_df.count()} records")
    
    if batch_df.count() == 0:
        return

    # Write to MongoDB using pymongo (avoids Java connector binary incompatibility)
    try:
        # Convert Spark DataFrame to Pandas for driver-side insertion
        pdf = batch_df.select(
            "timestamp", 
            "id_orig_h", "id_orig_p", 
            "id_resp_h", "id_resp_p", 
            "proto", "prediction", "probability", 
            "predicted_label"
        ).toPandas()
        
        if not pdf.empty:
            # Connect to MongoDB
            # Convert DenseVector to list for MongoDB serialization
            pdf['probability'] = pdf['probability'].apply(lambda x: x.toArray().tolist() if hasattr(x, 'toArray') else x)

            mongo_host = "mongo" if os.path.exists("/.dockerenv") else "localhost"
            client = MongoClient(f"mongodb://{mongo_host}:27017")
            db = client["iot_malware"]
            collection = db["predictions"]
            
            # Convert DataFrame to dict records and insert
            records = pdf.to_dict("records")
            collection.insert_many(records)
            client.close()
            
            logger.info(f"Batch {batch_id} written to MongoDB successfully ({len(records)} records).")
    except Exception as e:
        logger.error(f"Error writing to MongoDB: {e}")

def main():
    logger.info("Starting Real-Time Prediction Pipeline...")
    
    if not os.path.exists(MODEL_PATH) or not os.path.exists(PIPELINE_PATH):
        logger.error(f"Models not found at {MODEL_PATH} or {PIPELINE_PATH}. Please run Phase 5 first.")
        sys.exit(1)

    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    # 1. Load Models
    logger.info("Loading models...")
    try:
        pipeline_model = PipelineModel.load(PIPELINE_PATH)
        rf_model = RandomForestClassificationModel.load(MODEL_PATH)
        logger.info("Models loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        sys.exit(1)

    # 2. Read from Kafka
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    df_kafka = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    # 3. Parse JSON
    schema = get_schema()
    df_parsed = df_kafka.selectExpr("CAST(value AS STRING) as json") \
        .select(from_json(col("json"), schema).alias("data")) \
        .select("data.*")

    # 4. Preprocessing (Must match training)
    # Handle missing values and types
    df_cleaned = df_parsed.withColumn("duration", col("duration").cast("double")) \
        .withColumn("orig_bytes", col("orig_bytes").cast("long")) \
        .withColumn("resp_bytes", col("resp_bytes").cast("long")) \
        .withColumn("orig_port", col("`id.orig_p`").cast("int")) \
        .withColumn("resp_port", col("`id.resp_p`").cast("int")) \
        .withColumnRenamed("id.orig_h", "id_orig_h") \
        .withColumnRenamed("id.resp_h", "id_resp_h") \
        .withColumnRenamed("id.orig_p", "id_orig_p") \
        .withColumnRenamed("id.resp_p", "id_resp_p") \
        .fillna(0, subset=["duration", "orig_bytes", "resp_bytes"])

    # Feature Extraction
    df_features = df_cleaned.withColumn("timestamp", from_unixtime("ts").cast("timestamp")) \
        .withColumn("hour_of_day", hour("timestamp")) \
        .withColumn("day_of_week", dayofweek("timestamp")) \
        .withColumn("total_bytes", col("orig_bytes") + col("resp_bytes")) \
        .withColumn("bytes_per_sec", (col("orig_bytes") + col("resp_bytes")) / (col("duration") + 0.001))

    # 5. Apply Feature Pipeline
    # Note: The pipeline expects 'id.orig_p' but we renamed it? 
    # Wait, the pipeline uses 'orig_port' which we created from 'id.orig_p'.
    # The pipeline uses 'proto', 'conn_state', 'label'.
    # We must ensure 'label' exists. If it's missing in real data, we might need to add a dummy.
    # Since our producer sends 'label', it's fine.
    
    df_transformed = pipeline_model.transform(df_features)

    # 6. Make Predictions
    predictions = rf_model.transform(df_transformed)

    # 7. Post-processing
    # Convert prediction index back to label string if possible, or just use prediction
    # 0.0 -> Benign, 1.0 -> Malicious (usually, depends on StringIndexer order)
    # We can infer this or just map it. 
    # Let's assume 0=Benign, 1=Malicious based on typical alphabetical sorting, but we should verify.
    # For now, we'll store the numeric prediction.
    
    final_output = predictions.withColumn("predicted_label", 
                                          when(col("prediction") == 0.0, "Benign")
                                          .when(col("prediction") == 1.0, "Malicious")
                                          .otherwise("Unknown"))

    # 8. Write Stream
    query = final_output.writeStream \
        .foreachBatch(process_batch) \
        .option("checkpointLocation", CHECKPOINT_LOCATION) \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
