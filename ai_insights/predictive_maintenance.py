import math
from typing import Dict, List
from datetime import datetime, timedelta

def predict_maintenance(trip_data: Dict, user_history: List[Dict] = None, vehicle_age_months: int = 24) -> Dict:
    """Predict maintenance needs using trip data and wear patterns"""
    
    predictions = []
    
    # Brake system analysis
    brake_prediction = _predict_brake_maintenance(trip_data, user_history)
    if brake_prediction:
        predictions.append(brake_prediction)
    
    # Engine maintenance
    engine_prediction = _predict_engine_maintenance(trip_data, user_history, vehicle_age_months)
    if engine_prediction:
        predictions.append(engine_prediction)
    
    # Tire maintenance
    tire_prediction = _predict_tire_maintenance(trip_data, user_history)
    if tire_prediction:
        predictions.append(tire_prediction)
    
    # Transmission analysis
    transmission_prediction = _predict_transmission_maintenance(trip_data, user_history)
    if transmission_prediction:
        predictions.append(transmission_prediction)
    
    # Sort by urgency
    predictions.sort(key=lambda x: x['urgency_score'], reverse=True)
    
    return {
        'predictions': predictions,
        'total_components': len(predictions),
        'urgent_count': len([p for p in predictions if p['risk_level'] == 'high']),
        'estimated_costs': _calculate_maintenance_costs(predictions),
        'next_service_km': _calculate_next_service(predictions),
        'timestamp': datetime.now().isoformat()
    }

def _predict_brake_maintenance(trip_data: Dict, history: List[Dict]) -> Dict:
    """Predict brake system maintenance needs"""
    brake_events = trip_data.get('brake_events', 0)
    distance = trip_data.get('distance_km', 1)
    brake_pressure = trip_data.get('brake_pressure', 50)
    
    # Calculate brake wear rate
    brake_rate = brake_events / distance if distance > 0 else 0
    
    # Historical analysis
    wear_factor = 1.0
    if history:
        historical_brake_rates = []
        for trip in history[-20:]:
            if trip.get('distance_km', 0) > 0:
                rate = trip.get('brake_events', 0) / trip['distance_km']
                historical_brake_rates.append(rate)
        
        if historical_brake_rates:
            avg_rate = sum(historical_brake_rates) / len(historical_brake_rates)
            wear_factor = brake_rate / avg_rate if avg_rate > 0 else 1.0
    
    # Predict brake pad life
    base_life_km = 40000  # Average brake pad life
    adjusted_life = base_life_km / max(wear_factor, 0.5)
    
    # Risk assessment
    if brake_rate > 6 or brake_pressure > 80:
        risk_level = 'high'
        urgency_score = 90
        timeline = "Next 500-1000 km"
    elif brake_rate > 4 or brake_pressure > 65:
        risk_level = 'medium'
        urgency_score = 60
        timeline = "Next 2000-3000 km"
    else:
        risk_level = 'low'
        urgency_score = 30
        timeline = "Next 5000+ km"
    
    return {
        'component': 'brake_system',
        'component_name': 'Brake Pads & Rotors',
        'risk_level': risk_level,
        'urgency_score': urgency_score,
        'predicted_timeline': timeline,
        'wear_percentage': min(95, max(10, 100 - (adjusted_life / base_life_km * 100))),
        'indicators': [
            f"Brake events: {brake_events} ({brake_rate:.1f}/km)",
            f"Brake pressure: {brake_pressure}%",
            f"Wear factor: {wear_factor:.2f}x normal"
        ],
        'recommendations': [
            "Monitor brake performance closely",
            "Check brake fluid levels",
            "Inspect brake pads for wear" if risk_level == 'high' else "Schedule brake inspection"
        ],
        'estimated_cost_range': (150, 400) if risk_level == 'high' else (100, 250)
    }

def _predict_engine_maintenance(trip_data: Dict, history: List[Dict], vehicle_age: int) -> Dict:
    """Predict engine maintenance needs"""
    max_rpm = trip_data.get('max_rpm', 0)
    engine_load = trip_data.get('engine_load', 50)
    distance = trip_data.get('distance_km', 0)
    
    # Calculate engine stress score
    stress_score = 0
    if max_rpm > 4000:
        stress_score += 30
    elif max_rpm > 3000:
        stress_score += 15
    
    if engine_load > 80:
        stress_score += 25
    elif engine_load > 60:
        stress_score += 10
    
    # Age factor
    age_factor = min(2.0, vehicle_age / 24)  # Older vehicles need more maintenance
    stress_score *= age_factor
    
    # Historical analysis
    if history:
        high_rpm_trips = sum(1 for trip in history[-10:] if trip.get('max_rpm', 0) > 3500)
        if high_rpm_trips > 5:
            stress_score += 20
    
    # Determine maintenance needs
    if stress_score > 60:
        risk_level = 'high'
        urgency_score = 85
        timeline = "Next 1000 km or 1 month"
        maintenance_type = "Oil change + engine inspection"
    elif stress_score > 30:
        risk_level = 'medium'
        urgency_score = 50
        timeline = "Next 3000 km or 3 months"
        maintenance_type = "Oil change"
    else:
        risk_level = 'low'
        urgency_score = 25
        timeline = "Next 5000 km or 6 months"
        maintenance_type = "Routine oil change"
    
    return {
        'component': 'engine',
        'component_name': 'Engine Oil & Filter',
        'risk_level': risk_level,
        'urgency_score': urgency_score,
        'predicted_timeline': timeline,
        'wear_percentage': min(90, stress_score),
        'indicators': [
            f"Max RPM: {max_rpm}",
            f"Engine load: {engine_load}%",
            f"Stress score: {stress_score:.1f}",
            f"Vehicle age: {vehicle_age} months"
        ],
        'recommendations': [
            maintenance_type,
            "Check air filter condition",
            "Monitor oil level regularly" if risk_level != 'high' else "Schedule immediate service"
        ],
        'estimated_cost_range': (80, 150) if risk_level != 'high' else (150, 300)
    }

