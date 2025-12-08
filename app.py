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

from werkzeug.security import generate_password_hash, check_password_hash
from chatbot.chatbot_logic import VehicleChatbot
from flask import jsonify
from route_optimization.route_engine import RouteOptimizer, geocode_location

# Logging Setup
logging.basicConfig(level=logging.INFO)

# --- ML pipeline loader ---
try:
    from ml_model.model_utils import load_artifacts, predict_behavior
    model, scaler, le, model_info = load_artifacts()
    ML_MODEL_LOADED = True
    logging.info(f"✅ ML Pipeline Connected: {model_info.get('best_model_name', 'Unknown')} ready for predictions")
except Exception:
    logging.warning("⚠️  ML model loading failed", exc_info=True)
    ML_MODEL_LOADED = False
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
    rows = cur.fetchall()
    trips = [dict(zip([column[0] for column in cur.description], row)) for row in rows]

    alert_count = cur.execute(
        "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND resolved = FALSE AND timestamp >= date('now','-30 days')",
        (session['user_id'],)
    ).fetchone()[0]
    conn.close()

    valid_trips = [
        trip for trip in trips
        if trip.get('distance_km', 0) > 0 and trip.get('avg_speed_kmph', 0) > 0 and trip.get('max_rpm') is not None
    ]
    return render_template('dashboard.html', trips=valid_trips, alert_count=alert_count)


@app.route("/trip/<int:trip_id>")
@login_required
def trip_detail(trip_id):
    conn = get_db_connection()
    trip_row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()

    if not trip_row:
        return "Trip not found", 404

    try:
        trip_dict = dict(trip_row)

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

        # ML prediction (if available)
        ml_behavior, ml_confidence, ml_model_used, ml_error = "Unknown", 0.0, "None", None
        if ML_MODEL_LOADED:
            try:
                ml_result = predict_behavior(trip_dict, model, scaler, le, model_info)
                ml_behavior = ml_result.get('behavior_class', 'Unknown')
                ml_confidence = ml_result.get('confidence', 0.0)
                ml_model_used = ml_result.get('model_used', 'Unknown')
                if 'error' in ml_result:
                    ml_error = ml_result['error']
            except Exception as e:
                ml_error = str(e)
                logging.warning(f"ML prediction failed: {e}")
        else:
            ml_error = "ML pipeline not loaded"

        # Maintenance alerts and health recommendation
        maintenance_alerts, health_recommendation = build_alerts(trip_dict)
        # Save alerts to DB if any
        if maintenance_alerts:
            try:
                save_alerts_to_db(maintenance_alerts, session.get('user_id'), trip_id)
            except Exception:
                logging.exception("Failed to save maintenance alerts to DB")

        # Combine ML and logic recommendations
        if ml_behavior != "Unknown":
            try:
                ml_health = get_health_recommendation(ml_behavior)
            except Exception:
                ml_health = ""
            combined_recommendation = f"{health_recommendation}\n\n{ml_health}" if ml_health else health_recommendation
        else:
            combined_recommendation = health_recommendation

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
        trip=trip_dict,
        logic_score=logic_score,
        logic_behavior=logic_behavior,
        ml_behavior=ml_behavior,
        ml_confidence=ml_confidence,
        ml_model_used=ml_model_used,
        ml_error=ml_error,
        health_recommendation=combined_recommendation,
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


