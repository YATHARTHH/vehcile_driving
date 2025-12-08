import math
from typing import Dict, List, Tuple
from datetime import datetime

def predict_fuel_consumption(route_data: Dict, user_profile: Dict = None, vehicle_data: Dict = None) -> Dict:
    """Predict fuel consumption for different driving scenarios"""
    
    if not user_profile:
        user_profile = {'avg_efficiency': 12.0, 'driving_style': 'normal'}
    
    if not vehicle_data:
        vehicle_data = {'engine_size': 1.6, 'vehicle_type': 'sedan', 'age_years': 3}
    
    distance = route_data.get('distance_km', 0)
    route_type = route_data.get('route_type', 'mixed')
    traffic_conditions = route_data.get('traffic', 'normal')
    
    # Generate predictions for different scenarios
    scenarios = _generate_driving_scenarios(distance, route_type, traffic_conditions, user_profile, vehicle_data)
    
    # Calculate cost implications
    cost_analysis = _calculate_cost_analysis(scenarios)
    
    # Generate optimization suggestions
    optimization_tips = _generate_optimization_tips(scenarios, user_profile)
    
    return {
        'scenarios': scenarios,
        'cost_analysis': cost_analysis,
        'optimization_tips': optimization_tips,
        'best_scenario': _find_best_scenario(scenarios),
        'route_factors': _analyze_route_factors(route_data),
        'confidence_level': _calculate_prediction_confidence(user_profile, vehicle_data),
        'timestamp': datetime.now().isoformat()
    }

def _generate_driving_scenarios(distance: float, route_type: str, traffic: str, 
                               user_profile: Dict, vehicle_data: Dict) -> List[Dict]:
    """Generate fuel consumption predictions for different driving styles"""
    
    base_efficiency = user_profile.get('avg_efficiency', 12.0)
    scenarios = []
    
    # Eco-driving scenario
    eco_scenario = _calculate_eco_scenario(distance, route_type, traffic, base_efficiency, vehicle_data)
    scenarios.append(eco_scenario)
    
    # Normal driving scenario
    normal_scenario = _calculate_normal_scenario(distance, route_type, traffic, base_efficiency, vehicle_data)
    scenarios.append(normal_scenario)
    
    # Aggressive driving scenario
    aggressive_scenario = _calculate_aggressive_scenario(distance, route_type, traffic, base_efficiency, vehicle_data)
    scenarios.append(aggressive_scenario)
    
    # Sport/Performance scenario
    sport_scenario = _calculate_sport_scenario(distance, route_type, traffic, base_efficiency, vehicle_data)
    scenarios.append(sport_scenario)
    
    return scenarios

def _calculate_eco_scenario(distance: float, route_type: str, traffic: str, 
                           base_efficiency: float, vehicle_data: Dict) -> Dict:
    """Calculate eco-driving fuel consumption"""
    
    # Eco-driving efficiency boost
    efficiency_multiplier = 1.25  # 25% better efficiency
    
    # Route type adjustments
    route_multipliers = {
        'highway': 1.1,    # Highways are efficient at steady speeds
        'city': 0.9,       # City eco-driving saves more fuel
        'mixed': 1.0,      # Balanced
        'rural': 1.05      # Rural roads are efficient
    }
    
    # Traffic impact (eco-driving helps more in traffic)
    traffic_multipliers = {
        'light': 1.0,
        'normal': 1.1,     # More benefit in normal traffic
        'heavy': 1.2       # Significant benefit in heavy traffic
    }
    
    adjusted_efficiency = (base_efficiency * efficiency_multiplier * 
                          route_multipliers.get(route_type, 1.0) * 
                          traffic_multipliers.get(traffic, 1.0))
    
    fuel_consumption = distance / adjusted_efficiency
    fuel_cost = fuel_consumption * 110  # ₹110 per liter
    
    return {
        'scenario': 'eco_driving',
        'name': 'Eco-Friendly Driving',
        'description': 'Optimal fuel efficiency with gentle acceleration and steady speeds',
        'fuel_consumption_liters': round(fuel_consumption, 2),
        'fuel_cost_inr': round(fuel_cost, 2),
        'efficiency_kmpl': round(adjusted_efficiency, 1),
        'avg_speed_kmph': 55,
        'driving_characteristics': [
            'Gentle acceleration (0-60 in 15+ seconds)',
            'Steady speeds between 50-70 km/h',
            'Anticipatory braking',
            'Optimal gear shifting'
        ],
        'time_impact': '+8-12 minutes',
        'co2_emissions_kg': round(fuel_consumption * 2.31, 2),
        'efficiency_rating': 'A+',
        'savings_vs_normal': 0  # Will be calculated later
    }