def _predict_tire_maintenance(trip_data: Dict, history: List[Dict]) -> Dict:
    """Predict tire maintenance needs"""
    tire_pressure = trip_data.get('tire_pressure', 32)
    distance = trip_data.get('distance_km', 0)
    max_speed = trip_data.get('max_speed', 0)
    
    # Tire wear calculation
    wear_score = 0
    
    # Pressure impact
    if tire_pressure < 28:
        wear_score += 40
    elif tire_pressure < 30:
        wear_score += 20
    elif tire_pressure > 36:
        wear_score += 15
    
    # Speed impact
    if max_speed > 100:
        wear_score += 25
    elif max_speed > 80:
        wear_score += 10
    
    # Historical mileage
    total_distance = distance
    if history:
        total_distance += sum(trip.get('distance_km', 0) for trip in history[-50:])
    
    # Estimate tire life (assuming 50,000 km average)
    tire_life_remaining = max(0, 50000 - total_distance)
    wear_percentage = (total_distance / 50000) * 100
    
    if wear_score > 50 or wear_percentage > 80:
        risk_level = 'high'
        urgency_score = 80
        timeline = "Next 1000 km"
    elif wear_score > 25 or wear_percentage > 60:
        risk_level = 'medium'
        urgency_score = 45
        timeline = "Next 5000 km"
    else:
        risk_level = 'low'
        urgency_score = 20
        timeline = "Next 10000+ km"
    
    return {
        'component': 'tires',
        'component_name': 'Tire Rotation & Inspection',
        'risk_level': risk_level,
        'urgency_score': urgency_score,
        'predicted_timeline': timeline,
        'wear_percentage': min(95, wear_percentage),
        'indicators': [
            f"Tire pressure: {tire_pressure} PSI",
            f"Total mileage: {total_distance:.0f} km",
            f"Max speed: {max_speed} km/h",
            f"Wear score: {wear_score}"
        ],
        'recommendations': [
            "Check tire pressure monthly",
            "Rotate tires every 8000 km",
            "Inspect tread depth" if risk_level == 'high' else "Monitor tire condition"
        ],
        'estimated_cost_range': (50, 100) if risk_level != 'high' else (400, 800)
    }

def _predict_transmission_maintenance(trip_data: Dict, history: List[Dict]) -> Dict:
    """Predict transmission maintenance needs"""
    gear_position = trip_data.get('gear_position', 3)
    max_rpm = trip_data.get('max_rpm', 0)
    distance = trip_data.get('distance_km', 0)
    
    # Transmission stress factors
    stress_score = 0
    
    # High RPM shifting
    if max_rpm > 4000:
        stress_score += 30
    elif max_rpm > 3500:
        stress_score += 15
    
    # Gear usage patterns
    if gear_position > 5:  # High gear usage
        stress_score += 10
    
    # Historical analysis
    if history:
        high_stress_trips = sum(1 for trip in history[-15:] 
                               if trip.get('max_rpm', 0) > 3500)
        stress_score += high_stress_trips * 2
    
    # Determine maintenance timeline
    if stress_score > 40:
        risk_level = 'medium'
        urgency_score = 40
        timeline = "Next 10000 km or 12 months"
    else:
        risk_level = 'low'
        urgency_score = 20
        timeline = "Next 20000 km or 24 months"
    
    return {
        'component': 'transmission',
        'component_name': 'Transmission Fluid',
        'risk_level': risk_level,
        'urgency_score': urgency_score,
        'predicted_timeline': timeline,
        'wear_percentage': min(70, stress_score),
        'indicators': [
            f"Max RPM: {max_rpm}",
            f"Gear position: {gear_position}",
            f"Stress score: {stress_score}"
        ],
        'recommendations': [
            "Check transmission fluid level",
            "Monitor shifting smoothness",
            "Avoid high RPM shifts"
        ],
        'estimated_cost_range': (120, 250)
    }

def _calculate_maintenance_costs(predictions: List[Dict]) -> Dict:
    """Calculate estimated maintenance costs"""
    if not predictions:
        return {'min_total': 0, 'max_total': 0, 'urgent_cost': 0}
    
    min_total = sum(p['estimated_cost_range'][0] for p in predictions)
    max_total = sum(p['estimated_cost_range'][1] for p in predictions)
    
    urgent_predictions = [p for p in predictions if p['risk_level'] == 'high']
    urgent_cost = sum(p['estimated_cost_range'][1] for p in urgent_predictions)
    
    return {
        'min_total': min_total,
        'max_total': max_total,
        'urgent_cost': urgent_cost,
        'currency': 'USD'
    }

def _calculate_next_service(predictions: List[Dict]) -> int:
    """Calculate recommended next service interval in km"""
    if not predictions:
        return 5000
    
    urgent_predictions = [p for p in predictions if p['risk_level'] == 'high']
    if urgent_predictions:
        return 500  # Immediate service needed
    
    medium_predictions = [p for p in predictions if p['risk_level'] == 'medium']
    if medium_predictions:
        return 2000  # Service soon
    
    return 5000  # Regular service interval