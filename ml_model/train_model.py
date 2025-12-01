import pandas as pd
import os
import joblib
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import sys

# Add project root to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db import get_db_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def fetch_data():
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
        return df
    except Exception as e:
        logging.error("Failed to fetch data from database: %s", str(e))
        return pd.DataFrame()

def label_behavior(row):
    if row["avg_speed_kmph"] >= 80 and row["max_rpm"] < 4000:
        return "Safe"
    elif row["avg_speed_kmph"] >= 60:
        return "Moderate"
    else:
        return "Aggressive"

def train_model():
    df = fetch_data()
    if df.empty:
        logging.warning("No data found to train the model.")
        return

    # Add behavior labels
    df["behavior"] = df.apply(label_behavior, axis=1)

    # Define feature set
    features = [
        "avg_speed_kmph",
        "max_speed",
        "max_rpm",
        "fuel_consumed",
        "brake_events",
        "steering_angle",
        "angular_velocity",
        "acceleration",
        "gear_position",
        "tire_pressure",
        "engine_load",
        "throttle_position",
        "brake_pressure",
        "trip_duration",
    ]

    # Filter usable data
    df = df.dropna(subset=features + ["behavior"])
    if df.empty:
        logging.error("Insufficient clean data to train model.")
        return

    X = df[features]
    y = df["behavior"]

    # Split the dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train Random Forest model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate model
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred)
    logging.info("Model Evaluation Report:\n%s", report)

    # Save model
    os.makedirs("ml_model", exist_ok=True)
    model_path = "ml_model/driving_model.pkl"
    joblib.dump(model, model_path)
    logging.info("Model trained and saved at: %s", model_path)

if __name__ == "__main__":
    train_model()