def _calculate_normal_scenario(distance: float, route_type: str, traffic: str,
                              base_efficiency: float, vehicle_data: Dict) -> Dict:
    """Calculate normal driving fuel consumption"""
    
    # Route type adjustments
    route_multipliers = {
        'highway': 1.05,
        'city': 0.85,
        'mixed': 1.0,
        'rural': 1.0
    }
    
    # Traffic impact
    traffic_multipliers = {
        'light': 1.1,
        'normal': 1.0,
        'heavy': 0.8  # Lower efficiency in heavy traffic
    }
    
    adjusted_efficiency = (base_efficiency * 
                          route_multipliers.get(route_type, 1.0) * 
                          traffic_multipliers.get(traffic, 1.0))
    
    fuel_consumption = distance / adjusted_efficiency
    fuel_cost = fuel_consumption * 110
    
    return {
        'scenario': 'normal_driving',
        'name': 'Normal Driving',
        'description': 'Balanced driving style with moderate acceleration and speeds',
        'fuel_consumption_liters': round(fuel_consumption, 2),
        'fuel_cost_inr': round(fuel_cost, 2),
        'efficiency_kmpl': round(adjusted_efficiency, 1),
        'avg_speed_kmph': 65,
        'driving_characteristics': [
            'Moderate acceleration',
            'Variable speeds 60-80 km/h',
            'Normal braking patterns',
            'Standard gear usage'
        ],
        'time_impact': 'Baseline',
        'co2_emissions_kg': round(fuel_consumption * 2.31, 2),
        'efficiency_rating': 'B',
        'savings_vs_normal': 0
    }

def _calculate_aggressive_scenario(distance: float, route_type: str, traffic: str,
                                  base_efficiency: float, vehicle_data: Dict) -> Dict:
    """Calculate aggressive driving fuel consumption"""
    
    # Aggressive driving penalty
    efficiency_multiplier = 0.7  # 30% worse efficiency
    
    # Route type adjustments
    route_multipliers = {
        'highway': 0.8,    # High speeds hurt highway efficiency
        'city': 0.75,      # Stop-and-go aggressive driving is very inefficient
        'mixed': 0.8,
        'rural': 0.85
    }
    
    # Traffic impact (aggressive driving worse in all conditions)
    traffic_multipliers = {
        'light': 0.9,
        'normal': 0.8,
        'heavy': 0.7  # Very inefficient in heavy traffic
    }
    
    adjusted_efficiency = (base_efficiency * efficiency_multiplier * 
                          route_multipliers.get(route_type, 1.0) * 
                          traffic_multipliers.get(traffic, 1.0))
    
    fuel_consumption = distance / adjusted_efficiency
    fuel_cost = fuel_consumption * 110
    
    return {
        'scenario': 'aggressive_driving',
        'name': 'Aggressive Driving',
        'description': 'Fast acceleration, high speeds, and frequent braking',
        'fuel_consumption_liters': round(fuel_consumption, 2),
        'fuel_cost_inr': round(fuel_cost, 2),
        'efficiency_kmpl': round(adjusted_efficiency, 1),
        'avg_speed_kmph': 75,
        'driving_characteristics': [
            'Rapid acceleration (0-60 in <8 seconds)',
            'High speeds 80-100+ km/h',
            'Frequent hard braking',
            'High RPM operation'
        ],
        'time_impact': '-5-8 minutes',
        'co2_emissions_kg': round(fuel_consumption * 2.31, 2),
        'efficiency_rating': 'D',
        'savings_vs_normal': 0
    }

