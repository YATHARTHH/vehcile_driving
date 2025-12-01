"""
process_datasets.py - Enhanced Version with Vehicle Number Standardization
-------------------------------------------------------------------------
Processes ALL CSV/Excel files in data/dataset1..dataset7.
- Standardizes columns (fuzzy/forgiving match!)
- Computes per-trip features
- Inserts rows into database with all 23 fields
- Logs kept & skipped files with reason
- NOW SUPPORTS: Multiple trips per file and multiple users!
- ENHANCED: Better error handling, validation, and logging
- NEW: Vehicle number standardization utility for consistent formatting

How to run (from project root):
    python -m utils.process_datasets
"""

import os
import pandas as pd
import datetime
import random
import numpy as np
import logging
import hashlib
import re
from typing import List, Tuple, Dict, Optional, Any
from utils import db  # Assuming 'db' module exists and has 'add_trip'

# Configure logging with UTF-8 encoding support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_processing.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set console output encoding for Windows
import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# ✨ VEHICLE NUMBER STANDARDIZATION UTILITY
def standardize_vehicle_number(vehicle_number):
    """
    Formats a vehicle number: UPPERCASE, blocks with dashes (no extra chars).
    Ex: 'mp09 ab1234' -> 'MP09-AB1234'
    """
    if not vehicle_number:
        return ''
    clean = re.sub(r'[^A-Za-z0-9 -]', '', vehicle_number)
    parts = [blk for blk in re.split(r'[\s\-]+', clean.upper()) if blk]
    return '-'.join(parts)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_FOLDERS = [
    os.path.join(PROJECT_ROOT, 'data', f'dataset{i}') 
    for i in range(1, 8)
]

# Configuration constants
MIN_TRIP_DURATION_MINUTES = 2
MAX_TRIP_DURATION_MINUTES = 1440  # 24 hours (increased for long trips)
MIN_TRIP_DISTANCE_KM = 0.5
MAX_TRIP_DISTANCE_KM = 2000  # Increased for long distance trips
TIMESTAMP_GAP_THRESHOLD_MINUTES = 30
ZERO_SPEED_THRESHOLD_POINTS = 50

# Master column mapping with comprehensive variants
COLUMN_MAPPING = {
    'speed': [
        'Speed (km/h)', 'Vehicle Speed Sensor [km/h]', 'VEHICLE_SPEED', 'VEHICLE_SPEED ()', 'SPEED', 'speed', 'gps_speed',
        'Speed (GPS)(km/h)', 'Speed (OBD)(km/h)', 'Average trip speed(whilst moving only)(km/h)',
        'Average trip speed(whilst stopped or moving)(km/h)', 'velocity', 'car_speed'
    ],
    'rpm': [
        'Engine RPM [RPM]', 'ENGINE_RPM', 'ENGINE_RPM ()', 'ENGINE RPM(rpm)', 'rpm', 'Motor speed (rpm)',
        'engine_rpm', 'motor_rpm', 'revolutions_per_minute'
    ],
    'acceleration': [
        'Acceleration (m/s²)', 'Acceleration Sensor(Total)(g)', 'accData', 'acceleration',
        'accel', 'longitudinal_acceleration', 'acc_x', 'acc_y', 'acc_z'
    ],
    'brake': [
        'Braking intensity (%)', 'Braking intensity ()', 'Regen braking level (%)', 'Regen braking state',
        'brake_position', 'brake_pedal', 'braking_force'
    ],
    'throttle': [
        'Throttle position (%)', 'THROTTLE', 'THROTTLE ()', 'Absolute Throttle Position [%]',
        'Throttle Position(Manifold)(%)', 'Absolute Throttle Position B(%)', 'tPos', 'THROTTLE_POS',
        'throttle_position', 'accelerator_position', 'gas_pedal'
    ],
    'engine_load': [
        'ENGINE_LOAD', 'ENGINE_LOAD ()', 'Engine Load(Absolute)(%)', 'Engine Load(%)', 'eLoad',
        'calculated_engine_load', 'engine_load_percent'
    ],
    'coolant_temp': [
        'COOLANT_TEMPERATURE', 'COOLANT_TEMPERATURE ()', 'Engine Coolant Temperature [°C]', 'ENGINE_COOLANT_TEMP',
        'Engine Coolant Temperature(°C)', 'cTemp', 'coolant_temperature', 'engine_temp'
    ],
    'battery': [
        'Battery SoC (%)', 'Battery current (A)', 'battery', 'battery_voltage', 'soc', 'state_of_charge'
    ],
    'fuel_level': [
        'FUEL_LEVEL', 'FUEL_LEVEL ()', 'FUEL_TANK', 'Fuel Remaining (Calculated from vehicle profile)(%)',
        'fuel_tank_level', 'fuel_percentage'
    ],
    'trip_distance': [
        'Distance traveled (km)', 'Trip distance (km)', 'Trip Distance(km)', 'Trip Distance',
        'distance', 'odometer', 'total_distance'
    ],
    'trip_time': [
        'Trip time (min)', 'Trip Time(Since journey start)(s)', 'TIME', 'duration', 'elapsed_time'
    ],
    'latitude': [
        'LATITUDE', 'LATITUDE ()', 'GPS Latitude(°)', 'Latitude', 'lat', 'gps_lat'
    ],
    'longitude': [
        'LONGITUDE', 'LONGITUDE ()', 'GPS Longitude(°)', 'Longitude', 'lon', 'lng', 'gps_lon'
    ],
    'driver_rating': [
        'Driver Behavior rating', 'driving_score', 'safety_score', 'performance_rating'
    ],
    'user_id': [
        'User ID', 'user_id', 'driver_id', 'Driver ID', 'USER_ID', 'DRIVER_ID',
        'UserId', 'DriverId', 'User', 'Driver', 'user', 'driver'
    ],
    'trip_id': [
        'Trip ID', 'trip_id', 'TRIP_ID', 'TripId', 'Trip', 'trip', 'journey_id'
    ],
    'timestamp': [
        'Timestamp', 'timestamp', 'TIMESTAMP', 'Time', 'time', 'TIME',
        'DateTime', 'datetime', 'DATETIME', 'Date Time', 'date_time', 'recorded_at'
    ],
    'steering_angle': [
        'Steering Angle', 'steering_angle', 'wheel_angle', 'steering_position'
    ],
    'angular_velocity': [
        'Angular Velocity', 'angular_velocity', 'yaw_rate', 'rotation_rate'
    ],
    'gear_position': [
        'Gear Position', 'gear_position', 'gear', 'transmission_gear'
    ],
    'tire_pressure': [
        'Tire Pressure', 'tire_pressure', 'wheel_pressure', 'tyre_pressure'
    ],
    'brake_pressure': [
        'Brake Pressure', 'brake_pressure', 'braking_pressure', 'brake_force'
    ],
    'vehicle_number': [
        'Vehicle Number', 'vehicle_number', 'VehicleNumber', 'VEHICLE_NUMBER',
        'License Plate', 'license_plate', 'LicensePlate', 'LICENSE_PLATE',
        'Registration Number', 'registration_number', 'RegNumber', 'reg_number',
        'Plate Number', 'plate_number', 'PlateNumber', 'PLATE_NUMBER',
        'Car Number', 'car_number', 'CarNumber', 'CAR_NUMBER'
    ]
}


