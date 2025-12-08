import random
from typing import Dict, List
from datetime import datetime

def analyze_trip_sentiment(trip_data: Dict) -> Dict:
    """Analyze driving sentiment using trip patterns"""
    
    # Extract key metrics
    avg_speed = trip_data.get('avg_speed_kmph', 0)
    brake_events = trip_data.get('brake_events', 0)
    max_rpm = trip_data.get('max_rpm', 0)
    acceleration = trip_data.get('acceleration', 0)
    distance = trip_data.get('distance_km', 0)
    
    # Calculate sentiment score (0-100)
    sentiment_score = 70  # Base neutral score
    
    # Speed consistency factor
    if 50 <= avg_speed <= 80:
        sentiment_score += 15
    elif avg_speed > 100:
        sentiment_score -= 20
    elif avg_speed < 30:
        sentiment_score -= 10
    
    # Braking pattern analysis
    brake_rate = brake_events / max(distance, 1)
    if brake_rate < 2:
        sentiment_score += 10
    elif brake_rate > 5:
        sentiment_score -= 15
    
    # RPM stress indicator
    if max_rpm > 4000:
        sentiment_score -= 12
    elif max_rpm < 2500:
        sentiment_score += 8
    
    # Acceleration smoothness
    if abs(acceleration) < 2:
        sentiment_score += 8
    elif abs(acceleration) > 4:
        sentiment_score -= 10
    
    sentiment_score = max(0, min(100, sentiment_score))
    
    # Determine sentiment category
    if sentiment_score >= 80:
        sentiment = "positive"
        emotion = "relaxed"
        description = "Calm and controlled driving"
    elif sentiment_score >= 60:
        sentiment = "neutral"
        emotion = "focused"
        description = "Steady driving with minor variations"
    else:
        sentiment = "negative"
        emotion = "stressed"
        description = "Aggressive or erratic driving patterns"
    
    # Generate insights
    insights = []
    if brake_events > distance * 3:
        insights.append("High braking frequency suggests traffic or aggressive driving")
    if max_rpm > 3500:
        insights.append("High RPM indicates potential engine stress")
    if avg_speed > 90:
        insights.append("High speed driving detected - consider safety")
    
    return {
        'sentiment': sentiment,
        'emotion': emotion,
        'score': sentiment_score,
        'confidence': min(95, 60 + (abs(sentiment_score - 50) * 0.7)),
        'description': description,
        'insights': insights,
        'tags': _generate_sentiment_tags(sentiment_score, trip_data),
        'timestamp': datetime.now().isoformat()
    }

def _generate_sentiment_tags(score: int, trip_data: Dict) -> List[str]:
    """Generate descriptive tags based on sentiment analysis"""
    tags = []
    
    if score >= 80:
        tags.extend(['smooth', 'efficient', 'controlled'])
    elif score >= 60:
        tags.extend(['steady', 'consistent'])
    else:
        tags.extend(['erratic', 'aggressive'])
    
    # Add specific behavior tags
    if trip_data.get('brake_events', 0) > trip_data.get('distance_km', 1) * 4:
        tags.append('frequent-braking')
    if trip_data.get('max_rpm', 0) > 3500:
        tags.append('high-rpm')
    if trip_data.get('avg_speed_kmph', 0) > 85:
        tags.append('high-speed')
    
    return tags

def get_sentiment_trends(trip_history: List[Dict]) -> Dict:
    """Analyze sentiment trends over multiple trips"""
    if not trip_history:
        return {'trend': 'insufficient_data', 'improvement': 0}
    
    sentiments = [analyze_trip_sentiment(trip)['score'] for trip in trip_history[-10:]]
    
    if len(sentiments) < 3:
        return {'trend': 'insufficient_data', 'improvement': 0}
    
    recent_avg = sum(sentiments[-3:]) / 3
    older_avg = sum(sentiments[:-3]) / len(sentiments[:-3])
    
    improvement = recent_avg - older_avg
    
    if improvement > 5:
        trend = 'improving'
    elif improvement < -5:
        trend = 'declining'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'improvement': round(improvement, 1),
        'current_avg': round(recent_avg, 1),
        'historical_avg': round(older_avg, 1)
    }