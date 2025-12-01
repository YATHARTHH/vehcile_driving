import random
from datetime import datetime, timedelta
from utils.db import get_db_connection

def generate_random_trip_data():
    today = datetime.today()
    trip_date = (today - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d")
    distance = round(random.uniform(10, 200), 1)
    avg_speed = round(random.uniform(40, 100), 1)
    max_speed = round(avg_speed + random.uniform(10, 50), 1)
    max_rpm = random.randint(3000, 6000)
    fuel_consumed = round(distance / random.uniform(10, 20), 2)
    brake_events = random.randint(1, 15)
    steering_angle = round(random.uniform(-30, 30), 1)
    angular_velocity = round(random.uniform(0.5, 3.5), 2)
    acceleration = round(random.uniform(0.5, 3.5), 2)
    gear_position = random.randint(1, 6)
    tire_pressure = round(random.uniform(28.0, 35.0), 1)
    engine_load = round(random.uniform(20.0, 90.0), 1)
    throttle_position = round(random.uniform(10, 100), 2)  # Throttle position between 10% and 100%
    brake_pressure = round(random.uniform(0, 100), 2)  # Brake pressure between 0 psi to 100 psi
    start_location = f"{round(random.uniform(-90, 90), 6)},{round(random.uniform(-180, 180), 6)}"  # Random lat-long
    end_location = f"{round(random.uniform(-90, 90), 6)},{round(random.uniform(-180, 180), 6)}"  # Random lat-long
    trip_duration = random.randint(10, 120) 
    gps_path = "path_to_gps_data"

    return {
        'trip_date': trip_date,
        'distance': distance,
        'avg_speed': avg_speed,
        'max_speed': max_speed,
        'max_rpm': max_rpm,
        'fuel_consumed': fuel_consumed,
        'brake_events': brake_events,
        'steering_angle': steering_angle,
        'angular_velocity': angular_velocity,
        'acceleration': acceleration, 
        'gear_position': gear_position,
        'tire_pressure': tire_pressure,
        'engine_load': engine_load,
        'throttle_position':throttle_position,
        'brake_pressure': brake_pressure,
        'trip_duration': trip_duration,
        'start_location': start_location,
        'end_location': end_location,
        'gps_path': gps_path
    }

def generate_trips(vehicle_number, user_id, n=5):
    conn = get_db_connection()
    cur = conn.cursor()

    for _ in range(n):
        data = generate_random_trip_data()
        cur.execute(""" 
            INSERT INTO trips (
        user_id, trip_date, distance_km, avg_speed_kmph, max_speed, max_rpm, 
        fuel_consumed, brake_events, steering_angle, angular_velocity, acceleration, gear_position, 
        tire_pressure, engine_load, throttle_position, brake_pressure, trip_duration, 
        start_location, end_location, gps_path
    ) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    user_id, data['trip_date'], data['distance'], data['avg_speed'], data['max_speed'], data['max_rpm'],
    data['fuel_consumed'], data['brake_events'], data['steering_angle'], data['angular_velocity'], 
    data['acceleration'], data['gear_position'], data['tire_pressure'], data['engine_load'],
    data['throttle_position'], data['brake_pressure'], data['trip_duration'], 
    data['start_location'], data['end_location'], data['gps_path']
))


    conn.commit()
    conn.close()