def _calculate_sport_scenario(distance: float, route_type: str, traffic: str,
                             base_efficiency: float, vehicle_data: Dict) -> Dict:
    """Calculate sport/performance driving fuel consumption"""
    
    # Sport driving penalty
    efficiency_multiplier = 0.6  # 40% worse efficiency
    
    adjusted_efficiency = base_efficiency * efficiency_multiplier * 0.8  # Additional penalty
    fuel_consumption = distance / adjusted_efficiency
    fuel_cost = fuel_consumption * 110
    
    return {
        'scenario': 'sport_driving',
        'name': 'Sport/Performance',
        'description': 'Maximum performance with high RPM and aggressive acceleration',
        'fuel_consumption_liters': round(fuel_consumption, 2),
        'fuel_cost_inr': round(fuel_cost, 2),
        'efficiency_kmpl': round(adjusted_efficiency, 1),
        'avg_speed_kmph': 85,
        'driving_characteristics': [
            'Maximum acceleration',
            'High RPM (3500+ RPM)',
            'Performance-oriented speeds',
            'Sport mode engaged'
        ],
        'time_impact': '-10-15 minutes',
        'co2_emissions_kg': round(fuel_consumption * 2.31, 2),
        'efficiency_rating': 'F',
        'savings_vs_normal': 0
    }

def _calculate_cost_analysis(scenarios: List[Dict]) -> Dict:
    """Calculate cost analysis across scenarios"""
    
    normal_cost = next(s['fuel_cost_inr'] for s in scenarios if s['scenario'] == 'normal_driving')
    
    # Calculate savings/costs relative to normal driving
    for scenario in scenarios:
        scenario['savings_vs_normal'] = round(normal_cost - scenario['fuel_cost_inr'], 2)
    
    # Find best and worst scenarios
    best_scenario = min(scenarios, key=lambda x: x['fuel_cost_inr'])
    worst_scenario = max(scenarios, key=lambda x: x['fuel_cost_inr'])
    
    max_savings = worst_scenario['fuel_cost_inr'] - best_scenario['fuel_cost_inr']
    
    return {
        'baseline_cost': normal_cost,
        'best_case_cost': best_scenario['fuel_cost_inr'],
        'worst_case_cost': worst_scenario['fuel_cost_inr'],
        'max_potential_savings': round(max_savings, 2),
        'monthly_savings_potential': round(max_savings * 20, 2),  # Assuming 20 trips/month
        'annual_savings_potential': round(max_savings * 240, 2),  # Assuming 240 trips/year
        'best_scenario_name': best_scenario['name'],
        'cost_range': {
            'min': best_scenario['fuel_cost_inr'],
            'max': worst_scenario['fuel_cost_inr']
        }
    }

