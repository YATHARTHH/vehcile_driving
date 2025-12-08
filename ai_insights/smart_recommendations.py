import random
from typing import Dict, List
from datetime import datetime, timedelta

def generate_recommendations(trip_data: Dict, user_profile: Dict = None, context: Dict = None) -> Dict:
    """Generate smart, contextual driving recommendations"""
    
    if not user_profile:
        user_profile = {'experience_level': 'intermediate', 'goals': ['fuel_efficiency']}
    
    if not context:
        context = {'weather': 'clear', 'time_of_day': 'day', 'traffic': 'normal'}
    
    recommendations = []
    
    # Fuel efficiency recommendations
    fuel_recs = _generate_fuel_recommendations(trip_data, user_profile, context)
    recommendations.extend(fuel_recs)
    
    # Safety recommendations
    safety_recs = _generate_safety_recommendations(trip_data, user_profile, context)
    recommendations.extend(safety_recs)
    
    # Performance recommendations
    performance_recs = _generate_performance_recommendations(trip_data, user_profile)
    recommendations.extend(performance_recs)
    
    # Maintenance recommendations
    maintenance_recs = _generate_maintenance_recommendations(trip_data)
    recommendations.extend(maintenance_recs)
    
    # Sort by priority and relevance
    recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
    
    return {
        'recommendations': recommendations[:8],  # Top 8 recommendations
        'total_generated': len(recommendations),
        'context_factors': context,
        'personalization_level': _calculate_personalization_level(user_profile),
        'categories': _categorize_recommendations(recommendations[:8]),
        'timestamp': datetime.now().isoformat()
    }

def _generate_fuel_recommendations(trip_data: Dict, profile: Dict, context: Dict) -> List[Dict]:
    """Generate fuel efficiency recommendations"""
    recommendations = []
    
    avg_speed = trip_data.get('avg_speed_kmph', 0)
    fuel_consumed = trip_data.get('fuel_consumed', 0)
    distance = trip_data.get('distance_km', 1)
    max_rpm = trip_data.get('max_rpm', 0)
    
    fuel_efficiency = distance / fuel_consumed if fuel_consumed > 0 else 15
    
    # Speed optimization
    if avg_speed > 85:
        recommendations.append({
            'category': 'fuel_efficiency',
            'title': 'Optimize Speed for Fuel Savings',
            'description': f'Reduce average speed from {avg_speed:.1f} to 70-80 km/h',
            'impact': 'Save 15-20% fuel consumption',
            'difficulty': 'easy',
            'priority_score': 85,
            'estimated_savings': f'₹{(fuel_consumed * 0.18 * 110):.0f} per trip',
            'action_steps': [
                'Use cruise control on highways',
                'Maintain 70-80 km/h speed range',
                'Plan extra 5-10 minutes for journey'
            ],
            'context_relevance': 'high' if context.get('traffic') == 'light' else 'medium'
        })
    
    # RPM management
    if max_rpm > 3500:
        recommendations.append({
            'category': 'fuel_efficiency',
            'title': 'Reduce Engine RPM',
            'description': f'Keep RPM below 3000 (current max: {max_rpm})',
            'impact': 'Improve fuel efficiency by 8-12%',
            'difficulty': 'medium',
            'priority_score': 75,
            'estimated_savings': f'₹{(fuel_consumed * 0.10 * 110):.0f} per trip',
            'action_steps': [
                'Shift gears earlier',
                'Accelerate more gradually',
                'Use eco-mode if available'
            ],
            'context_relevance': 'high'
        })
    
    # Poor fuel efficiency alert
    if fuel_efficiency < 10:
        recommendations.append({
            'category': 'fuel_efficiency',
            'title': 'Improve Overall Fuel Efficiency',
            'description': f'Current efficiency: {fuel_efficiency:.1f} km/L (target: 12+ km/L)',
            'impact': 'Potential 25% fuel cost reduction',
            'difficulty': 'medium',
            'priority_score': 90,
            'estimated_savings': f'₹{(fuel_consumed * 0.25 * 110):.0f} per trip',
            'action_steps': [
                'Check tire pressure weekly',
                'Remove excess weight from vehicle',
                'Service engine if overdue',
                'Plan efficient routes'
            ],
            'context_relevance': 'high'
        })
    
    return recommendations

def _generate_safety_recommendations(trip_data: Dict, profile: Dict, context: Dict) -> List[Dict]:
    """Generate safety-focused recommendations"""
    recommendations = []
    
    brake_events = trip_data.get('brake_events', 0)
    distance = trip_data.get('distance_km', 1)
    max_speed = trip_data.get('max_speed', 0)
    
    brake_rate = brake_events / distance if distance > 0 else 0
    
    # Excessive braking
    if brake_rate > 5:
        recommendations.append({
            'category': 'safety',
            'title': 'Reduce Hard Braking Events',
            'description': f'{brake_events} brake events in {distance:.1f}km indicates aggressive driving',
            'impact': 'Reduce accident risk by 30%',
            'difficulty': 'medium',
            'priority_score': 80,
            'action_steps': [
                'Increase following distance to 3+ seconds',
                'Anticipate traffic flow changes',
                'Coast to red lights instead of braking hard',
                'Check mirrors every 5-8 seconds'
            ],
            'context_relevance': 'high' if context.get('traffic') == 'heavy' else 'medium'
        })
    
    # Speed safety
    if max_speed > 100:
        recommendations.append({
            'category': 'safety',
            'title': 'Maintain Safe Speeds',
            'description': f'Maximum speed of {max_speed} km/h exceeds safe limits',
            'impact': 'Significantly reduce accident risk',
            'difficulty': 'easy',
            'priority_score': 95,
            'action_steps': [
                'Observe speed limits strictly',
                'Adjust speed for road conditions',
                'Use speed limit alerts if available'
            ],
            'context_relevance': 'high'
        })
    
    # Weather-specific safety
    if context.get('weather') in ['rain', 'fog', 'snow']:
        recommendations.append({
            'category': 'safety',
            'title': f'Weather-Adapted Driving ({context["weather"].title()})',
            'description': 'Adjust driving for current weather conditions',
            'impact': 'Prevent weather-related incidents',
            'difficulty': 'medium',
            'priority_score': 85,
            'action_steps': [
                'Reduce speed by 20% in wet conditions',
                'Increase following distance to 4+ seconds',
                'Use headlights even during day',
                'Avoid sudden movements'
            ],
            'context_relevance': 'high'
        })
    
    return recommendations

