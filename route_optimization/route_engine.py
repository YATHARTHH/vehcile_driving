import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class RouteOptimizer:
    """Advanced route optimization engine with multiple algorithms and real-time features"""
    
    def __init__(self):
        self.fuel_price_per_liter = 110.0  # Indian Rupees per liter
        self.traffic_patterns = self._initialize_traffic_patterns()
        
    def _initialize_traffic_patterns(self) -> Dict:
        """Initialize traffic patterns for different times and road types"""
        return {
            'rush_hours': [(7, 9), (17, 19)],  # Morning and evening rush
            'weekend_factor': 0.7,  # Less traffic on weekends
            'highway_speed_factor': 1.2,  # Highways are generally faster
            'city_congestion_factor': 0.6,  # City roads are slower
            'weather_impact': {
                'rain': 0.8,
                'snow': 0.5,
                'clear': 1.0
            }
        }
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def calculate_fuel_consumption(self, distance_km: float, route_type: str, 
                                 user_efficiency: float = 15.0, vehicle_data: Dict = None) -> float:
        """Calculate personalized fuel consumption based on route type and user data"""
        base_consumption = distance_km / user_efficiency
        
        # Route type multipliers
        route_multipliers = {
            'direct': 1.0,
            'eco': 0.85,  # 15% more efficient
            'fastest': 1.15,  # Highway driving uses more fuel
            'scenic': 1.1
        }
        
        # Apply route type multiplier
        consumption = base_consumption * route_multipliers.get(route_type, 1.0)
        
        # Apply vehicle-specific adjustments if available
        if vehicle_data:
            engine_load_factor = vehicle_data.get('avg_engine_load', 50) / 50
            consumption *= (0.8 + 0.4 * engine_load_factor)
        
        return round(max(consumption, 0.1), 2)  # Minimum 0.1L consumption
    
    def simulate_traffic_conditions(self, route_type: str, departure_time: datetime = None) -> Dict:
        """Simulate real-time traffic conditions with intelligent patterns"""
        if not departure_time:
            departure_time = datetime.now()
        
        hour = departure_time.hour
        is_weekend = departure_time.weekday() >= 5
        
        # Base traffic level
        traffic_level = 'light'
        delay_factor = 1.0
        
        # Rush hour detection
        is_rush_hour = any(start <= hour < end for start, end in self.traffic_patterns['rush_hours'])
        
        if is_rush_hour and not is_weekend:
            if route_type == 'fastest':  # Highway routes more congested in rush hour
                traffic_level = 'heavy'
                delay_factor = 1.6
            elif route_type == 'direct':  # Main roads moderately affected
                traffic_level = 'moderate'
                delay_factor = 1.3
            else:  # Eco routes use back roads, less affected
                traffic_level = 'light'
                delay_factor = 1.1
        elif is_weekend:
            delay_factor *= self.traffic_patterns['weekend_factor']
            if route_type == 'fastest':  # Highways still faster on weekends
                delay_factor *= 0.8
        else:
            # Off-peak hours
            if route_type == 'fastest':  # Highways are fastest during off-peak
                delay_factor = 0.8
            elif route_type == 'eco':  # Back roads may be slower
                delay_factor = 1.1
        
        # Add some randomness for realism
        delay_factor *= random.uniform(0.9, 1.1)
        
        return {
            'level': traffic_level,
            'delay_factor': delay_factor,
            'congestion_points': self._generate_congestion_points(traffic_level),
            'estimated_delay_minutes': round(max(0, (delay_factor - 1) * 30))
        }
    
    def _generate_congestion_points(self, traffic_level: str) -> List[str]:
        """Generate realistic congestion points based on traffic level"""
        congestion_points = []
        
        if traffic_level == 'heavy':
            congestion_points = [
                "City Center Junction",
                "Highway Merge Point",
                "Shopping District",
                "School Zone"
            ]
        elif traffic_level == 'moderate':
            congestion_points = [
                "Main Street Intersection",
                "Bridge Crossing"
            ]
        
        return congestion_points
    
    def calculate_efficiency_score(self, route_data: Dict) -> int:
        """Calculate efficiency score (0-100) based on multiple factors"""
        # Base score varies by route type
        route_type = route_data.get('type', 'direct')
        if route_type == 'eco':
            score = 85
        elif route_type == 'direct':
            score = 75
        else:  # fastest
            score = 65
        
        # Distance-based efficiency (25% weight)
        distance = route_data.get('distance_km', 50)
        fuel_consumption = route_data.get('fuel_consumption', 5)
        fuel_efficiency = distance / fuel_consumption if fuel_consumption > 0 else 15
        
        if fuel_efficiency > 18:
            score += 10
        elif fuel_efficiency > 15:
            score += 5
        elif fuel_efficiency < 10:
            score -= 10
        
        # Time vs distance efficiency (25% weight)
        travel_time = route_data.get('travel_time_minutes', 60)
        time_efficiency = distance / (travel_time / 60) if travel_time > 0 else 50  # km/h
        
        if time_efficiency > 60:
            score += 8
        elif time_efficiency > 40:
            score += 5
        elif time_efficiency < 25:
            score -= 8
        
        # Traffic impact (20% weight)
        traffic_delay = route_data.get('traffic_delay_minutes', 0)
        if traffic_delay == 0:
            score += 8
        elif traffic_delay < 5:
            score += 4
        elif traffic_delay > 15:
            score -= 12
        
        # Route optimization (15% weight)
        route_type = route_data.get('type', 'direct')
        if route_type == 'eco':
            score += 6  # Bonus for eco-friendly
        elif route_type == 'fastest' and traffic_delay < 5:
            score += 4  # Bonus for fastest only if low traffic
        
        # Cost efficiency (15% weight)
        fuel_cost = route_data.get('fuel_cost', 100)
        if fuel_cost < 50:
            score += 6
        elif fuel_cost < 100:
            score += 3
        elif fuel_cost > 200:
            score -= 6
        
        return max(0, min(100, score))
    
    def optimize_routes(self, start_coords: Tuple[float, float], end_coords: Tuple[float, float],
                       user_preferences: Dict = None, user_vehicle_data: Dict = None) -> List[Dict]:
        """Generate optimized route options with comprehensive analysis"""
        
        if not user_preferences:
            user_preferences = {'priority': 'balanced', 'fuel_efficiency': 8.0}
        
        base_distance = self.haversine_distance(
            start_coords[0], start_coords[1], end_coords[0], end_coords[1]
        )
        
        routes = []
        
        # Route 1: Direct/Balanced Route
        direct_route = self._generate_direct_route(
            base_distance, start_coords, end_coords, user_preferences, user_vehicle_data
        )
        routes.append(direct_route)
        
        # Route 2: Eco-Friendly Route
        eco_route = self._generate_eco_route(
            base_distance, start_coords, end_coords, user_preferences, user_vehicle_data
        )
        routes.append(eco_route)
        
        # Route 3: Fastest Route
        fastest_route = self._generate_fastest_route(
            base_distance, start_coords, end_coords, user_preferences, user_vehicle_data
        )
        routes.append(fastest_route)
        
        # Sort by efficiency score
        routes.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
        return routes
    
    def _generate_direct_route(self, base_distance: float, start_coords: Tuple, end_coords: Tuple,
                              user_prefs: Dict, vehicle_data: Dict) -> Dict:
        """Generate direct/balanced route option"""
        distance = base_distance * random.uniform(1.0, 1.1)  # Slight variation for realism
        
        traffic_info = self.simulate_traffic_conditions('direct')
        base_time = (distance / 50) * 60  # Assume 50 km/h average
        travel_time = base_time * traffic_info['delay_factor']
        
        fuel_consumption = self.calculate_fuel_consumption(
            distance, 'direct', user_prefs.get('fuel_efficiency', 15.0), vehicle_data
        )
        
        route_data = {
            'type': 'direct',
            'name': 'Direct Route',
            'description': 'Balanced route with optimal distance and time',
            'distance_km': round(distance, 1),
            'travel_time_minutes': round(travel_time, 0),
            'fuel_consumption': fuel_consumption,
            'fuel_cost': round(fuel_consumption * self.fuel_price_per_liter, 2),
            'traffic_info': traffic_info,
            'traffic_delay_minutes': traffic_info['estimated_delay_minutes'],
            'route_highlights': ['Main roads', 'Balanced traffic', 'Direct path'],
            'coordinates': [start_coords, end_coords]
        }
        
        route_data['efficiency_score'] = self.calculate_efficiency_score(route_data)
        return route_data
    
    def _generate_eco_route(self, base_distance: float, start_coords: Tuple, end_coords: Tuple,
                           user_prefs: Dict, vehicle_data: Dict) -> Dict:
        """Generate eco-friendly route option"""
        distance = base_distance * random.uniform(1.15, 1.25)  # Longer but more efficient
        
        traffic_info = self.simulate_traffic_conditions('eco')
        base_time = (distance / 45) * 60  # Slower average speed
        travel_time = base_time * traffic_info['delay_factor']
        
        fuel_consumption = self.calculate_fuel_consumption(
            distance, 'eco', user_prefs.get('fuel_efficiency', 15.0), vehicle_data
        )
        
        route_data = {
            'type': 'eco',
            'name': 'Eco-Friendly Route',
            'description': '15% more fuel efficient with minimal stops',
            'distance_km': round(distance, 1),
            'travel_time_minutes': round(travel_time, 0),
            'fuel_consumption': fuel_consumption,
            'fuel_cost': round(fuel_consumption * self.fuel_price_per_liter, 2),
            'traffic_info': traffic_info,
            'traffic_delay_minutes': traffic_info['estimated_delay_minutes'],
            'route_highlights': ['Scenic roads', 'Fewer traffic lights', 'Optimal elevation'],
            'coordinates': [start_coords, end_coords],
            'eco_benefits': {
                'fuel_savings_percent': 15,
                'co2_reduction_kg': round(fuel_consumption * 0.15 * 2.31, 2)
            }
        }
        
        route_data['efficiency_score'] = self.calculate_efficiency_score(route_data)
        return route_data
    
    def _generate_fastest_route(self, base_distance: float, start_coords: Tuple, end_coords: Tuple,
                               user_prefs: Dict, vehicle_data: Dict) -> Dict:
        """Generate fastest route option"""
        distance = base_distance * random.uniform(1.05, 1.15)  # Slightly longer for highways
        
        traffic_info = self.simulate_traffic_conditions('fastest')
        base_time = (distance / 70) * 60  # Higher average speed on highways
        travel_time = base_time * traffic_info['delay_factor']
        
        fuel_consumption = self.calculate_fuel_consumption(
            distance, 'fastest', user_prefs.get('fuel_efficiency', 15.0), vehicle_data
        )
        
        route_data = {
            'type': 'fastest',
            'name': 'Fastest Route',
            'description': 'Highway-preferred route for time optimization',
            'distance_km': round(distance, 1),
            'travel_time_minutes': round(travel_time, 0),
            'fuel_consumption': fuel_consumption,
            'fuel_cost': round(fuel_consumption * self.fuel_price_per_liter, 2),
            'traffic_info': traffic_info,
            'traffic_delay_minutes': traffic_info['estimated_delay_minutes'],
            'route_highlights': ['Highway access', 'High-speed roads', 'Minimal intersections'],
            'coordinates': [start_coords, end_coords],
            'time_savings_minutes': max(0, 45 - travel_time)
        }
        
        route_data['efficiency_score'] = self.calculate_efficiency_score(route_data)
        return route_data
    
    def get_personalized_recommendations(self, routes: List[Dict], user_history: Dict = None) -> Dict:
        """Generate personalized recommendations based on user driving history"""
        if not user_history:
            user_history = {'avg_fuel_efficiency': 8.0, 'preferred_route_type': 'balanced'}
        
        recommendations = {
            'primary_recommendation': None,
            'reasons': [],
            'savings_analysis': {},
            'tips': []
        }
        
        # Analyze user's historical preferences
        avg_efficiency = user_history.get('avg_fuel_efficiency', 8.0)
        preferred_type = user_history.get('preferred_route_type', 'balanced')
        
        # Find best route based on user profile
        if avg_efficiency < 7.0:  # User has poor fuel efficiency
            eco_route = next((r for r in routes if r['type'] == 'eco'), None)
            if eco_route:
                recommendations['primary_recommendation'] = {'name': eco_route['name'], 'type': eco_route['type']}
                recommendations['reasons'].append("Eco-friendly route recommended to improve fuel efficiency")
        else:
            # Recommend based on efficiency score
            recommendations['primary_recommendation'] = {'name': routes[0]['name'], 'type': routes[0]['type']}
            recommendations['reasons'].append("Best overall efficiency for your driving profile")
        
        # Calculate savings analysis
        if len(routes) >= 2:
            best_route = routes[0]
            worst_route = routes[-1]
            
            fuel_savings = worst_route['fuel_cost'] - best_route['fuel_cost']
            time_difference = worst_route['travel_time_minutes'] - best_route['travel_time_minutes']
            
            recommendations['savings_analysis'] = {
                'potential_fuel_savings': round(fuel_savings, 2),
                'time_difference_minutes': round(time_difference, 0),
                'monthly_savings_estimate': round(fuel_savings * 20, 2)  # Assuming 20 trips per month
            }
        
        # Generate personalized tips
        recommendations['tips'] = [
            "Maintain steady speed to improve fuel efficiency",
            "Plan trips during off-peak hours when possible",
            "Keep tires properly inflated for better mileage",
            "Use cruise control on highways for consistent speed"
        ]
        
        return recommendations

def geocode_location(location_name: str) -> Optional[Tuple[float, float]]:
    """Simple geocoding simulation - in production, use a real geocoding service"""
    # This is a simplified version - in production, integrate with Google Maps API, OpenStreetMap, etc.
    sample_locations = {
        'new york': (40.7128, -74.0060),
        'los angeles': (34.0522, -118.2437),
        'chicago': (41.8781, -87.6298),
        'houston': (29.7604, -95.3698),
        'phoenix': (33.4484, -112.0740),
        'philadelphia': (39.9526, -75.1652),
        'san antonio': (29.4241, -98.4936),
        'san diego': (32.7157, -117.1611),
        'dallas': (32.7767, -96.7970),
        'san jose': (37.3382, -121.8863),
        'mumbai': (19.0760, 72.8777),
        'delhi': (28.7041, 77.1025),
        'bangalore': (12.9716, 77.5946),
        'hyderabad': (17.3850, 78.4867),
        'chennai': (13.0827, 80.2707),
        'kolkata': (22.5726, 88.3639),
        'pune': (18.5204, 73.8567),
        'ahmedabad': (23.0225, 72.5714)
    }
    
    location_lower = location_name.lower().strip()
    return sample_locations.get(location_lower)