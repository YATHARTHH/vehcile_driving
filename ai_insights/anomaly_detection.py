import math
from typing import Dict, List, Tuple
from datetime import datetime

def detect_anomalies(trip_data: Dict, user_history: List[Dict] = None) -> Dict:
    """Detect driving anomalies using statistical analysis"""
    
    anomalies = []
    
    # Speed anomalies
    speed_anomalies = _detect_speed_anomalies(trip_data, user_history)
    anomalies.extend(speed_anomalies)
    
    # RPM anomalies
    rpm_anomalies = _detect_rpm_anomalies(trip_data, user_history)
    anomalies.extend(rpm_anomalies)
    
    # Braking anomalies
    brake_anomalies = _detect_brake_anomalies(trip_data, user_history)
    anomalies.extend(brake_anomalies)
    
    # Fuel consumption anomalies
    fuel_anomalies = _detect_fuel_anomalies(trip_data, user_history)
    anomalies.extend(fuel_anomalies)
    
    # Calculate overall risk score
    risk_score = _calculate_risk_score(anomalies)
    
    return {
        'anomalies': anomalies,
        'total_count': len(anomalies),
        'risk_score': risk_score,
        'severity_breakdown': _get_severity_breakdown(anomalies),
        'recommendations': _generate_anomaly_recommendations(anomalies),
        'timestamp': datetime.now().isoformat()
    }

def _detect_speed_anomalies(trip_data: Dict, history: List[Dict]) -> List[Dict]:
    """Detect speed-related anomalies"""
    anomalies = []
    current_speed = trip_data.get('avg_speed_kmph', 0)
    max_speed = trip_data.get('max_speed', 0)
    
    # Historical baseline
    if history:
        historical_speeds = [t.get('avg_speed_kmph', 0) for t in history[-10:] if t.get('avg_speed_kmph')]
        if historical_speeds:
            avg_historical = sum(historical_speeds) / len(historical_speeds)
            speed_deviation = abs(current_speed - avg_historical) / avg_historical if avg_historical > 0 else 0
            
            if speed_deviation > 0.3:  # 30% deviation
                anomalies.append({
                    'type': 'speed_deviation',
                    'severity': 'high' if speed_deviation > 0.5 else 'medium',
                    'description': f'Speed {current_speed:.1f} km/h deviates {speed_deviation*100:.1f}% from normal',
                    'value': current_speed,
                    'baseline': avg_historical,
                    'recommendation': 'Monitor driving conditions and adjust speed accordingly'
                })
    
    # Absolute speed thresholds
    if max_speed > 120:
        anomalies.append({
            'type': 'excessive_speed',
            'severity': 'high',
            'description': f'Maximum speed of {max_speed} km/h exceeds safe limits',
            'value': max_speed,
            'recommendation': 'Reduce speed for safety and fuel efficiency'
        })
    
    return anomalies

def _detect_rpm_anomalies(trip_data: Dict, history: List[Dict]) -> List[Dict]:
    """Detect RPM-related anomalies"""
    anomalies = []
    max_rpm = trip_data.get('max_rpm', 0)
    
    # High RPM detection
    if max_rpm > 4500:
        anomalies.append({
            'type': 'excessive_rpm',
            'severity': 'high',
            'description': f'Maximum RPM of {max_rpm} indicates engine stress',
            'value': max_rpm,
            'recommendation': 'Shift gears earlier or reduce acceleration intensity'
        })
    elif max_rpm > 3500:
        anomalies.append({
            'type': 'high_rpm',
            'severity': 'medium',
            'description': f'RPM of {max_rpm} is higher than optimal range',
            'value': max_rpm,
            'recommendation': 'Consider gentler acceleration for better efficiency'
        })
    
    # Historical comparison
    if history:
        historical_rpms = [t.get('max_rpm', 0) for t in history[-10:] if t.get('max_rpm')]
        if historical_rpms:
            avg_historical = sum(historical_rpms) / len(historical_rpms)
            if max_rpm > avg_historical * 1.4:
                anomalies.append({
                    'type': 'rpm_spike',
                    'severity': 'medium',
                    'description': f'RPM spike detected: {max_rpm} vs normal {avg_historical:.0f}',
                    'value': max_rpm,
                    'baseline': avg_historical,
                    'recommendation': 'Check for mechanical issues or driving style changes'
                })
    
    return anomalies

