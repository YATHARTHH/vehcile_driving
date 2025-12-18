import os
import logging
import re
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, g
)

from utils.db import get_db_connection, init_db
from utils.data_generator import generate_trips

from ml_model.driving_logic import calculate_driving_score
from ml_model.maintenance_logic import (
    build_alerts, save_alerts_to_db, get_health_recommendation, get_recent_alerts
)
from ml_model.predictive_maintenance_dashboard import calculate_maintenance_predictions

from werkzeug.security import generate_password_hash, check_password_hash

# Logging Setup
logging.basicConfig(level=logging.INFO)

# --- Enhanced ML pipeline loader ---
try:
    # Try to load enhanced model first
    from ml_model.enhanced_model_utils import (
        load_enhanced_artifacts, predict_enhanced_behavior, 
        predict_maintenance_needs, get_enhanced_model_info
    )
    
    enhanced_loaded, enhanced_msg = load_enhanced_artifacts()
    if enhanced_loaded:
        ML_MODEL_LOADED = True
        ENHANCED_MODEL_LOADED = True
        model_info = get_enhanced_model_info()
        logging.info(f"✅ Enhanced ML Pipeline Connected: {enhanced_msg}")
    else:
        # Fallback to original model
        from ml_model.model_utils import load_artifacts, predict_behavior
        model, scaler, le, model_info = load_artifacts()
        ML_MODEL_LOADED = True
        ENHANCED_MODEL_LOADED = False
        logging.info(f"✅ Original ML Pipeline Connected: {model_info['best_model_name']}")
        logging.info(f"ℹ️  Enhanced model not available: {enhanced_msg}")
except Exception as e:
    logging.warning("⚠️  ML model loading failed", exc_info=True)
    ML_MODEL_LOADED = False
    ENHANCED_MODEL_LOADED = False
    model = scaler = le = model_info = None


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key_fallback")


with app.app_context():
    init_db()


# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Login required.", "error")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# --- Filters ---
@app.template_filter('to_dict')
def to_dict(row):
    return {key: value for key, value in row.items()}


# --- Routes ---

@app.route("/")
def index():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        vehicle_number = request.form.get("vehicle_number", "").strip().upper()

        # Validate presence
        if not username or not password or not vehicle_number:
            flash("All fields are required.", "error")
            return render_template("register.html")
        
        # Optional: Regex vehicle number validation
        vehicle_pattern = r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$'
        if not re.match(vehicle_pattern, vehicle_number):
            flash("Invalid vehicle number format. Use like MP09AB1234", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password, vehicle_number) VALUES (?, ?, ?)",
                (username, password_hash, vehicle_number)
            )
            conn.commit()
            user_id = cur.lastrowid
            generate_trips(vehicle_number, user_id, n=5)
            flash("Registration successful. Please log in.", "success")
            return redirect("/login")
        except Exception as e:
            msg = str(e)
            if "users.username" in msg:
                flash("Username already exists.", "error")
            elif "users.vehicle_number" in msg:
                flash("Vehicle number already exists.", "error")
            else:
                logging.error("Registration Error", exc_info=True)
                flash(f"Error: {msg}", "error")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["vehicle_number"] = user["vehicle_number"]
            flash("Login successful.", "success")
            return redirect("/dashboard")
        else:
            flash("Invalid credentials.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect("/login")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        vehicle_number = request.form.get('vehicle_number', '').strip().upper()
        new_password = request.form.get('new_password', '').strip()
        if not (username and vehicle_number and new_password):
            flash('Please fill in all fields.', 'error')
            return render_template('forgot_password.html')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = ? AND vehicle_number = ?",
            (username, vehicle_number)
        )
        user = cur.fetchone()
        if user:
            new_pw_hash = generate_password_hash(new_password)
            cur.execute(
                "UPDATE users SET password = ? WHERE username = ? AND vehicle_number = ?",
                (new_pw_hash, username, vehicle_number)
            )
            conn.commit()
            flash('Password reset successful. Please log in.', 'success')
            conn.close()
            return redirect("/login")
        else:
            flash('Username and vehicle number do not match.', 'error')
            conn.close()
    return render_template('forgot_password.html')


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(''' 
        SELECT id, trip_date, distance_km, avg_speed_kmph, max_rpm, max_speed, fuel_consumed, brake_events, steering_angle, angular_velocity,
        acceleration, gear_position, tire_pressure, engine_load, throttle_position, brake_pressure, trip_duration, start_location, end_location 
        FROM trips
        WHERE user_id = ? 
        ORDER BY trip_date DESC
        LIMIT 15
    ''', (session['user_id'],))
    trips = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]

    alert_count = cur.execute(
        "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND resolved = FALSE AND timestamp >= date('now','-30 days')",
        (session['user_id'],)
    ).fetchone()[0]
    conn.close()

    valid_trips = [
        trip for trip in trips
        if trip['distance_km'] > 0 and trip['avg_speed_kmph'] > 0 and trip['max_rpm'] is not None
    ]
    return render_template('dashboard.html', trips=valid_trips, alert_count=alert_count)


