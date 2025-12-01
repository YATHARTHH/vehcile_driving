"""
ml_model/maintenance_logic.py
----------------------------
Health recommendations and maintenance alerts logic based on trip data.
Compatible with the alerts table in the latest db.py schema.
"""

def build_alerts(trip):
    """
    Build health/maintenance alerts for a single trip dict.
    Returns (alerts_list, high_level_recommendation)
    
    Args:
        trip (dict): Trip data containing sensor readings
        
    Returns:
        tuple: (alerts_list, health_recommendation_string)
    """
    alerts = []

    # --- 1. Tyre pressure analysis ---
    tyre = trip.get("tire_pressure")
    if tyre is not None and tyre != "":
        tyre = float(tyre)
        if tyre < 28:
            alerts.append({
                "alert_type": "tire_pressure",
                "severity": "warning",
                "title": "Low Tyre Pressure",
                "description": f"Measured {tyre} psi (recommended ≥32 psi).",
                "icon": "fa-tire"
            })
        elif tyre > 42:
            alerts.append({
                "alert_type": "tire_pressure", 
                "severity": "warning",
                "title": "High Tyre Pressure",
                "description": f"Measured {tyre} psi (recommended ≤40 psi).",
                "icon": "fa-tire"
            })

    # --- 2. Engine load analysis ---
    engine_load = trip.get("engine_load")
    if engine_load is not None and engine_load != "":
        engine_load = float(engine_load)
        if engine_load > 90:
            alerts.append({
                "alert_type": "engine_load",
                "severity": "warning", 
                "title": "High Engine Load",
                "description": f"Engine at {engine_load}% load - check air filter and driving habits.",
                "icon": "fa-car"
            })

    # --- 3. Brake events analysis ---
    brakes = trip.get("brake_events")
    if brakes is not None and brakes != "":
        brakes = int(brakes)
        if brakes > 30:
            alerts.append({
                "alert_type": "brake_events",
                "severity": "warning",
                "title": "Excessive Hard Braking",
                "description": f"{brakes} hard brake events - inspect brake system soon.",
                "icon": "fa-car-burst"
            })
        elif brakes > 15:
            alerts.append({
                "alert_type": "brake_events",
                "severity": "info",
                "title": "Frequent Hard Braking",
                "description": f"{brakes} hard brake events detected - increased brake pad wear likely.",
                "icon": "fa-car-burst"
            })

    # --- 4. High RPM analysis ---
    max_rpm = trip.get("max_rpm")
    if max_rpm is not None and max_rpm != "":
        max_rpm = float(max_rpm)
        if max_rpm > 6000:
            alerts.append({
                "alert_type": "high_rpm",
                "severity": "warning",
                "title": "High RPM Operation",
                "description": f"Peak RPM: {max_rpm} - engine stress detected.",
                "icon": "fa-tachometer-alt"
            })

    # --- 5. Fuel efficiency analysis ---
    fuel = trip.get("fuel_consumed")
    dist = trip.get("distance_km")
    if fuel and dist and fuel not in ("", 0, "0") and dist not in ("", 0, "0"):
        fuel = float(fuel)
        dist = float(dist)
        efficiency = dist / fuel if fuel > 0 else 0
        if efficiency < 8:  # Less than 8 km/L
            alerts.append({
                "alert_type": "fuel_efficiency",
                "severity": "info",
                "title": "Low Fuel Efficiency",
                "description": f"Efficiency: {efficiency:.1f} km/L - consider maintenance check.",
                "icon": "fa-gas-pump"
            })

    # --- 6. Speeding analysis ---
    max_speed = trip.get("max_speed")
    if max_speed is not None and max_speed != "":
        max_speed = float(max_speed)
        if max_speed > 120:
            alerts.append({
                "alert_type": "speeding",
                "severity": "warning",
                "title": "Speeding Detected",
                "description": f"Max speed {max_speed} km/h - safety risk and increased wear.",
                "icon": "fa-gauge-high"
            })

    # --- 7. Long idle or inefficient trip ---
    trip_duration = trip.get("trip_duration")
    if trip_duration and dist and trip_duration not in ("", 0, "0"):
        trip_duration = float(trip_duration)
        dist = float(dist)
        if trip_duration > 180 and dist < 50:
            alerts.append({
                "alert_type": "idle_time",
                "severity": "info", 
                "title": "Excessive Idle Time",
                "description": "Trip duration is very long with short distance - reduce idle to save fuel.",
                "icon": "fa-clock"
            })

    # --- Health Recommendation Determination ---
    if not alerts:
        health_recommendation = "✅ Vehicle health is optimal. All systems functioning normally."
    elif any(a["severity"] == "critical" for a in alerts):
        health_recommendation = "🚨 Critical issues detected - service immediately to prevent damage."
    elif any(a["severity"] == "warning" for a in alerts):
        health_recommendation = "⚠️ Warning conditions detected - schedule maintenance soon to prevent issues."
    else:
        health_recommendation = "ℹ️ Minor observations noted - consider optimizing driving habits for better efficiency."

    return alerts, health_recommendation

def get_health_recommendation(behavior_class):
    """
    Get health recommendation based on ML behavior classification.
    Args:
        behavior_class (str): ML predicted behavior ('Good', 'Average', 'Risky', etc.)
    Returns:
        str: Health recommendation message.
    """
    recommendations = {
        'Good':       "🌟 Excellent driving behavior! Vehicle health should remain optimal with regular maintenance.",
        'Average':    "⚖️ Moderate driving detected. Consider smoother acceleration/braking to reduce wear.",
        'Risky':      "⚠️ Aggressive driving detected! High vehicle stress - inspect brakes, tires, and engine components.",
        'Safe':       "🌟 Safe driving detected! Vehicle health should remain optimal with regular maintenance.",
        'Moderate':   "⚖️ Moderate driving behavior. Some stress on vehicle components - monitor closely.",
        'Aggressive': "🚨 Aggressive driving detected! High wear on brakes, tires, and engine - service recommended.",
        'Unknown':    "❓ Unable to assess driving behavior - ensure all sensors are functioning properly."
    }
    return recommendations.get(behavior_class, recommendations['Unknown'])

def save_alerts_to_db(alerts, user_id, trip_id):
    """
    Save alerts to the alerts table.
    """
    from utils.db import get_db_connection
    conn = get_db_connection()
    for alert in alerts:
        conn.execute('''
            INSERT INTO alerts (user_id, trip_id, alert_type, severity, title, message, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            trip_id,
            alert["alert_type"],
            alert["severity"],
            alert["title"],
            alert["description"],
            alert["icon"]
        ))
    conn.commit()
    conn.close()

def get_recent_alerts(user_id, limit=10):
    """
    Get recent unresolved alerts for a user (for alerts dashboard page)
    """
    from utils.db import get_db_connection
    conn = get_db_connection()
    alerts = conn.execute('''
        SELECT * FROM alerts 
        WHERE user_id = ? AND resolved = FALSE
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit)).fetchall()
    conn.close()
    return [dict(alert) for alert in alerts]
