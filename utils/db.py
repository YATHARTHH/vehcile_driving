import sqlite3
import os

# Ensure 'instance' folder exists
os.makedirs("instance", exist_ok=True)
DB_PATH = os.path.join("instance", "trips.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            vehicle_number TEXT NOT NULL UNIQUE,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create trips table with full schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trip_date TEXT,
        distance_km REAL,
        avg_speed_kmph REAL,
        max_speed REAL,
        max_rpm INTEGER,
        fuel_consumed REAL,
        brake_events INTEGER,
        steering_angle REAL,
        angular_velocity REAL,
        gps_path TEXT,
        distance REAL,
        avg_speed REAL,
        score TEXT,
        acceleration REAL,
        gear_position INTEGER,
        tire_pressure REAL,
        engine_load REAL,
        throttle_position REAL,
        brake_pressure REAL,
        trip_duration REAL,
        start_location TEXT,
        end_location TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # ------------------------------
    # NEW: Maintenance alerts table
    # ------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            trip_id INTEGER,
            alert_type TEXT,       -- e.g. 'tire_pressure', 'engine_load', etc
            severity TEXT,         -- info | warning | critical
            title TEXT,            -- alert panel title
            message TEXT,          -- alert panel description
            icon TEXT,             -- icon to show for alert
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT FALSE,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(trip_id) REFERENCES trips(id)
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized with alerts table.")

# -------------------------------------------------
# Insert trip data safely (unchanged)
# -------------------------------------------------
def add_trip(
    user_id, trip_date, distance_km, avg_speed_kmph, max_speed, max_rpm, fuel_consumed,
    brake_events, steering_angle, angular_velocity, gps_path, distance, avg_speed, score,
    acceleration, gear_position, tire_pressure, engine_load, throttle_position,
    brake_pressure, trip_duration, start_location, end_location
):
    """
    Inserts a new trip record into the trips table.
    Any field can be None if not available for the trip.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trips (
            user_id, trip_date, distance_km, avg_speed_kmph, max_speed, max_rpm, fuel_consumed,
            brake_events, steering_angle, angular_velocity, gps_path, distance, avg_speed, score,
            acceleration, gear_position, tire_pressure, engine_load, throttle_position,
            brake_pressure, trip_duration, start_location, end_location
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, trip_date, distance_km, avg_speed_kmph, max_speed, max_rpm, fuel_consumed,
        brake_events, steering_angle, angular_velocity, gps_path, distance, avg_speed, score,
        acceleration, gear_position, tire_pressure, engine_load, throttle_position,
        brake_pressure, trip_duration, start_location, end_location
    ))
    conn.commit()
    conn.close()

# -------------------------------------------------
# Insert an alert
# -------------------------------------------------
def add_alert(user_id, trip_id, alert_type, severity, title, message, icon):
    """
    Insert a new maintenance alert for a trip.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO alerts (
            user_id, trip_id, alert_type, severity, title, message, icon
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, trip_id, alert_type, severity, title, message, icon))
    conn.commit()
    conn.close()