@app.route("/trip/<int:trip_id>")
@login_required
def trip_detail(trip_id):
    conn = get_db_connection()
    trip = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()

    if not trip:
        return "Trip not found", 404

    try:
        trip_dict = dict(trip)
        # Required trip fields
        field_names = [
            "avg_speed_kmph", "max_speed", "max_rpm", "fuel_consumed", "brake_events",
            "steering_angle", "angular_velocity", "acceleration", "gear_position",
            "tire_pressure", "engine_load", "throttle_position", "brake_pressure",
            "trip_duration"
        ]
        required_values = [trip_dict.get(f) for f in field_names]
        if None in required_values:
            missing_fields = [f for f, v in zip(field_names, required_values) if v is None]
            raise ValueError(f"Missing trip data: {', '.join(missing_fields)}")

        # Logic-based scoring
        logic_behavior, logic_score = calculate_driving_score(
            trip_dict["avg_speed_kmph"], trip_dict["max_rpm"], trip_dict["brake_events"], trip_dict["steering_angle"],
            trip_dict["angular_velocity"], trip_dict["acceleration"], trip_dict["gear_position"], trip_dict["tire_pressure"],
            trip_dict["engine_load"], trip_dict["throttle_position"], trip_dict["brake_pressure"], trip_dict["trip_duration"]
        )

        # Enhanced ML prediction (if available)
        ml_behavior, ml_confidence, ml_model_used, ml_error = "Unknown", 0.0, "None", None
        maintenance_prediction = None
        
        if ML_MODEL_LOADED:
            try:
                if ENHANCED_MODEL_LOADED:
                    # Use enhanced model with all 14 features
                    ml_result = predict_enhanced_behavior(trip_dict)
                    maintenance_prediction = predict_maintenance_needs(trip_dict)
                    
                    ml_behavior = ml_result.get('behavior_class', 'Unknown')
                    ml_confidence = ml_result.get('confidence', 0.0)
                    ml_model_used = ml_result.get('model_used', 'Enhanced Model')
                    
                    if 'error' in ml_result:
                        ml_error = ml_result['error']
                    elif ml_result.get('warning'):
                        ml_error = f"Warning: {ml_result['warning']}"
                else:
                    # Fallback to original model
                    ml_result = predict_behavior(trip_dict, model, scaler, le, model_info)
                    ml_behavior = ml_result['behavior_class']
                    ml_confidence = ml_result['confidence']
                    ml_model_used = ml_result['model_used']
                    if 'error' in ml_result:
                        ml_error = ml_result['error']
                        
            except Exception as e:
                ml_error = str(e)
        else:
            ml_error = "ML pipeline not loaded"

        # Enhanced maintenance alerts and health recommendation
        maintenance_alerts, health_recommendation = build_alerts(trip_dict)
        
        # Add ML-based maintenance predictions if available
        if maintenance_prediction and not maintenance_prediction.get('error'):
            ml_alerts = maintenance_prediction.get('alerts', [])
            
            # Convert ML alerts to database format
            for ml_alert in ml_alerts:
                maintenance_alerts.append({
                    "alert_type": f"ml_{ml_alert['component'].lower().replace(' ', '_')}",
                    "severity": ml_alert['severity'],
                    "title": f"ML Prediction: {ml_alert['component']}",
                    "description": f"{ml_alert['message']} (Est. {ml_alert['days_remaining']} days)",
                    "icon": ml_alert.get('icon', 'fa-wrench')
                })
            
            # Enhanced health recommendation
            overall_health = maintenance_prediction.get('overall_health', {})
            ml_health_info = f"ML Health Analysis: Overall Score {overall_health.get('score', 0)}/100 ({overall_health.get('status', 'Unknown')}). Components Analyzed: {overall_health.get('components', 0)}"
        else:
            ml_health_info = ""
        
        if maintenance_alerts:
            save_alerts_to_db(maintenance_alerts, session['user_id'], trip_id)

        # Separate recommendations
        combined_recommendation = health_recommendation
        ml_health_recommendation = None
        ml_health_score = None
        ml_health_status = None
        
        if ml_behavior != "Unknown":
            ml_health_recommendation = get_health_recommendation(ml_behavior)
            if maintenance_prediction and not maintenance_prediction.get('error'):
                overall_health = maintenance_prediction.get('overall_health', {})
                ml_health_score = overall_health.get('score', 0)
                ml_health_status = overall_health.get('status', 'Unknown')

    except Exception as e:
        logging.error("Error in trip_detail", exc_info=True)
        logic_behavior = "Unknown"
        logic_score = "N/A"
        ml_behavior = "Unknown"
        ml_confidence = 0.0
        ml_model_used = "Error"
        ml_error = str(e)
        maintenance_alerts = []
        combined_recommendation = f"Insufficient data to generate recommendation. Error: {str(e)}"

    return render_template(
        "trip_detail.html",
        trip=trip,
        logic_score=logic_score,
        logic_behavior=logic_behavior,
        ml_behavior=ml_behavior,
        ml_confidence=ml_confidence,
        ml_model_used=ml_model_used,
        ml_error=ml_error,
        health_recommendation=combined_recommendation,
        ml_health_recommendation=ml_health_recommendation,
        ml_health_score=ml_health_score,
        ml_health_status=ml_health_status,
        maintenance_prediction=maintenance_prediction,
        maintenance_alerts=maintenance_alerts,
        fuel_consumed=trip_dict.get("fuel_consumed"),
        brake_events=trip_dict.get("brake_events"),
        steering_angle=trip_dict.get("steering_angle"),
        acceleration=trip_dict.get("acceleration"),
        angular_velocity=trip_dict.get("angular_velocity"),
        gear_position=trip_dict.get("gear_position"),
        throttle_position=trip_dict.get("throttle_position"),
        brake_pressure=trip_dict.get("brake_pressure"),
        tire_pressure=trip_dict.get("tire_pressure"),
        engine_load=trip_dict.get("engine_load"),
        trip_duration=trip_dict.get("trip_duration")
    )


@app.route("/alerts")
@login_required
def alerts_page():
    recent_alerts = get_recent_alerts(session['user_id'], limit=50)
    return render_template("alerts.html", alerts=recent_alerts)


@app.route("/resolve_alert/<int:alert_id>", methods=["POST"])
@login_required
def resolve_alert(alert_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE alerts SET resolved = TRUE WHERE id = ? AND user_id = ?",
        (alert_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    flash("Alert marked as resolved.", "success")
    return redirect("/alerts")


@app.route("/model-info")
def model_info_page():
    if not ML_MODEL_LOADED:
        return render_template("model_info.html", model_loaded=False)
    return render_template("model_info.html", model_loaded=True, model_info=model_info)


if __name__ == "__main__":
    app.run(debug=True)