def normalize(s: str) -> str:
    """Normalize string for fuzzy column matching."""
    return ''.join(e for e in s.lower() if e.isalnum())


def standardize_columns(df: pd.DataFrame, mapping: Dict[str, List[str]]) -> pd.DataFrame:
    """Standardize column names using fuzzy matching."""
    renamed = {}
    columns_norm = {normalize(col): col for col in df.columns}
    
    logger.debug(f"Original columns: {df.columns.tolist()}")
    
    for std_name, variants in mapping.items():
        for variant in variants:
            n = normalize(variant)
            if n in columns_norm:
                original_col_name = columns_norm[n]
                renamed[original_col_name] = std_name
                logger.debug(f"Mapped '{original_col_name}' to '{std_name}'")
                break
    
    return df.rename(columns=renamed)


def safe_series(df: pd.DataFrame, colname: str) -> Optional[pd.Series]:
    """Safely get a series from dataframe."""
    col = df.get(colname)
    if not isinstance(col, pd.Series) or col.empty:
        return None
    return col


def safe_numeric_operation(df: pd.DataFrame, colname: str, operation: str = 'last') -> Optional[float]:
    """Safely perform numeric operations on series."""
    col = safe_series(df, colname)
    if col is None:
        return None
    
    col_num = pd.to_numeric(col, errors='coerce')
    if col_num.isnull().all():
        return None
    
    if operation == 'last':
        return col_num.iloc[-1] if not col_num.empty else None
    elif operation == 'first':
        return col_num.iloc[0] if not col_num.empty else None
    elif operation == 'mean':
        return col_num.mean()
    elif operation == 'max':
        return col_num.max()
    elif operation == 'sum':
        return col_num.sum()
    else:
        return None


def extract_vehicle_number(df: pd.DataFrame, filename: str, user_id: int) -> str:
    """Extract or generate vehicle number from data or filename."""
    # Try to get from data first
    if 'vehicle_number' in df.columns:
        vehicle_series = safe_series(df, 'vehicle_number')
        if vehicle_series is not None:
            first_vehicle = vehicle_series.dropna()
            if not first_vehicle.empty:
                raw_vehicle_number = str(first_vehicle.iloc[0])
                standardized = standardize_vehicle_number(raw_vehicle_number)
                if standardized:
                    logger.info(f"Extracted vehicle_number from data: {standardized}")
                    return standardized

    # ✂️ Use stricter pattern to avoid junk like "IDLE28"
    # Only allow clean Indian vehicle numbers like MP09AB1234
    vehicle_patterns = [
        r'([A-Z]{2}\d{2}[A-Z]{2}\d{4})',  # Ex: MP09AB1234
    ]

    filename_clean = filename.replace('.csv', '').replace('.xlsx', '').replace('.xls', '')
    for pattern in vehicle_patterns:
        match = re.search(pattern, filename_clean, re.IGNORECASE)
        if match:
            raw_vehicle_number = match.group(1).strip()
            standardized = standardize_vehicle_number(raw_vehicle_number)
            if standardized and len(standardized) >= 4:
                logger.info(f"Extracted vehicle_number from filename: {standardized}")
                return standardized

    # 🚀 Fallback: Generate vehicle number using user_id
    state_codes = ['MP', 'MH', 'DL', 'KA', 'TN', 'UP', 'GJ', 'RJ', 'WB', 'AP']
    np.random.seed(user_id)

    state = random.choice(state_codes)
    district = f"{random.randint(1, 99):02d}"
    series = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    number = f"{random.randint(1000, 9999)}"

    generated_vehicle_number = f"{state}{district}-{series}{number}"
    logger.info(f"Generated vehicle_number: {generated_vehicle_number} (for user_id {user_id})")

    return generated_vehicle_number