@app.route("/chatbot", methods=["POST"])
@login_required
def chatbot():
    data = request.get_json()
    message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id', '')
    
    if not message:
        return jsonify({'response': 'Please enter a message.', 'suggestions': []})
    
    # Get user's recent trip data for context
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Enhanced trip data query
    cur.execute('''
        SELECT distance_km, avg_speed_kmph, max_rpm, fuel_consumed, brake_events,
               trip_date, max_speed, steering_angle, acceleration, gear_position,
               tire_pressure, engine_load, throttle_position, brake_pressure
        FROM trips WHERE user_id = ? ORDER BY trip_date DESC LIMIT 10
    ''', (session['user_id'],))
    rows = cur.fetchall()
    recent_trips = [dict(zip([col[0] for col in cur.description], row)) for row in rows]
    
    # Get user vehicle info
    cur.execute('SELECT vehicle_number FROM users WHERE id = ?', (session['user_id'],))
    user_info = cur.fetchone()
    vehicle_number = user_info['vehicle_number'] if user_info else 'Unknown'
    
    conn.close()
    
    # Enhanced user data
    user_data = {
        'recent_trips': recent_trips,
        'vehicle_number': vehicle_number,
        'user_id': session['user_id']
    }
    
    # Initialize chatbot with session management
    if 'chatbot_instance' not in session or session.get('conversation_id') != conversation_id:
        session['chatbot_instance'] = True
        session['conversation_id'] = conversation_id
    
    chatbot_instance = VehicleChatbot()
    response = chatbot_instance.get_response(message, user_data)
    
    # Generate contextual suggestions with NLP enhancement
    suggestions = generate_suggestions_enhanced(message, user_data, chatbot_instance)
    
    # Get NLP insights for debugging (optional)
    nlp_insights = chatbot_instance.get_nlp_insights(message)
    
    return jsonify({
        'response': response,
        'suggestions': suggestions,
        'conversation_id': conversation_id,
        'nlp_insights': nlp_insights if data.get('debug') else None
    })


def generate_suggestions_enhanced(message, user_data, chatbot_instance):
    """Generate enhanced contextual suggestions using NLP"""
    suggestions = []
    
    # Get NLP insights
    try:
        nlp_insights = chatbot_instance.get_nlp_insights(message)
        
        # Use entities and keywords for better suggestions
        if nlp_insights and 'entities' in nlp_insights:
            entities = nlp_insights['entities']
            keywords = nlp_insights.get('keywords', [])
            
            # Entity-based suggestions
            if 'speed' in entities:
                suggestions.extend([
                    "Optimize my speed for better efficiency",
                    "What's the ideal speed range?"
                ])
            
            if 'fuel' in entities:
                suggestions.extend([
                    "Calculate my fuel savings potential",
                    "Compare my fuel efficiency"
                ])
            
            # Keyword-based suggestions
            if 'maintenance' in keywords:
                suggestions.extend([
                    "Create maintenance schedule",
                    "Check vehicle health status"
                ])
            
            if 'safety' in keywords:
                suggestions.extend([
                    "Emergency driving tips",
                    "Weather safety advice"
                ])
        
        # Sentiment-based suggestions
        if nlp_insights and 'sentiment' in nlp_insights:
            sentiment = nlp_insights['sentiment'].get('final', 'neutral')
            if sentiment == 'negative':
                suggestions.append("How can I solve this issue?")
            elif sentiment == 'positive':
                suggestions.append("Show me advanced tips")
    
    except Exception:
        pass  # Fallback to original logic
    
    # Fallback to original suggestion logic if no NLP suggestions
    if not suggestions:
        suggestions = generate_suggestions(message, user_data)
    
    return suggestions[:3]  # Limit to 3 suggestions

def generate_suggestions(message, user_data):
    """Generate contextual follow-up suggestions (original logic)"""
    message_lower = message.lower()
    suggestions = []
    
    if any(word in message_lower for word in ['fuel', 'efficiency', 'gas']):
        suggestions = [
            "What's my current fuel efficiency?",
            "How can I reduce fuel costs?",
            "Show me eco-driving tips"
        ]
    elif any(word in message_lower for word in ['trip', 'analyze', 'performance']):
        suggestions = [
            "Compare my recent trips",
            "What's my driving score?",
            "Show weekly summary"
        ]
    elif any(word in message_lower for word in ['maintenance', 'service', 'repair']):
        suggestions = [
            "When is my next service due?",
            "Check for maintenance alerts",
            "Show maintenance schedule"
        ]
    elif any(word in message_lower for word in ['safety', 'tips', 'advice']):
        suggestions = [
            "Weather driving tips",
            "Highway safety advice",
            "Emergency preparedness"
        ]
    else:
        # Default suggestions based on user data
        if user_data.get('recent_trips'):
            suggestions = [
                "Analyze my driving patterns",
                "How can I improve?",
                "Show me cost savings tips"
            ]
        else:
            suggestions = [
                "What can you help me with?",
                "Give me driving tips",
                "How do I save fuel?"
            ]
    
    return suggestions[:3]  # Limit to 3 suggestions