def _generate_optimization_tips(scenarios: List[Dict], user_profile: Dict) -> List[Dict]:
    """Generate fuel optimization tips based on scenarios"""
    
    tips = []
    
    eco_scenario = next(s for s in scenarios if s['scenario'] == 'eco_driving')
    normal_scenario = next(s for s in scenarios if s['scenario'] == 'normal_driving')
    
    potential_savings = normal_scenario['fuel_cost_inr'] - eco_scenario['fuel_cost_inr']
    
    if potential_savings > 20:
        tips.append({
            'category': 'driving_style',
            'title': 'Switch to Eco-Driving',
            'description': f'Save ₹{potential_savings:.0f} per trip with eco-friendly driving',
            'impact': 'high',
            'difficulty': 'medium',
            'steps': [
                'Accelerate gradually (15+ seconds to 60 km/h)',
                'Maintain steady speeds between 50-70 km/h',
                'Anticipate traffic and coast to stops',
                'Use cruise control on highways'
            ]
        })
    
    tips.append({
        'category': 'route_planning',
        'title': 'Optimize Route Timing',
        'description': 'Choose travel times to avoid heavy traffic',
        'impact': 'medium',
        'difficulty': 'easy',
        'steps': [
            'Avoid rush hours (7-9 AM, 5-7 PM)',
            'Use traffic apps for real-time updates',
            'Consider alternative routes',
            'Combine multiple errands in one trip'
        ]
    })
    
    tips.append({
        'category': 'vehicle_maintenance',
        'title': 'Maintain Vehicle Efficiency',
        'description': 'Keep your vehicle in optimal condition',
        'impact': 'medium',
        'difficulty': 'easy',
        'steps': [
            'Check tire pressure monthly',
            'Replace air filter every 15,000 km',
            'Use recommended engine oil grade',
            'Remove unnecessary weight from vehicle'
        ]
    })
    
    return tips

def _find_best_scenario(scenarios: List[Dict]) -> Dict:
    """Find the most recommended scenario based on efficiency and practicality"""
    
    # Score each scenario
    for scenario in scenarios:
        score = 0
        
        # Efficiency score (40% weight)
        if scenario['efficiency_rating'] == 'A+':
            score += 40
        elif scenario['efficiency_rating'] == 'B':
            score += 30
        elif scenario['efficiency_rating'] == 'C':
            score += 20
        else:
            score += 10
        
        # Practicality score (30% weight)
        if 'eco' in scenario['scenario']:
            score += 25  # Eco is practical for most
        elif 'normal' in scenario['scenario']:
            score += 30  # Normal is most practical
        else:
            score += 10  # Aggressive/sport less practical
        
        # Cost savings score (30% weight)
        savings = scenario.get('savings_vs_normal', 0)
        if savings > 0:
            score += min(30, savings)  # Cap at 30 points
        
        scenario['recommendation_score'] = score
    
    return max(scenarios, key=lambda x: x['recommendation_score'])

def _analyze_route_factors(route_data: Dict) -> Dict:
    """Analyze factors that affect fuel consumption on this route"""
    
    factors = {
        'distance_impact': 'medium',
        'route_type_impact': 'high',
        'traffic_impact': 'high',
        'elevation_impact': 'low',  # Placeholder
        'weather_impact': 'medium'
    }
    
    distance = route_data.get('distance_km', 0)
    route_type = route_data.get('route_type', 'mixed')
    
    # Distance impact
    if distance > 100:
        factors['distance_impact'] = 'high'
        factors['distance_note'] = 'Long distance - highway efficiency important'
    elif distance < 20:
        factors['distance_impact'] = 'low'
        factors['distance_note'] = 'Short distance - city efficiency matters'
    
    # Route type impact
    if route_type == 'highway':
        factors['route_type_note'] = 'Highway driving - steady speeds optimal'
    elif route_type == 'city':
        factors['route_type_note'] = 'City driving - stop-and-go patterns'
    
    return factors

def _calculate_prediction_confidence(user_profile: Dict, vehicle_data: Dict) -> int:
    """Calculate confidence level of predictions (0-100)"""
    
    confidence = 70  # Base confidence
    
    # User profile completeness
    if user_profile.get('avg_efficiency'):
        confidence += 10
    if user_profile.get('driving_style'):
        confidence += 5
    if user_profile.get('trip_history'):
        confidence += 10
    
    # Vehicle data completeness
    if vehicle_data.get('engine_size'):
        confidence += 5
    if vehicle_data.get('vehicle_type'):
        confidence += 5
    if vehicle_data.get('age_years'):
        confidence += 5
    
    return min(95, confidence)  # Cap at 95%