def extract_user_id(df: pd.DataFrame, filename: str) -> int:
    """Extract or generate user ID from data or filename."""
    # Try to get from data first
    if 'user_id' in df.columns:
        user_series = safe_series(df, 'user_id')
        if user_series is not None:
            first_user = pd.to_numeric(user_series, errors='coerce').dropna()
            if not first_user.empty:
                return int(first_user.iloc[0])
    
    # Try to extract from filename patterns
    user_patterns = [
        r'user[_-]?(\d+)', r'driver[_-]?(\d+)', r'u(\d+)', r'd(\d+)'
    ]
    filename_lower = filename.lower()
    for pattern in user_patterns:
        match = re.search(pattern, filename_lower)
        if match:
            user_id = int(match.group(1))
            logger.info(f"Extracted user_id {user_id} from filename pattern")
            return user_id
    
    # Generate consistent user ID based on filename hash
    filename_hash = int(hashlib.md5(filename.encode()).hexdigest()[:8], 16)
    generated_user_id = (filename_hash % 1000) + 1
    logger.info(f"Generated user_id: {generated_user_id} (from filename hash)")
    
    return generated_user_id


from werkzeug.security import generate_password_hash
import re  # make sure this is imported

def ensure_user_exists(user_id: int, vehicle_number: str):
    """Checks if a user exists in the DB, if not, creates a dummy user with standardized vehicle number."""
    vehicle_number = standardize_vehicle_number(vehicle_number)

    conn = db.get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        # ✅ Generate username from vehicle_number like 'mpab1234'
        username = re.sub(r'[^A-Za-z0-9]', '', vehicle_number).lower()
        hashed_password = generate_password_hash('default_password')

        try:
            conn.execute(
                'INSERT INTO users (id, username, password, vehicle_number) VALUES (?, ?, ?, ?)',
                (user_id, username, hashed_password, vehicle_number)
            )
            conn.commit()
        except conn.IntegrityError:
            logging.warning(f"User {user_id} was created by another process concurrently.")
        except Exception as e:
            logging.error(f"Failed to create dummy user {user_id}: {e}")
    conn.close()

    """Checks if a user exists in the DB, if not, creates a dummy user with standardized vehicle number."""
    # ✨ ALWAYS STANDARDIZE VEHICLE NUMBER BEFORE DB OPERATIONS
    vehicle_number = standardize_vehicle_number(vehicle_number)
    
    conn = db.get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        # User does not exist, create a dummy entry
        logger.info(f"User with ID {user_id} not found. Creating a dummy user with vehicle: {vehicle_number}")
        try:
            hashed_password = hashlib.sha256('default_password'.encode()).hexdigest()
            conn.execute(
                'INSERT INTO users (id, username, password, vehicle_number) VALUES (?, ?, ?, ?)',
                (user_id, f'generated_user_{user_id}', hashed_password, vehicle_number)
            )
            conn.commit()
        except conn.IntegrityError:
            # Race condition: another process might have inserted it. Ignore.
            logger.warning(f"User {user_id} was created by another process concurrently.")
        except Exception as e:
            logger.error(f"Failed to create dummy user {user_id}: {e}")
    conn.close()


def generate_trip_id(filename: str, trip_index: int, user_id: int) -> int:
    """Generate unique trip ID."""
    unique_string = f"{filename}_{trip_index}_{user_id}"
    trip_hash = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
    return abs(trip_hash % 100000) + 1


