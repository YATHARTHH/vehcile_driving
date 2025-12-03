import re
import random
from datetime import datetime, timedelta

class VehicleChatbot:
    def __init__(self):
        self.session_memory = {}
        self.responses = {
            'greeting': [
                "Hello! I'm your vehicle assistant. How can I help you today?",
                "Hi there! I can help you with driving tips and vehicle data analysis.",
                "Welcome! Ask me about your driving performance or vehicle maintenance.",
                "Good day! Ready to optimize your driving experience?",
                "Hey! I'm here to help with all your vehicle questions."
            ],
            'driving_tips': [
                "🚗 Eco-driving tips:\n• Maintain steady speeds (50-80 km/h is optimal)\n• Avoid rapid acceleration and hard braking\n• Keep tires properly inflated\n• Remove excess weight from your vehicle",
                "🛣️ Highway driving tips:\n• Use cruise control when possible\n• Maintain 3-second following distance\n• Plan lane changes early\n• Keep windows closed at high speeds",
                "🏙️ City driving tips:\n• Anticipate traffic lights\n• Coast to red lights instead of braking hard\n• Use gentle acceleration from stops\n• Avoid rush hour when possible"
            ],
            'fuel_efficiency': [
                "⛽ Fuel efficiency strategies:\n• Drive at steady speeds between 50-80 km/h\n• Avoid excessive idling (turn off engine if waiting >30 seconds)\n• Maintain proper tire pressure\n• Use air conditioning wisely",
                "💡 Advanced fuel tips:\n• Combine multiple errands into one trip\n• Remove roof racks when not in use\n• Keep up with regular maintenance\n• Use the recommended grade of motor oil",
                "📊 Your fuel consumption can improve by 10-15% with:\n• Smooth acceleration and braking\n• Proper vehicle maintenance\n• Route planning to avoid traffic\n• Maintaining optimal tire pressure"
            ],
            'maintenance': [
                "🔧 Essential maintenance schedule:\n• Oil change: Every 5,000-7,500 miles\n• Tire rotation: Every 6,000-8,000 miles\n• Brake inspection: Every 12,000 miles\n• Air filter: Every 12,000-15,000 miles",
                "📅 Monthly checks:\n• Tire pressure and tread depth\n• Fluid levels (oil, coolant, brake)\n• Lights and signals\n• Battery terminals\n• Windshield wipers",
                "⚠️ Warning signs to watch for:\n• Dashboard warning lights\n• Unusual noises or vibrations\n• Changes in steering or braking\n• Fluid leaks under the vehicle\n• Decreased fuel efficiency"
            ],
            'safety': [
                "🛡️ Safety reminders:\n• Always wear your seatbelt\n• Adjust mirrors before driving\n• Keep a safe following distance\n• Avoid phone use while driving\n• Check blind spots before changing lanes",
                "🌧️ Weather driving tips:\n• Reduce speed in rain/snow\n• Increase following distance\n• Use headlights in poor visibility\n• Avoid sudden movements\n• Keep emergency kit in car"
            ],
            'default': [
                "I can help you with:\n🚗 Driving tips and techniques\n⛽ Fuel efficiency advice\n🔧 Maintenance schedules\n📊 Trip data analysis\n🛡️ Safety reminders\n\nWhat interests you most?",
                "Ask me about:\n• Your driving performance\n• Fuel-saving techniques\n• Vehicle maintenance\n• Safety tips\n• Trip analysis\n• Weather driving conditions",
                "I'm your vehicle expert! Try asking:\n• 'How can I save fuel?'\n• 'Analyze my trips'\n• 'Give me safety tips'\n• 'What maintenance do I need?'"
            ]
        }
        
        self.patterns = {
            'greeting': [r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b'],
            'driving_tips': [r'\b(driving tips|drive better|improve driving|safe driving|how to drive)\b'],
            'fuel_efficiency': [r'\b(fuel|efficiency|mpg|gas|consumption|save fuel|mileage|economy)\b'],
            'maintenance': [r'\b(maintenance|service|oil change|tire|brake|check|repair|schedule)\b'],
            'trip_data': [r'\b(trip|data|distance|speed|rpm|analysis|analyze|performance|stats)\b'],
            'safety': [r'\b(safety|safe|accident|crash|seatbelt|emergency)\b']
        }

    def get_response(self, message, user_data=None):
        message = message.lower().strip()
        
        # Check for patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    if category == 'trip_data' and user_data:
                        return self._analyze_trip_data(user_data)
                    elif category in self.responses:
                        return random.choice(self.responses[category])
        
        # Specific questions and keywords
        if any(word in message for word in ['score', 'performance', 'rating']):
            return self._performance_advice(user_data)
        elif any(word in message for word in ['alert', 'warning', 'problem']):
            return "⚠️ Check your dashboard for maintenance alerts. Common issues:\n• Low tire pressure\n• Engine temperature\n• Brake wear\n• Oil change due\n\nRegular monitoring prevents major problems!"
        elif any(word in message for word in ['thank', 'thanks']):
            return random.choice(["You're welcome! Drive safely! 🚗", "Happy to help! Stay safe on the roads!", "Anytime! Feel free to ask more questions."])
        elif any(word in message for word in ['help', 'what can you do']):
            return self._show_capabilities()
        elif any(word in message for word in ['rpm', 'revolutions']):
            return self._rpm_advice(user_data)
        elif any(word in message for word in ['acceleration', 'accelerate']):
            return "🚀 Acceleration tips:\n• Gradual acceleration saves fuel\n• Avoid flooring the gas pedal\n• Shift gears smoothly (manual)\n• Use eco-mode if available\n• Anticipate traffic to avoid unnecessary acceleration"
        elif 'how' in message and any(word in message for word in ['improve', 'better']):
            return self._improvement_suggestions(user_data)
        elif any(word in message for word in ['vehicle', 'car', 'my car']):
            return self._vehicle_info(user_data)
        elif any(word in message for word in ['compare', 'comparison', 'vs']):
            return self._comparison_analysis(user_data)
        elif any(word in message for word in ['grade', 'rating']) and 'score' not in message:
            return self._driving_score(user_data)
        elif any(word in message for word in ['week', 'weekly', 'summary']):
            return self._weekly_summary(user_data)
        elif any(word in message for word in ['streak', 'consistent', 'progress']):
            return self._streak_analysis(user_data)
        
        return self._personalized_greeting(user_data) if not self.session_memory.get('greeted') else random.choice(self.responses['default'])

    def _analyze_trip_data(self, user_data):
        if not user_data or 'recent_trips' not in user_data:
            return "📊 I don't have access to your recent trip data. Please check your dashboard for detailed analytics."
        
        trips = user_data['recent_trips']
        if not trips:
            return "🚗 You don't have any recent trips to analyze. Start driving to see personalized insights!"
        
        avg_speed = sum(trip.get('avg_speed_kmph', 0) for trip in trips) / len(trips)
        total_distance = sum(trip.get('distance_km', 0) for trip in trips)
        avg_fuel = sum(trip.get('fuel_consumed', 0) for trip in trips) / len(trips)
        avg_rpm = sum(trip.get('max_rpm', 0) for trip in trips) / len(trips)
        total_brake_events = sum(trip.get('brake_events', 0) for trip in trips)
        
        analysis = f"📈 Analysis of your recent {len(trips)} trips:\n\n"
        analysis += f"🛣️ Total distance: {total_distance:.1f} km\n"
        analysis += f"⚡ Average speed: {avg_speed:.1f} km/h\n"
        analysis += f"⛽ Average fuel consumption: {avg_fuel:.1f} L\n"
        analysis += f"🔧 Average max RPM: {avg_rpm:.0f}\n"
        analysis += f"🛑 Total brake events: {total_brake_events}\n\n"
        
        # Personalized recommendations
        recommendations = "💡 Recommendations:\n"
        if avg_speed > 80:
            recommendations += "• Consider reducing speed to 70-80 km/h for 15% better fuel efficiency\n"
        elif avg_speed < 40:
            recommendations += "• Your city driving speeds are excellent for fuel economy\n"
        
        if avg_rpm > 3000:
            recommendations += "• Try to keep RPM under 3000 for better engine efficiency\n"
        
        if total_brake_events > len(trips) * 10:
            recommendations += "• Work on smoother driving to reduce brake events\n"
        else:
            recommendations += "• Great job on smooth driving with minimal braking!\n"
        
        return analysis + recommendations

    def _performance_advice(self, user_data):
        if not user_data or not user_data.get('recent_trips'):
            return "🏆 General performance tips:\n• Maintain steady speeds (50-80 km/h optimal)\n• Avoid harsh braking and acceleration\n• Plan routes to avoid traffic\n• Keep RPM under 3000\n• Regular vehicle maintenance"
        
        trips = user_data['recent_trips']
        avg_speed = sum(trip.get('avg_speed_kmph', 0) for trip in trips) / len(trips)
        avg_rpm = sum(trip.get('max_rpm', 0) for trip in trips) / len(trips)
        
        advice = "🎯 Personalized performance tips:\n\n"
        
        if avg_speed > 90:
            advice += "🐌 Speed: Consider slowing down - you're averaging {:.1f} km/h\n".format(avg_speed)
        elif avg_speed < 30:
            advice += "🚦 Speed: Your low average speed suggests city driving - great for efficiency!\n"
        else:
            advice += "✅ Speed: Your average speed of {:.1f} km/h is in the efficient range\n".format(avg_speed)
        
        if avg_rpm > 3500:
            advice += "🔧 RPM: Try shifting earlier or driving more gently (current avg: {:.0f} RPM)\n".format(avg_rpm)
        else:
            advice += "✅ RPM: Good engine management with average {:.0f} RPM\n".format(avg_rpm)
        
        advice += "\n📊 Check your trip details for specific metrics and trends!"
        return advice
    
    def _show_capabilities(self):
        return "🤖 I can help you with:\n\n🚗 Driving Tips & Techniques\n⛽ Fuel Efficiency Strategies\n🔧 Maintenance Schedules\n📊 Trip Data Analysis\n🛡️ Safety Reminders\n💰 Cost-Saving Tips\n\nJust ask me anything about your vehicle!"
    
    def _rpm_advice(self, user_data):
        base_advice = "🔧 RPM (Revolutions Per Minute) tips:\n\n• Keep RPM between 1500-3000 for efficiency\n• Shift gears before reaching 3000 RPM (manual)\n• Higher RPM = more fuel consumption\n• Lower RPM in higher gears saves fuel\n"
        
        if user_data and user_data.get('recent_trips'):
            trips = user_data['recent_trips']
            avg_rpm = sum(trip.get('max_rpm', 0) for trip in trips) / len(trips)
            base_advice += f"\n📊 Your average max RPM: {avg_rpm:.0f}\n"
            
            if avg_rpm > 4000:
                base_advice += "⚠️ Your RPM is quite high - try gentler acceleration"
            elif avg_rpm < 2500:
                base_advice += "✅ Excellent RPM management for fuel efficiency!"
            else:
                base_advice += "👍 Good RPM range for balanced performance"
        
        return base_advice
    
    def _improvement_suggestions(self, user_data):
        suggestions = "🚀 Ways to improve your driving:\n\n"
        suggestions += "1️⃣ **Fuel Efficiency:**\n   • Maintain 50-80 km/h when possible\n   • Avoid rapid acceleration\n   • Plan routes to minimize stops\n\n"
        suggestions += "2️⃣ **Safety:**\n   • Increase following distance\n   • Check mirrors every 5-8 seconds\n   • Anticipate other drivers' actions\n\n"
        suggestions += "3️⃣ **Vehicle Care:**\n   • Regular maintenance checks\n   • Monitor tire pressure monthly\n   • Keep emergency kit in car\n\n"
        
        if user_data and user_data.get('recent_trips'):
            suggestions += "📊 Check your dashboard for personalized insights based on your driving data!"
        
        return suggestions
    
    def _vehicle_info(self, user_data):
        if not user_data or not user_data.get('vehicle_number'):
            return "🚗 I don't have your vehicle information. Please check your profile settings."
        
        vehicle_num = user_data['vehicle_number']
        info = f"🚗 Your Vehicle: {vehicle_num}\n\n"
        
        if user_data.get('recent_trips'):
            trips = user_data['recent_trips']
            total_distance = sum(trip.get('distance_km', 0) for trip in trips)
            avg_fuel = sum(trip.get('fuel_consumed', 0) for trip in trips) / len(trips)
            
            info += f"📊 Recent Performance:\n"
            info += f"• Total distance: {total_distance:.1f} km\n"
            info += f"• Average fuel consumption: {avg_fuel:.1f} L per trip\n"
            info += f"• Fuel efficiency: {total_distance/sum(trip.get('fuel_consumed', 1) for trip in trips):.1f} km/L"
        
        return info
    
    def _comparison_analysis(self, user_data):
        if not user_data or not user_data.get('recent_trips') or len(user_data['recent_trips']) < 2:
            return "📊 Need at least 2 trips for comparison analysis. Keep driving to see trends!"
        
        trips = user_data['recent_trips']
        recent = trips[0]
        older = trips[-1]
        
        analysis = "📈 Trip Comparison (Latest vs Oldest):\n\n"
        
        speed_diff = recent.get('avg_speed_kmph', 0) - older.get('avg_speed_kmph', 0)
        fuel_diff = recent.get('fuel_consumed', 0) - older.get('fuel_consumed', 0)
        rpm_diff = recent.get('max_rpm', 0) - older.get('max_rpm', 0)
        
        analysis += f"⚡ Speed: {speed_diff:+.1f} km/h change\n"
        analysis += f"⛽ Fuel: {fuel_diff:+.1f} L change\n"
        analysis += f"🔧 RPM: {rpm_diff:+.0f} change\n\n"
        
        if speed_diff > 5:
            analysis += "📈 You're driving faster lately - consider slowing down for efficiency\n"
        elif speed_diff < -5:
            analysis += "📉 Good job reducing speed for better fuel economy\n"
        
        return analysis
    
    def _personalized_greeting(self, user_data):
        self.session_memory['greeted'] = True
        hour = datetime.now().hour
        greeting = "Good morning!" if hour < 12 else "Good afternoon!" if hour < 17 else "Good evening!"
        
        if user_data and user_data.get('vehicle_number'):
            return f"{greeting} Ready to check your {user_data['vehicle_number']} performance? 🚗"
        return f"{greeting} How can I help with your driving today? 🚗"
    
    def _driving_score(self, user_data):
        if not user_data or not user_data.get('recent_trips'):
            return "🏆 I need trip data to calculate your driving score. Start driving!"
        
        trips = user_data['recent_trips']
        score = 10
        avg_speed = sum(trip.get('avg_speed_kmph', 0) for trip in trips) / len(trips)
        avg_rpm = sum(trip.get('max_rpm', 0) for trip in trips) / len(trips)
        avg_brake_events = sum(trip.get('brake_events', 0) for trip in trips) / len(trips)
        
        if avg_speed > 90: score -= 2
        elif avg_speed > 80: score -= 1
        if avg_rpm > 4000: score -= 2
        elif avg_rpm > 3000: score -= 1
        if avg_brake_events > 15: score -= 2
        elif avg_brake_events > 10: score -= 1
        
        score = max(1, min(10, score))
        rating = "🌟 Excellent" if score >= 9 else "👍 Good" if score >= 7 else "⚠️ Average" if score >= 5 else "🔴 Needs Improvement"
        
        return f"🏆 Your Driving Score: {score}/10 ({rating})\n\nBased on speed, RPM, and braking patterns."
    
    def _weekly_summary(self, user_data):
        if not user_data or not user_data.get('recent_trips'):
            return "📅 I need more trip data for summaries. Keep driving!"
        
        trips = user_data['recent_trips']
        total_distance = sum(trip.get('distance_km', 0) for trip in trips)
        total_fuel = sum(trip.get('fuel_consumed', 0) for trip in trips)
        efficiency = total_distance / total_fuel if total_fuel > 0 else 0
        
        summary = f"📊 Recent Summary:\n\n🛣️ Trips: {len(trips)}\n📏 Distance: {total_distance:.1f} km\n⛽ Fuel: {total_fuel:.1f} L\n📈 Efficiency: {efficiency:.1f} km/L\n\n"
        
        if len(trips) >= 5:
            summary += "🎯 Great consistency!"
        elif efficiency > 10:
            summary += "🌱 Excellent efficiency!"
        else:
            summary += "💡 Try steady speeds for better efficiency."
        
        return summary
    
    def _streak_analysis(self, user_data):
        if not user_data or not user_data.get('recent_trips'):
            return "🔥 Start driving consistently to build your streak!"
        
        trips = user_data['recent_trips']
        streak = 0
        
        for trip in trips:
            speed = trip.get('avg_speed_kmph', 0)
            rpm = trip.get('max_rpm', 0)
            brakes = trip.get('brake_events', 0)
            
            if 40 <= speed <= 80 and rpm <= 3000 and brakes <= 8:
                streak += 1
            else:
                break
        
        if streak >= 5:
            return f"🔥 Amazing! {streak} efficient trips in a row! 🌟"
        elif streak >= 3:
            return f"👍 Good streak! {streak} efficient trips."
        elif streak >= 1:
            return f"🌱 {streak} efficient trip(s). Build a longer streak!"
        else:
            return "💡 Focus on steady speeds (40-80 km/h) and smooth driving!"