@app.route("/chatbot/suggestions")
@login_required
def chatbot_suggestions():
    # Get user context for personalized suggestions
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as trip_count FROM trips WHERE user_id = ?', (session['user_id'],))
    trip_count = cur.fetchone()['trip_count']
    conn.close()
    
    if trip_count > 0:
        suggestions = [
            "Analyze my recent trips",
            "How can I improve my fuel efficiency?",
            "What's my driving score?",
            "Show me cost savings tips",
            "Give me maintenance advice"
        ]
    else:
        suggestions = [
            "What can you help me with?",
            "Give me driving tips",
            "How do I save fuel?",
            "Tell me about safety features",
            "Show maintenance schedule"
        ]
    
    return jsonify({'suggestions': suggestions})

@app.route("/chatbot/clear", methods=["POST"])
@login_required
def clear_chatbot_session():
    """Clear chatbot session data"""
    session.pop('chatbot_instance', None)
    session.pop('conversation_id', None)
    return jsonify({'success': True})


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


@app.route("/route-planner")
@login_required
def route_planner():
    return render_template("route_planner.html")


@app.route("/api/save-route", methods=["POST"])
@login_required
def save_route():
    try:
        data = request.get_json()
        route_data = data.get('route')
        
        if not route_data:
            return jsonify({'success': False, 'error': 'No route data provided'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create saved_routes table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS saved_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                route_name TEXT,
                start_location TEXT,
                end_location TEXT,
                route_type TEXT,
                distance_km REAL,
                travel_time_minutes INTEGER,
                fuel_consumption REAL,
                fuel_cost REAL,
                efficiency_score INTEGER,
                saved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert saved route
        cur.execute('''
            INSERT INTO saved_routes 
            (user_id, route_name, start_location, end_location, route_type, 
             distance_km, travel_time_minutes, fuel_consumption, fuel_cost, efficiency_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user_id'],
            route_data['name'],
            data.get('start_location', ''),
            data.get('end_location', ''),
            route_data['type'],
            route_data['distance_km'],
            route_data['travel_time_minutes'],
            route_data['fuel_consumption'],
            route_data['fuel_cost'],
            route_data['efficiency_score']
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Route saved successfully'})
        
    except Exception as e:
        logging.error(f"Save route error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@app.route("/api/route-optimize", methods=["POST"])
@login_required
def optimize_route():
    try:
        data = request.get_json()
        start_coords = data.get('start_coords')
        end_coords = data.get('end_coords')
        priority = data.get('priority', 'balanced')
        
        if not start_coords or not end_coords:
            return jsonify({'success': False, 'error': 'Missing coordinates'})
        
        # Get user's vehicle data for personalization
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT 15.0 as avg_efficiency,
                   AVG(engine_load) as avg_engine_load,
                   COUNT(*) as trip_count
            FROM trips 
            WHERE user_id = ? AND distance_km > 0
        ''', (session['user_id'],))
        
        user_stats = cur.fetchone()
        conn.close()
        
        # Prepare user preferences and vehicle data
        user_preferences = {
            'priority': priority,
            'fuel_efficiency': user_stats['avg_efficiency'] if user_stats['avg_efficiency'] else 15.0
        }
        
        user_vehicle_data = {
            'avg_engine_load': user_stats['avg_engine_load'] if user_stats['avg_engine_load'] else 50
        }
        
        user_history = {
            'avg_fuel_efficiency': user_stats['avg_efficiency'] if user_stats['avg_efficiency'] else 15.0,
            'preferred_route_type': priority
        }
        
        # Initialize route optimizer
        optimizer = RouteOptimizer()
        
        # Generate optimized routes
        routes = optimizer.optimize_routes(
            tuple(start_coords), 
            tuple(end_coords),
            user_preferences,
            user_vehicle_data
        )
        
        # Get personalized recommendations
        recommendations = optimizer.get_personalized_recommendations(routes, user_history)
        
        return jsonify({
            'success': True,
            'routes': routes,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logging.error(f"Route optimization error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


if __name__ == "__main__":
    app.run(debug=True)