def validate_trip_data(trip_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate trip data before database insertion."""
    errors = []
    
    # Check required fields
    required_fields = ['user_id', 'trip_date', 'distance_km', 'avg_speed_kmph', 'score']
    for field in required_fields:
        if field not in trip_data or trip_data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    # Validate numeric ranges with more lenient limits
    if 'distance_km' in trip_data and trip_data['distance_km'] is not None:
        if not (MIN_TRIP_DISTANCE_KM <= trip_data['distance_km'] <= MAX_TRIP_DISTANCE_KM):
            # Log warning but don't fail validation for reasonable distances
            if trip_data['distance_km'] > MAX_TRIP_DISTANCE_KM:
                logger.warning(f"Long trip detected: {trip_data['distance_km']:.1f} km")
                # Cap at maximum but allow processing
                trip_data['distance_km'] = MAX_TRIP_DISTANCE_KM
    
    if 'trip_duration' in trip_data and trip_data['trip_duration'] is not None:
        if not (MIN_TRIP_DURATION_MINUTES <= trip_data['trip_duration'] <= MAX_TRIP_DURATION_MINUTES):
            # Log warning but don't fail validation for reasonable durations
            if trip_data['trip_duration'] > MAX_TRIP_DURATION_MINUTES:
                logger.warning(f"Long trip duration detected: {trip_data['trip_duration']:.1f} minutes")
                # Cap at maximum but allow processing
                trip_data['trip_duration'] = MAX_TRIP_DURATION_MINUTES
            elif trip_data['trip_duration'] < MIN_TRIP_DURATION_MINUTES:
                errors.append(f"Trip too short: {trip_data['trip_duration']:.1f} minutes")
    
    if 'avg_speed_kmph' in trip_data and trip_data['avg_speed_kmph'] is not None:
        if not (0 <= trip_data['avg_speed_kmph'] <= 300):  # Increased max speed
            if trip_data['avg_speed_kmph'] > 300:
                logger.warning(f"High speed detected: {trip_data['avg_speed_kmph']:.1f} km/h")
                trip_data['avg_speed_kmph'] = min(trip_data['avg_speed_kmph'], 200)  # Cap at reasonable speed
            else:
                errors.append(f"Invalid average speed: {trip_data['avg_speed_kmph']:.1f} km/h")
    
    return len(errors) == 0, errors


def detect_trip_boundaries(df: pd.DataFrame) -> List[Tuple[int, int]]:
    """Detect trip boundaries using multiple heuristics."""
    if len(df) == 0:
        return []
    
    trip_boundaries = []
    current_start = 0
    
    # Method 1: Timestamp gaps
    if 'timestamp' in df.columns:
        timestamp_series = safe_series(df, 'timestamp')
        if timestamp_series is not None:
            try:
                timestamp_col = pd.to_datetime(timestamp_series, errors='coerce')
                if not timestamp_col.isnull().all():
                    time_diffs = timestamp_col.diff()
                    large_gaps = time_diffs > pd.Timedelta(minutes=TIMESTAMP_GAP_THRESHOLD_MINUTES)
                    gap_indices = large_gaps[large_gaps].index.tolist()
                    
                    for gap_idx in gap_indices:
                        if gap_idx > current_start:
                            trip_boundaries.append((current_start, gap_idx - 1))
                            current_start = gap_idx
                    
                    # Add final trip
                    if current_start < len(df) - 1:
                        trip_boundaries.append((current_start, len(df) - 1))
                    
                    if trip_boundaries:
                        logger.info(f"Detected {len(trip_boundaries)} trips using timestamp gaps")
                        return trip_boundaries
            except Exception as e:
                logger.warning(f"Failed to use timestamp method: {e}")
    
    # Method 2: Speed patterns (zero-speed periods)
    speed_col = safe_series(df, 'speed')
    if speed_col is not None:
        speed_num = pd.to_numeric(speed_col, errors='coerce').fillna(0)
        zero_speed = speed_num <= 1  # Consider very low speeds as stops
        
        # Find consecutive zero-speed periods
        speed_changes = zero_speed.astype(int).diff().fillna(0)
        zero_starts = speed_changes[speed_changes == 1].index.tolist()
        zero_ends = speed_changes[speed_changes == -1].index.tolist()
        
        # Ensure we have matching starts and ends
        if len(zero_starts) > len(zero_ends):
            zero_ends.append(len(df) - 1)
        
        for i, start in enumerate(zero_starts):
            if i < len(zero_ends):
                end = zero_ends[i]
                stop_duration = end - start
                if stop_duration > ZERO_SPEED_THRESHOLD_POINTS and start > current_start:
                    trip_boundaries.append((current_start, start - 1))
                    current_start = end + 1
        
        # Add final trip
        if current_start < len(df) - 1:
            trip_boundaries.append((current_start, len(df) - 1))
        
        if trip_boundaries:
            logger.info(f"Detected {len(trip_boundaries)} trips using speed patterns")
            return trip_boundaries
    
    # Method 3: Distance resets
    distance_col = safe_series(df, 'trip_distance')
    if distance_col is not None:
        distance_num = pd.to_numeric(distance_col, errors='coerce').fillna(0)
        distance_resets = distance_num.diff() < -1
        reset_indices = distance_resets[distance_resets].index.tolist()
        
        for reset_idx in reset_indices:
            if reset_idx > current_start:
                trip_boundaries.append((current_start, reset_idx - 1))
                current_start = reset_idx
        
        # Add final trip
        if current_start < len(df) - 1:
            trip_boundaries.append((current_start, len(df) - 1))
        
        if trip_boundaries:
            logger.info(f"Detected {len(trip_boundaries)} trips using distance resets")
            return trip_boundaries
    
    # Default: Treat entire file as one trip
    logger.info("No trip boundaries detected, treating entire file as one trip")
    return [(0, len(df) - 1)]


def generate_realistic_field(field_name: str, df_segment: pd.DataFrame, 
                           existing_data: Dict[str, Any] = None) -> Optional[pd.Series]:
    """Generate realistic missing field data."""
    if df_segment.empty:
        return None
    
    length = len(df_segment)
    seed_value = length + hash(str(df_segment.index[0]) + field_name)
    np.random.seed(seed_value % (2**32))
    random.seed(seed_value)
    
    if field_name == 'speed':
        # Generate realistic speed pattern
        base_speed = random.uniform(30, 80)
        speed_variation = np.random.normal(0, 15, length)
        speed_pattern = np.maximum(0, base_speed + speed_variation)
        # Add realistic acceleration/deceleration phases
        for i in range(1, length):
            max_change = 5  # Max speed change per sample
            change = np.clip(speed_pattern[i] - speed_pattern[i-1], -max_change, max_change)
            speed_pattern[i] = speed_pattern[i-1] + change
        return pd.Series(np.clip(speed_pattern, 0, 150), index=df_segment.index)
    
    elif field_name == 'rpm':
        # Generate RPM correlated with speed if available
        speed_col = safe_series(df_segment, 'speed')
        if speed_col is not None:
            speed_num = pd.to_numeric(speed_col, errors='coerce').fillna(30)
            # Realistic RPM calculation: base idle + speed factor + gear simulation
            base_rpm = 800  # Idle RPM
            speed_factor = speed_num * random.uniform(40, 60)  # Gear-dependent
            rpm_noise = np.random.normal(0, 200, length)
            rpm_pattern = base_rpm + speed_factor + rpm_noise
            return pd.Series(np.clip(rpm_pattern, 600, 7000), index=df_segment.index)
        else:
            # Generate standalone RPM pattern
            base_rpm = random.uniform(1500, 3000)
            rpm_variation = np.random.normal(0, 500, length)
            return pd.Series(np.clip(base_rpm + rpm_variation, 600, 7000), index=df_segment.index)
    
    elif field_name == 'throttle':
        # Generate throttle correlated with speed/acceleration
        speed_col = safe_series(df_segment, 'speed')
        if speed_col is not None:
            speed_num = pd.to_numeric(speed_col, errors='coerce').fillna(0)
            # Calculate throttle based on speed changes (acceleration)
            speed_changes = speed_num.diff().fillna(0)
            base_throttle = np.where(speed_changes > 0, 
                                   speed_changes * 5 + 20,  # Accelerating
                                   np.maximum(10, speed_num * 0.3))  # Cruising/coasting
            throttle_noise = np.random.normal(0, 10, length)
            return pd.Series(np.clip(base_throttle + throttle_noise, 0, 100), index=df_segment.index)
        else:
            # Generate realistic throttle pattern
            base_throttle = random.uniform(20, 60)
            throttle_variation = np.random.normal(0, 20, length)
            return pd.Series(np.clip(base_throttle + throttle_variation, 0, 100), index=df_segment.index)
    
    # Add more field generation logic as needed
    return None


def process_trip_segment(df_segment: pd.DataFrame, filename: str, 
                        user_id: int, trip_index: int, vehicle_number: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Process a single trip segment."""
    try:
        trip_id = generate_trip_id(filename, trip_index, user_id)
        logger.debug(f"Processing trip {trip_index + 1} with ID {trip_id}")
        
        # Generate missing required fields
        required_fields = ['speed', 'rpm', 'throttle']
        generated_fields = []
        
        for field in required_fields:
            if safe_series(df_segment, field) is None:
                logger.info(f"Generating missing '{field}' field...")
                generated_series = generate_realistic_field(field, df_segment)
                if generated_series is not None:
                    df_segment[field] = generated_series
                    generated_fields.append(field)
                else:
                    return None, f"Failed to generate required field: {field}"
        
        if generated_fields:
            logger.info(f"Generated fields: {', '.join(generated_fields)}")
        
        # Extract core metrics
        avg_speed = safe_numeric_operation(df_segment, 'speed', 'mean')
        max_speed = safe_numeric_operation(df_segment, 'speed', 'max')
        max_rpm = safe_numeric_operation(df_segment, 'rpm', 'max')
        throttle_mean = safe_numeric_operation(df_segment, 'throttle', 'mean')
        
        if any(x is None for x in [avg_speed, max_speed, max_rpm, throttle_mean]):
            return None, "Failed to extract core metrics after field generation"
        
        # Calculate brake events
        speed_col = safe_series(df_segment, 'speed')
        brake_events = 0
        if speed_col is not None:
            speed_num = pd.to_numeric(speed_col, errors='coerce').dropna()
            if not speed_num.empty:
                brake_events = (speed_num.diff() < -10).sum()
        
        # Generate or extract other fields with validation
        trip_distance = safe_numeric_operation(df_segment, 'trip_distance', 'last')
        if trip_distance is None or trip_distance <= 0:
            # Estimate based on average speed and data points
            estimated_hours = len(df_segment) / 3600  # Assume 1 second per row
            trip_distance = max(0.1, avg_speed * estimated_hours)
            logger.debug(f"Generated trip_distance: {trip_distance:.2f} km")
        
        trip_duration = safe_numeric_operation(df_segment, 'trip_time', 'last')
        if trip_duration is None or trip_duration <= 0:
            trip_duration = max(1, len(df_segment) / 60)  # Convert to minutes
            logger.debug(f"Generated trip_duration: {trip_duration:.2f} minutes")
        
        # Location data
        latitude = safe_numeric_operation(df_segment, 'latitude', 'first')
        longitude = safe_numeric_operation(df_segment, 'longitude', 'first')
        if latitude is None or longitude is None:
            # Generate realistic coordinates (India region)
            np.random.seed(user_id + trip_index)
            latitude = random.uniform(8.0, 37.0)
            longitude = random.uniform(68.0, 97.0)
            logger.debug(f"Generated coordinates: {latitude:.4f}, {longitude:.4f}")
        
        # Additional fields with realistic generation
        engine_load = safe_numeric_operation(df_segment, 'engine_load', 'mean')
        if engine_load is None:
            engine_load = max(0, min(100, throttle_mean * 0.8 + random.uniform(-10, 10)))
        
        coolant_temp = safe_numeric_operation(df_segment, 'coolant_temp', 'mean')
        if coolant_temp is None:
            base_temp = 85 + (engine_load * 0.2) if engine_load else 88
            coolant_temp = base_temp + random.uniform(-5, 8)
        
        fuel_consumed = None
        if 'fuel_level' in df_segment.columns:
            fuel_start = safe_numeric_operation(df_segment, 'fuel_level', 'first')
            fuel_end = safe_numeric_operation(df_segment, 'fuel_level', 'last')
            if fuel_start and fuel_end and fuel_start > fuel_end:
                fuel_consumed = fuel_start - fuel_end
        
        if fuel_consumed is None or fuel_consumed <= 0:
            # Realistic fuel consumption: 6-12L/100km depending on driving style
            base_consumption_rate = 0.08  # 8L/100km base
            if max_rpm > 4000 or brake_events > 5:
                base_consumption_rate = 0.12  # Aggressive driving
            elif max_rpm < 3000 and brake_events <= 2:
                base_consumption_rate = 0.06  # Efficient driving
            
            fuel_consumed = max(0.1, trip_distance * base_consumption_rate)
        
        # Driver score calculation
        score = 'Good'  # Default
        if 'driver_rating' in df_segment.columns:
            rating_series = safe_series(df_segment, 'driver_rating')
            if rating_series is not None and not rating_series.empty:
                score = rating_series.iloc[0]
        else:
            # Calculate score based on driving patterns
            risk_factors = 0
            if max_rpm > 5000:
                risk_factors += 2
            if brake_events > 5:
                risk_factors += 2
            if avg_speed > 80:
                risk_factors += 1
            if throttle_mean > 70:
                risk_factors += 1
            
            if risk_factors >= 3:
                score = 'Risky'
            elif risk_factors >= 1:
                score = 'Average'
            else:
                score = 'Good'
        
        # Generate additional fields as needed
        steering_angle = safe_numeric_operation(df_segment, 'steering_angle', 'mean') or random.uniform(-20, 20)
        angular_velocity = safe_numeric_operation(df_segment, 'angular_velocity', 'mean') or (steering_angle * 0.1)
        acceleration = safe_numeric_operation(df_segment, 'acceleration', 'mean')
        if acceleration is None and speed_col is not None:
            speed_num = pd.to_numeric(speed_col, errors='coerce')
            if not speed_num.empty and len(speed_num) > 1:
                acceleration = speed_num.diff().mean() / 3.6  # Convert to m/s²
            else:
                acceleration = random.uniform(-1, 1)
        
        gear_position = safe_numeric_operation(df_segment, 'gear_position', 'mean')
        if gear_position is None:
            if avg_speed < 25:
                gear_position = random.choice([1, 2])
            elif avg_speed < 50:
                gear_position = random.choice([2, 3, 4])
            else:
                gear_position = random.choice([4, 5, 6])
        
        tire_pressure = safe_numeric_operation(df_segment, 'tire_pressure', 'mean') or random.uniform(28, 36)
        brake_pressure = safe_numeric_operation(df_segment, 'brake_pressure', 'mean')
        if brake_pressure is None:
            brake_pressure = random.uniform(2, 15) if brake_events > 0 else random.uniform(0, 3)
        
        # Date handling
        trip_date = datetime.date.today()
        if 'timestamp' in df_segment.columns:
            timestamp_series = safe_series(df_segment, 'timestamp')
            if timestamp_series is not None:
                try:
                    first_timestamp = pd.to_datetime(timestamp_series.iloc[0], errors='coerce')
                    if not pd.isna(first_timestamp):
                        trip_date = first_timestamp.date()
                except:
                    pass
        
        # GPS and location data
        end_lat = safe_numeric_operation(df_segment, 'latitude', 'last') or (latitude + random.uniform(-0.01, 0.01))
        end_lon = safe_numeric_operation(df_segment, 'longitude', 'last') or (longitude + random.uniform(-0.01, 0.01))
        
        start_location = f"{latitude},{longitude}" if latitude and longitude else None
        end_location = f"{end_lat},{end_lon}" if end_lat and end_lon else None
        gps_path = f"[{latitude},{longitude}]" if latitude and longitude else None
        
        # Construct trip data
        trip_data = {
            'user_id': user_id,
            'trip_date': trip_date,
            'distance_km': round(trip_distance, 2),
            'avg_speed_kmph': round(avg_speed, 2),
            'max_speed': round(max_speed, 2),
            'max_rpm': round(max_rpm, 0),
            'fuel_consumed': round(fuel_consumed, 3),
            'brake_events': int(brake_events),
            'steering_angle': round(steering_angle, 2),
            'angular_velocity': round(angular_velocity, 3),
            'gps_path': gps_path,
            'distance': round(trip_distance, 2),
            'avg_speed': round(avg_speed, 2),
            'score': score,
            'acceleration': round(acceleration, 3) if acceleration else 0,
            'gear_position': int(gear_position) if gear_position else 3,
            'tire_pressure': round(tire_pressure, 1),
            'engine_load': round(engine_load, 1),
            'throttle_position': round(throttle_mean, 1),
            'brake_pressure': round(brake_pressure, 2),
            'trip_duration': round(trip_duration, 2),
            'start_location': start_location,
            'end_location': end_location,
            'vehicle_number': vehicle_number  # Add vehicle number to trip data
        }
        
        # ✨ STANDARDIZE VEHICLE NUMBER IN TRIP DATA BEFORE VALIDATION/DB INSERT
        if 'vehicle_number' in trip_data:
            trip_data['vehicle_number'] = standardize_vehicle_number(trip_data['vehicle_number'])
        
        # Validate trip data
        is_valid, validation_errors = validate_trip_data(trip_data)
        if not is_valid:
            return None, f"Validation failed: {'; '.join(validation_errors)}"
        
        return trip_data, None
        
    except Exception as e:
        logger.error(f"Error processing trip segment: {e}")
        return None, f"Processing error: {str(e)}"


def clean_column_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column data by removing units and special characters."""
    cleaning_rules = {
        'throttle': [('%', ''), (',', '.')],
        'speed': [('km/h', ''), ('mph', ''), (',', '.')],
        'rpm': [('RPM', ''), ('rpm', ''), (',', '.')],
        'engine_load': [('%', ''), (',', '.')],
        'fuel_level': [('%', ''), (',', '.')],
        'brake': [('%', ''), (',', '.')],
        'battery': [('%', ''), ('A', ''), (',', '.')],
        'vehicle_number': [('(', ''), (')', ''), ('[', ''), (']', ''), ('{', ''), ('}', '')]
    }

    for std_col_name, replacements in cleaning_rules.items():
        if std_col_name in df.columns:
            temp_series = df[std_col_name].astype(str)
            for old_char, new_char in replacements:
                temp_series = temp_series.str.replace(old_char, new_char, regex=False)
            temp_series = temp_series.str.strip()
            df[std_col_name] = temp_series

    return df


def process_file_with_error_handling(file_path: str, filename: str) -> Tuple[List[Tuple[str, int]], List[Tuple[str, str]]]:
    """Process a single file with comprehensive error handling."""
    processed_trips = []
    errors = []
    
    try:
        # Load file with encoding detection
        df = None
        encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings_to_try:
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(file_path, low_memory=False, encoding=encoding)
                else:
                    df = pd.read_excel(file_path)
                logger.info(f"Successfully loaded {filename} with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if encoding == encodings_to_try[-1]:  # Last encoding attempt
                    raise e
                continue
        
        if df is None:
            return [], [(filename, "Failed to load file with any encoding")]
        
        # Basic validation
        if df.empty:
            return [], [(filename, "File is empty")]
        
        if len(df.columns) < 3:
            return [], [(filename, f"Too few columns ({len(df.columns)}), expected at least 3")]
        
        logger.info(f"Loaded {filename}: {len(df)} rows, {len(df.columns)} columns")
        
        # Standardize columns
        df = standardize_columns(df, COLUMN_MAPPING)
        
        # Clean column data
        df = clean_column_data(df)
        
        # Extract user ID and vehicle number
        user_id = extract_user_id(df, filename)
        vehicle_number = extract_vehicle_number(df, filename, user_id)
        
        # ✨ STANDARDIZE VEHICLE NUMBER BEFORE USER CREATION
        vehicle_number = standardize_vehicle_number(vehicle_number)
        
        # Ensure user exists with standardized vehicle number
        ensure_user_exists(user_id, vehicle_number)
        
        # Detect trip boundaries
        trip_boundaries = detect_trip_boundaries(df)
        logger.info(f"Detected {len(trip_boundaries)} trip(s) in {filename}")
        
        # Process each trip segment
        for trip_index, (start_idx, end_idx) in enumerate(trip_boundaries):
            logger.info(f"Processing trip {trip_index + 1}/{len(trip_boundaries)} "
                       f"(rows {start_idx}-{end_idx}) in {filename}")
            
            # Extract and validate trip segment
            df_segment = df.iloc[start_idx:end_idx + 1].copy()
            
            if len(df_segment) < 5:  # Minimum trip length
                errors.append((f"{filename}_trip_{trip_index + 1}", 
                             f"Trip too short ({len(df_segment)} rows)"))
                continue
            
            # Process trip segment with vehicle number
            trip_data, error_msg = process_trip_segment(df_segment, filename, user_id, trip_index, vehicle_number)
            
            if trip_data is None:
                errors.append((f"{filename}_trip_{trip_index + 1}", error_msg))
                continue
            
            # Insert into database
            try:
                # ✨ SAVE VEHICLE NUMBER FOR LOGGING, THEN REMOVE FROM TRIP DATA
                # since db.add_trip() doesn't accept vehicle_number parameter
                vehicle_number_for_log = trip_data.get('vehicle_number', 'N/A')
                
                # Create a copy of trip_data without vehicle_number for database insertion
                db_trip_data = {k: v for k, v in trip_data.items() if k != 'vehicle_number'}
                
                db.add_trip(**db_trip_data)
                processed_trips.append((f"{filename}_trip_{trip_index + 1}", 1))
                logger.info(f"Successfully inserted trip {trip_index + 1} from {filename} "
                           f"(score: {trip_data['score']}, distance: {trip_data['distance_km']:.2f}km, "
                           f"vehicle: {vehicle_number_for_log})")
                
            except Exception as db_error:
                error_msg = f"Database insertion failed: {str(db_error)}"
                errors.append((f"{filename}_trip_{trip_index + 1}", error_msg))
                logger.error(f"DB error for {filename} trip {trip_index + 1}: {db_error}")
        
        return processed_trips, errors
        
    except Exception as e:
        logger.error(f"Fatal error processing {filename}: {e}")
        return [], [(filename, f"Fatal processing error: {str(e)}")]


def process_all_files():
    """Main processing function with enhanced logging and error handling."""
    logger.info("Starting dataset processing with vehicle number standardization...")
    
    processed_files = []
    skipped_files = []
    total_trips_processed = 0
    total_files_found = 0
    
    # Process each dataset folder
    for folder_idx, folder in enumerate(DATASET_FOLDERS, 1):
        logger.info(f"Processing folder {folder_idx}/{len(DATASET_FOLDERS)}: {folder}")
        
        if not os.path.isdir(folder):
            logger.warning(f"Folder not found: {folder}")
            continue
        
        # Get all CSV and Excel files
        files = [f for f in os.listdir(folder) 
                if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
        
        if not files:
            logger.info(f"No data files found in {folder}")
            continue
        
        logger.info(f"Found {len(files)} files in {os.path.basename(folder)}")
        total_files_found += len(files)
        
        # Process each file
        for file_idx, filename in enumerate(files, 1):
            file_path = os.path.join(folder, filename)
            logger.info(f"Processing file {file_idx}/{len(files)}: {filename}")
            
            try:
                # Process file with comprehensive error handling
                trips_processed, file_errors = process_file_with_error_handling(file_path, filename)
                
                if trips_processed:
                    trip_count = len(trips_processed)
                    processed_files.append((filename, trip_count))
                    total_trips_processed += trip_count
                    logger.info(f"[SUCCESS] Processed {filename}: {trip_count} trip(s)")
                else:
                    # File had no successful trips
                    error_summary = "; ".join([error for _, error in file_errors])
                    skipped_files.append((filename, error_summary or "No valid trips found"))
                    logger.warning(f"[SKIPPED] {filename}: {error_summary or 'No valid trips found'}")
                
                # Log individual trip errors if any
                for trip_name, error in file_errors:
                    logger.warning(f"Trip error in {trip_name}: {error}")
                    
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                skipped_files.append((filename, error_msg))
                logger.error(f"[ERROR] Failed to process {filename}: {error_msg}")
    
    # Generate comprehensive summary
    logger.info("=" * 60)
    logger.info("DATASET PROCESSING SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"Total files found: {total_files_found}")
    logger.info(f"Files successfully processed: {len(processed_files)}")
    logger.info(f"Files skipped: {len(skipped_files)}")
    logger.info(f"Total trips processed: {total_trips_processed}")
    
    if processed_files:
        logger.info("\nSuccessfully processed files:")
        for filename, trip_count in processed_files:
            logger.info(f"  [OK] {filename} ({trip_count} trip{'s' if trip_count != 1 else ''})")
    
    if skipped_files:
        logger.info("\nSkipped files:")
        for filename, reason in skipped_files:
            logger.info(f"  [SKIP] {filename} — {reason}")
    
    # Performance statistics
    success_rate = (len(processed_files) / total_files_found * 100) if total_files_found > 0 else 0
    logger.info(f"\nProcessing success rate: {success_rate:.1f}%")
    
    if total_trips_processed > 0:
        avg_trips_per_file = total_trips_processed / len(processed_files) if processed_files else 0
        logger.info(f"Average trips per file: {avg_trips_per_file:.1f}")
        logger.info("\nDatabase is now ready for ML model training!")
        logger.info("✨ All vehicle numbers have been standardized to UPPERCASE with dashes format")
    else:
        logger.warning("No trips were successfully processed. Please check your data files.")
    
    logger.info("=" * 60)
    return {
        'total_files': total_files_found,
        'processed_files': len(processed_files),
        'skipped_files': len(skipped_files),
        'total_trips': total_trips_processed,
        'success_rate': success_rate
    }


def standardize_existing_vehicle_numbers_in_db():
    """
    ✨ UTILITY FUNCTION: Standardize existing vehicle numbers in database
    Run this once to clean up any existing data that wasn't standardized
    """
    logger.info("Starting vehicle number standardization for existing database records...")
    
    try:
        conn = db.get_db_connection()
        
        # Update users table
        users = conn.execute('SELECT id, vehicle_number FROM users WHERE vehicle_number IS NOT NULL').fetchall()
        user_updates = 0
        
        for user_id, vehicle_number in users:
            if vehicle_number:
                standardized = standardize_vehicle_number(vehicle_number)
                if standardized != vehicle_number:
                    conn.execute('UPDATE users SET vehicle_number = ? WHERE id = ?', (standardized, user_id))
                    user_updates += 1
                    logger.debug(f"Updated user {user_id}: '{vehicle_number}' -> '{standardized}'")
        
        # Update trips table (if vehicle_number column exists)
        try:
            trips = conn.execute('SELECT id, vehicle_number FROM trips WHERE vehicle_number IS NOT NULL').fetchall()
            trip_updates = 0
            
            for trip_id, vehicle_number in trips:
                if vehicle_number:
                    standardized = standardize_vehicle_number(vehicle_number)
                    if standardized != vehicle_number:
                        conn.execute('UPDATE trips SET vehicle_number = ? WHERE id = ?', (standardized, trip_id))
                        trip_updates += 1
                        logger.debug(f"Updated trip {trip_id}: '{vehicle_number}' -> '{standardized}'")
            
            conn.commit()
            logger.info(f"✅ Standardized {user_updates} user records and {trip_updates} trip records")
            
        except Exception as e:
            logger.warning(f"Trips table update skipped (column may not exist): {e}")
            conn.commit()
            logger.info(f"✅ Standardized {user_updates} user records")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to standardize existing vehicle numbers: {e}")


def main():
    """Entry point with argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process driving datasets for ML training')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Set logging level')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Process files without database insertion (validation only)')
    parser.add_argument('--standardize-existing', action='store_true',
                       help='Standardize vehicle numbers in existing database records')
    
    args = parser.parse_args()
    
    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))
    
    if args.standardize_existing:
        standardize_existing_vehicle_numbers_in_db()
        return 0
    
    if args.dry_run:
        logger.info("DRY RUN MODE: Files will be processed but not inserted into database")
        # Override db.add_trip for dry run
        original_add_trip = db.add_trip
        db.add_trip = lambda **kwargs: logger.info(f"DRY RUN: Would insert trip: {kwargs}")
    
    try:
        results = process_all_files()
        return 0 if results['total_trips'] > 0 else 1
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error during processing: {e}")
        return 1


if __name__ == '__main__':
    exit(main())