def _detect_brake_anomalies(trip_data: Dict, history: List[Dict]) -> List[Dict]:
    """Detect braking pattern anomalies"""
    anomalies = []
    brake_events = trip_data.get('brake_events', 0)
    distance = trip_data.get('distance_km', 1)
    brake_rate = brake_events / distance
    
    # High braking frequency
    if brake_rate > 8:
        anomalies.append({
            'type': 'excessive_braking',
            'severity': 'high',
            'description': f'{brake_events} brake events in {distance:.1f}km indicates aggressive driving',
            'value': brake_rate,
            'recommendation': 'Increase following distance and anticipate traffic flow'
        })
    elif brake_rate > 5:
        anomalies.append({
            'type': 'frequent_braking',
            'severity': 'medium',
            'description': f'High braking frequency: {brake_rate:.1f} events per km',
            'value': brake_rate,
            'recommendation': 'Practice smoother driving techniques'
        })
    
    return anomalies

def _detect_fuel_anomalies(trip_data: Dict, history: List[Dict]) -> List[Dict]:
    """Detect fuel consumption anomalies"""
    anomalies = []
    fuel_consumed = trip_data.get('fuel_consumed', 0)
    distance = trip_data.get('distance_km', 1)
    
    if fuel_consumed > 0 and distance > 0:
        fuel_efficiency = distance / fuel_consumed
        
        # Poor fuel efficiency
        if fuel_efficiency < 8:
            anomalies.append({
                'type': 'poor_fuel_efficiency',
                'severity': 'high',
                'description': f'Fuel efficiency of {fuel_efficiency:.1f} km/L is below optimal',
                'value': fuel_efficiency,
                'recommendation': 'Check driving style, tire pressure, and vehicle maintenance'
            })
        
        # Historical comparison
        if history:
            historical_efficiencies = []
            for trip in history[-10:]:
                if trip.get('fuel_consumed', 0) > 0 and trip.get('distance_km', 0) > 0:
                    eff = trip['distance_km'] / trip['fuel_consumed']
                    historical_efficiencies.append(eff)
            
            if historical_efficiencies:
                avg_efficiency = sum(historical_efficiencies) / len(historical_efficiencies)
                if fuel_efficiency < avg_efficiency * 0.7:
                    anomalies.append({
                        'type': 'fuel_efficiency_drop',
                        'severity': 'medium',
                        'description': f'Fuel efficiency dropped to {fuel_efficiency:.1f} from normal {avg_efficiency:.1f} km/L',
                        'value': fuel_efficiency,
                        'baseline': avg_efficiency,
                        'recommendation': 'Investigate potential mechanical issues or route changes'
                    })
    
    return anomalies

def _calculate_risk_score(anomalies: List[Dict]) -> int:
    """Calculate overall risk score based on anomalies"""
    if not anomalies:
        return 0
    
    severity_weights = {'low': 1, 'medium': 3, 'high': 5}
    total_weight = sum(severity_weights.get(a.get('severity', 'low'), 1) for a in anomalies)
    
    # Normalize to 0-100 scale
    risk_score = min(100, total_weight * 10)
    return risk_score

def _get_severity_breakdown(anomalies: List[Dict]) -> Dict:
    """Get breakdown of anomalies by severity"""
    breakdown = {'low': 0, 'medium': 0, 'high': 0}
    for anomaly in anomalies:
        severity = anomaly.get('severity', 'low')
        breakdown[severity] += 1
    return breakdown

def _generate_anomaly_recommendations(anomalies: List[Dict]) -> List[str]:
    """Generate prioritized recommendations based on detected anomalies"""
    recommendations = []
    
    # High priority recommendations
    high_severity = [a for a in anomalies if a.get('severity') == 'high']
    if high_severity:
        recommendations.append("🚨 Immediate attention required for high-severity issues")
        for anomaly in high_severity[:2]:  # Top 2 high severity
            recommendations.append(f"• {anomaly.get('recommendation', 'Review driving patterns')}")
    
    # Medium priority
    medium_severity = [a for a in anomalies if a.get('severity') == 'medium']
    if medium_severity:
        recommendations.append("⚠️ Monitor and improve these areas:")
        for anomaly in medium_severity[:2]:  # Top 2 medium severity
            recommendations.append(f"• {anomaly.get('recommendation', 'Monitor patterns')}")
    
    # General recommendations
    if len(anomalies) > 3:
        recommendations.append("📊 Consider comprehensive driving assessment")
    
    return recommendations[:6]  # Limit to 6 recommendations