def _generate_performance_recommendations(trip_data: Dict, profile: Dict) -> List[Dict]:
    """Generate performance improvement recommendations"""
    recommendations = []
    
    acceleration = trip_data.get('acceleration', 0)
    steering_angle = trip_data.get('steering_angle', 0)
    
    # Smooth acceleration
    if abs(acceleration) > 3:
        recommendations.append({
            'category': 'performance',
            'title': 'Improve Acceleration Smoothness',
            'description': f'Current acceleration: {acceleration:.1f} m/s² (target: ±2 m/s²)',
            'impact': 'Better vehicle control and passenger comfort',
            'difficulty': 'medium',
            'priority_score': 60,
            'action_steps': [
                'Apply gradual pressure on accelerator',
                'Anticipate speed changes needed',
                'Practice smooth throttle control',
                'Use progressive acceleration technique'
            ],
            'context_relevance': 'medium'
        })
    
    # Steering smoothness
    if abs(steering_angle) > 15:
        recommendations.append({
            'category': 'performance',
            'title': 'Enhance Steering Control',
            'description': 'Reduce abrupt steering movements for better stability',
            'impact': 'Improved vehicle stability and tire longevity',
            'difficulty': 'easy',
            'priority_score': 50,
            'action_steps': [
                'Make gradual steering adjustments',
                'Plan lane changes well in advance',
                'Keep hands at 9 and 3 o\'clock position',
                'Look ahead to anticipate turns'
            ],
            'context_relevance': 'medium'
        })
    
    return recommendations

def _generate_maintenance_recommendations(trip_data: Dict) -> List[Dict]:
    """Generate maintenance-related recommendations"""
    recommendations = []
    
    tire_pressure = trip_data.get('tire_pressure', 32)
    engine_load = trip_data.get('engine_load', 50)
    
    # Tire pressure
    if tire_pressure < 30 or tire_pressure > 36:
        recommendations.append({
            'category': 'maintenance',
            'title': 'Optimize Tire Pressure',
            'description': f'Current: {tire_pressure} PSI (optimal: 30-34 PSI)',
            'impact': 'Improve fuel efficiency by 3-5%',
            'difficulty': 'easy',
            'priority_score': 70,
            'action_steps': [
                'Check tire pressure monthly',
                'Adjust to manufacturer specifications',
                'Check when tires are cold',
                'Include spare tire in checks'
            ],
            'context_relevance': 'high'
        })
    
    # Engine load
    if engine_load > 75:
        recommendations.append({
            'category': 'maintenance',
            'title': 'Reduce Engine Stress',
            'description': f'High engine load detected: {engine_load}%',
            'impact': 'Extend engine life and improve efficiency',
            'difficulty': 'medium',
            'priority_score': 65,
            'action_steps': [
                'Check air filter condition',
                'Ensure regular oil changes',
                'Avoid carrying unnecessary weight',
                'Schedule engine diagnostic if persistent'
            ],
            'context_relevance': 'medium'
        })
    
    return recommendations

def _calculate_personalization_level(profile: Dict) -> str:
    """Calculate how personalized the recommendations are"""
    factors = 0
    
    if profile.get('experience_level'):
        factors += 1
    if profile.get('goals'):
        factors += 1
    if profile.get('vehicle_type'):
        factors += 1
    if profile.get('driving_history'):
        factors += 1
    
    if factors >= 3:
        return 'high'
    elif factors >= 2:
        return 'medium'
    else:
        return 'low'

def _categorize_recommendations(recommendations: List[Dict]) -> Dict:
    """Categorize recommendations by type"""
    categories = {}
    for rec in recommendations:
        category = rec['category']
        if category not in categories:
            categories[category] = 0
        categories[category] += 1
    
    return categories

def get_contextual_tips(context: Dict) -> List[str]:
    """Get quick contextual tips based on current conditions"""
    tips = []
    
    weather = context.get('weather', 'clear')
    traffic = context.get('traffic', 'normal')
    time_of_day = context.get('time_of_day', 'day')
    
    # Weather tips
    if weather == 'rain':
        tips.extend([
            "🌧️ Reduce speed by 20% in wet conditions",
            "🚗 Increase following distance to 4+ seconds",
            "💡 Use headlights for better visibility"
        ])
    elif weather == 'fog':
        tips.extend([
            "🌫️ Use low beam headlights, not high beams",
            "👀 Follow road markings closely",
            "🐌 Drive significantly slower than normal"
        ])
    
    # Traffic tips
    if traffic == 'heavy':
        tips.extend([
            "🚦 Maintain steady speed in traffic",
            "⏰ Leave extra time for journey",
            "🧘 Stay calm and patient"
        ])
    
    # Time-based tips
    if time_of_day == 'night':
        tips.extend([
            "🌙 Ensure headlights are clean and working",
            "👁️ Take breaks every 2 hours",
            "⚡ Reduce speed on unfamiliar roads"
        ])
    
    return tips[:5]  # Return top 5 tips