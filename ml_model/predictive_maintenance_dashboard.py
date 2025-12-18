"""
Predictive maintenance calculations for dashboard display
"""
from datetime import datetime, timedelta
import statistics

def calculate_maintenance_predictions(trips):
    """
    Calculate predictive maintenance data based on recent trips
    
    Args:
        trips (list): List of trip dictionaries
        
    Returns:
        dict: Maintenance prediction data for dashboard
    """
    if not trips:
        return get_default_maintenance_data()
    
    # Calculate brake pad life based on brake events
    brake_events = [trip.get('brake_events', 0) for trip in trips if trip.get('brake_events')]
    avg_brake_events = statistics.mean(brake_events) if brake_events else 0
    
    # Brake pad life calculation (higher brake events = lower life)
    brake_life = max(10, 100 - (avg_brake_events * 2))
    brake_days = int(brake_life * 3)  # Rough estimate: 1% = 3 days
    
    if brake_life > 70:
        brake_status, brake_message = "good", "Excellent condition"
    elif brake_life > 40:
        brake_status, brake_message = "warning", "Monitor closely"
    else:
        brake_status, brake_message = "critical", "Replace soon"
    
    # Calculate tire life based on distance and pressure
    distances = [trip.get('distance_km', 0) for trip in trips if trip.get('distance_km')]
    tire_pressures = [trip.get('tire_pressure', 32) for trip in trips if trip.get('tire_pressure')]
    
    total_distance = sum(distances)
    avg_pressure = statistics.mean(tire_pressures) if tire_pressures else 32
    
    # Tire life calculation (distance and pressure affect wear)
    tire_life = max(15, 100 - (total_distance * 0.1) - abs(32 - avg_pressure))
    tire_replacement_date = (datetime.now() + timedelta(days=int(tire_life * 5))).strftime("%b %Y")
    
    if tire_life > 75:
        tire_status, tire_message = "good", "Good condition"
    elif tire_life > 50:
        tire_status, tire_message = "warning", "Plan replacement"
    else:
        tire_status, tire_message = "critical", "Replace immediately"
    
    # Calculate engine health based on RPM, load, and efficiency
    max_rpms = [trip.get('max_rpm', 0) for trip in trips if trip.get('max_rpm')]
    engine_loads = [trip.get('engine_load', 0) for trip in trips if trip.get('engine_load')]
    
    avg_rpm = statistics.mean(max_rpms) if max_rpms else 0
    avg_load = statistics.mean(engine_loads) if engine_loads else 0
    
    # Engine health calculation (lower RPM and load = better health)
    engine_health = max(30, 100 - (avg_rpm / 100) - avg_load)
    engine_health = min(100, int(engine_health))
    
    if engine_health > 80:
        engine_status, engine_message = "good", "Optimal performance"
        engine_detail = "Running efficiently"
    elif engine_health > 60:
        engine_status, engine_message = "warning", "Minor stress detected"
        engine_detail = "Monitor performance"
    else:
        engine_status, engine_message = "critical", "High stress levels"
        engine_detail = "Service recommended"
    
    return {
        'brake_life': int(brake_life),
        'brake_days': brake_days,
        'brake_status': brake_status,
        'brake_message': brake_message,
        'tire_life': int(tire_life),
        'tire_date': tire_replacement_date,
        'tire_status': tire_status,
        'tire_message': tire_message,
        'engine_health': engine_health,
        'engine_detail': engine_detail,
        'engine_status': engine_status,
        'engine_message': engine_message
    }

def get_default_maintenance_data():
    """Default maintenance data when no trips available"""
    return {
        'brake_life': 85,
        'brake_days': 255,
        'brake_status': 'good',
        'brake_message': 'No data available',
        'tire_life': 80,
        'tire_date': (datetime.now() + timedelta(days=400)).strftime("%b %Y"),
        'tire_status': 'good',
        'tire_message': 'No data available',
        'engine_health': 90,
        'engine_detail': 'No data available',
        'engine_status': 'good',
        'engine_message': 'No data available'
    }