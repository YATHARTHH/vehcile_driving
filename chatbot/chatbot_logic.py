import re
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
try:
    from .nlp_engine import NLPEngine
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    NLPEngine = None

class VehicleChatbot:
    def __init__(self):
        self.session_memory = {}
        self.conversation_history = []
        self.user_context = {}
        
        # Initialize NLP engine if available
        self.nlp_engine = None
        if NLP_AVAILABLE:
            try:
                self.nlp_engine = NLPEngine()
                print("[NLP Engine] Advanced NLP engine loaded")
            except Exception as e:
                print(f"[NLP Engine] NLP engine failed to load: {e}")
                self.nlp_engine = None
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
            'greeting': [r'\b(hi|hello|hey|good morning|good afternoon|good evening|greetings)\b'],
            'driving_tips': [r'\b(driving tips|drive better|improve driving|safe driving|how to drive|driving advice)\b'],
            'fuel_efficiency': [r'\b(fuel|efficiency|mpg|gas|consumption|save fuel|mileage|economy|eco.?driving)\b'],
            'maintenance': [r'\b(maintenance|service|oil change|tire|brake|check|repair|schedule|servicing)\b'],
            'trip_data': [r'\b(trip|data|distance|speed|rpm|analysis|analyze|performance|stats|metrics)\b'],
            'safety': [r'\b(safety|safe|accident|crash|seatbelt|emergency|hazard)\b'],
            'weather': [r'\b(weather|rain|snow|fog|storm|winter|summer|conditions)\b'],
            'route': [r'\b(route|navigation|directions|path|way|road)\b'],
            'cost': [r'\b(cost|money|expensive|cheap|budget|price|save)\b']
        }
        
        self.intent_keywords = {
            'question': ['what', 'how', 'why', 'when', 'where', 'which', 'who'],
            'request': ['can you', 'could you', 'please', 'help me', 'show me'],
            'comparison': ['vs', 'versus', 'compare', 'better', 'worse', 'difference'],
            'improvement': ['improve', 'better', 'optimize', 'enhance', 'increase']
        }

    def get_response(self, message: str, user_data: Optional[Dict] = None) -> str:
        original_message = message
        message_lower = message.lower().strip()
        
        # Store conversation history
        self.conversation_history.append({'user': original_message, 'timestamp': datetime.now()})
        
        # Update user context
        if user_data:
            self.user_context.update(user_data)
        
        # Advanced NLP analysis if available
        nlp_analysis = None
        response_strategy = None
        if self.nlp_engine:
            try:
                nlp_analysis = self.nlp_engine.analyze_message(original_message)
                response_strategy = self.nlp_engine.get_response_strategy(nlp_analysis)
            except Exception as e:
                print(f"NLP analysis failed: {e}")
        
        # Detect intent (enhanced with NLP if available)
        intent = self._detect_intent_enhanced(message_lower, nlp_analysis)
        
        # Check for patterns with priority
        response = self._pattern_matching_enhanced(message_lower, user_data, intent, nlp_analysis)
        if response:
            # Enhance response with NLP insights
            if self.nlp_engine and nlp_analysis and response_strategy:
                response = self.nlp_engine.enhance_response(response, nlp_analysis, response_strategy)
            self._add_to_history('bot', response)
            return response
        
        # Contextual responses based on conversation history
        context_response = self._contextual_response(message_lower, user_data)
        if context_response:
            if self.nlp_engine and nlp_analysis and response_strategy:
                context_response = self.nlp_engine.enhance_response(context_response, nlp_analysis, response_strategy)
            self._add_to_history('bot', context_response)
            return context_response
        
        # Default intelligent response
        default_response = self._intelligent_default(message_lower, user_data, nlp_analysis)
        if self.nlp_engine and nlp_analysis and response_strategy:
            default_response = self.nlp_engine.enhance_response(default_response, nlp_analysis, response_strategy)
        self._add_to_history('bot', default_response)
        return default_response
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in message for keyword in keywords):
                return intent
        return 'statement'
    
    def _detect_intent_enhanced(self, message: str, nlp_analysis: Optional[Dict] = None) -> str:
        """Enhanced intent detection using NLP analysis"""
        if nlp_analysis and nlp_analysis.get('intent'):
            primary_intent = nlp_analysis['intent']['primary']
            confidence = nlp_analysis['intent']['confidence']
            
            # Use NLP intent if confidence is high
            if confidence > 0.6:
                return primary_intent
        
        # Fallback to rule-based detection
        return self._detect_intent(message)
    
    def _pattern_matching_enhanced(self, message: str, user_data: Optional[Dict], intent: str, nlp_analysis: Optional[Dict] = None) -> Optional[str]:
        """Enhanced pattern matching with NLP insights"""
        # Use entities from NLP analysis for better matching
        if nlp_analysis and nlp_analysis.get('entities'):
            entities = nlp_analysis['entities']
            
            # Handle specific entity-based responses
            if 'speed' in entities:
                speed_values = entities['speed']
                return f"🚗 I see you mentioned {speed_values[0]} speed. Here's what I recommend for optimal efficiency at that speed:\n\n" + self._speed_specific_advice(speed_values[0])
            
            if 'fuel' in entities:
                fuel_values = entities['fuel']
                return f"⛽ Regarding {fuel_values[0]} fuel consumption, here are personalized tips:\n\n" + self._fuel_specific_advice(fuel_values[0], user_data)
        
        # Fallback to original pattern matching
        return self._pattern_matching(message, user_data, intent)
    
    def _pattern_matching(self, message: str, user_data: Optional[Dict], intent: str) -> Optional[str]:
        """Enhanced pattern matching with context"""
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    if category == 'trip_data' and user_data:
                        return self._analyze_trip_data(user_data)
                    elif category == 'weather':
                        return self._weather_driving_advice()
                    elif category == 'route':
                        return self._route_advice()
                    elif category == 'cost':
                        return self._cost_saving_tips(user_data)
                    elif category in self.responses:
                        return self._contextual_response_selection(category, intent, user_data)
        
        # Specific keyword handling
        return self._handle_specific_keywords(message, user_data)
    
    def _contextual_response_selection(self, category: str, intent: str, user_data: Optional[Dict]) -> str:
        """Select response based on context and intent"""
        responses = self.responses[category]
        
        # Personalize based on user data
        if user_data and user_data.get('recent_trips'):
            if category == 'fuel_efficiency':
                return self._personalized_fuel_advice(user_data)
            elif category == 'driving_tips':
                return self._personalized_driving_tips(user_data)
        
        return random.choice(responses)
    
    def _handle_specific_keywords(self, message: str, user_data: Optional[Dict]) -> Optional[str]:
        """Handle specific keywords and phrases"""
        keyword_handlers = {
            ('score', 'performance', 'rating'): lambda: self._performance_advice(user_data),
            ('alert', 'warning', 'problem'): lambda: self._alert_advice(),
            ('thank', 'thanks'): lambda: self._gratitude_response(),
            ('help', 'what can you do'): lambda: self._show_capabilities(),
            ('rpm', 'revolutions'): lambda: self._rpm_advice(user_data),
            ('acceleration', 'accelerate'): lambda: self._acceleration_advice(),
            ('vehicle', 'car', 'my car'): lambda: self._vehicle_info(user_data),
            ('compare', 'comparison', 'vs'): lambda: self._comparison_analysis(user_data),
            ('week', 'weekly', 'summary'): lambda: self._weekly_summary(user_data),
            ('streak', 'consistent', 'progress'): lambda: self._streak_analysis(user_data)
        }
        
        for keywords, handler in keyword_handlers.items():
            if any(word in message for word in keywords):
                return handler()
        
        if 'how' in message and any(word in message for word in ['improve', 'better']):
            return self._improvement_suggestions(user_data)
        
        return None
    
    def _contextual_response(self, message: str, user_data: Optional[Dict]) -> Optional[str]:
        """Generate contextual responses based on conversation history"""
        if len(self.conversation_history) > 1:
            last_bot_response = next((item['bot'] for item in reversed(self.conversation_history) if 'bot' in item), None)
            
            # Follow-up questions
            if last_bot_response and 'fuel' in last_bot_response.lower():
                if any(word in message for word in ['more', 'tell me', 'explain']):
                    return self._detailed_fuel_tips(user_data)
            
            # Clarification requests
            if any(word in message for word in ['what do you mean', 'explain', 'clarify']):
                return "Let me clarify! I can help you with:\n• Analyzing your driving patterns\n• Fuel efficiency tips\n• Maintenance schedules\n• Safety advice\n\nWhat specific area interests you?"
        
        return None
    
    def _speed_specific_advice(self, speed: str) -> str:
        """Provide speed-specific advice"""
        try:
            speed_val = float(re.findall(r'\d+(?:\.\d+)?', speed)[0])
            if speed_val > 100:
                return "That's quite fast! Consider reducing speed to 80-90 km/h for better fuel efficiency and safety."
            elif speed_val > 80:
                return "Good highway speed! You're in the efficient range. Maintain steady speeds for best results."
            elif speed_val > 50:
                return "Perfect speed range for fuel efficiency! This is the sweet spot for most vehicles."
            else:
                return "City driving speeds are great for fuel economy. Focus on smooth acceleration and braking."
        except:
            return "Speed management is key to efficient driving. Aim for 50-80 km/h when possible."
    
    def _fuel_specific_advice(self, fuel: str, user_data: Optional[Dict]) -> str:
        """Provide fuel-specific advice"""
        base_advice = "Here are ways to optimize your fuel consumption:\n• Maintain steady speeds\n• Avoid rapid acceleration\n• Keep tires properly inflated\n• Remove excess weight"
        
        if user_data and user_data.get('recent_trips'):
            trips = user_data['recent_trips']
            avg_fuel = sum(trip.get('fuel_consumed', 0) for trip in trips) / len(trips)
            base_advice += f"\n\n📊 Your average fuel consumption: {avg_fuel:.1f}L per trip"
        
        return base_advice
    
    def _intelligent_default(self, message: str, user_data: Optional[Dict], nlp_analysis: Optional[Dict] = None) -> str:
        """Generate intelligent default responses with NLP enhancement"""
        if not self.session_memory.get('greeted'):
            return self._personalized_greeting(user_data)
        
        # Use NLP analysis for better default responses
        if nlp_analysis:
            sentiment = nlp_analysis.get('sentiment', {}).get('final', 'neutral')
            keywords = nlp_analysis.get('keywords', [])
            
            # Sentiment-aware responses
            if sentiment == 'negative':
                return "I understand you might be experiencing some issues. I'm here to help! Can you tell me more about what's concerning you with your vehicle?"
            elif sentiment == 'positive':
                return "Great to hear positive feedback! How can I help you optimize your driving experience even further?"
            
            # Keyword-based suggestions
            if keywords:
                relevant_keywords = [kw for kw in keywords if kw in ['fuel', 'speed', 'maintenance', 'safety', 'cost']]
                if relevant_keywords:
                    return f"I noticed you mentioned {', '.join(relevant_keywords)}. I can provide detailed advice on these topics. What specific aspect interests you most?"
        
        # Analyze message for potential topics
        if len(message.split()) > 5:  # Longer messages
            return "I understand you're asking about vehicle-related topics. I can help with driving tips, fuel efficiency, maintenance, and trip analysis. Could you be more specific about what you'd like to know?"
        
        return random.choice(self.responses['default'])
    
    def _add_to_history(self, sender: str, message: str):
        """Add message to conversation history"""
        self.conversation_history.append({sender: message, 'timestamp': datetime.now()})

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
    
    def _weather_driving_advice(self) -> str:
        """Weather-specific driving advice"""
        return "🌦️ Weather Driving Tips:\n\n🌧️ **Rain:**\n• Reduce speed by 10-15%\n• Increase following distance to 4+ seconds\n• Use headlights even during day\n• Avoid sudden movements\n\n❄️ **Snow/Ice:**\n• Drive 50% slower than normal\n• Brake gently and early\n• Accelerate slowly\n• Keep emergency kit in car\n\n🌫️ **Fog:**\n• Use low beam headlights\n• Follow road markings\n• Increase following distance\n• Pull over if visibility is too poor"
    
    def _route_advice(self) -> str:
        """Route planning and navigation advice"""
        return "🗺️ Smart Route Planning:\n\n📱 **Before You Go:**\n• Check traffic conditions\n• Plan fuel stops for long trips\n• Consider alternate routes\n• Update GPS maps regularly\n\n⛽ **Fuel Efficiency Routes:**\n• Avoid heavy traffic areas\n• Choose highways over city streets\n• Plan errands in one trip\n• Use route optimization apps\n\n🚗 **Safety First:**\n• Share your route with someone\n• Check weather conditions\n• Ensure vehicle is road-ready"
    
    def _cost_saving_tips(self, user_data: Optional[Dict]) -> str:
        """Cost-saving driving tips"""
        base_tips = "💰 Cost-Saving Driving Tips:\n\n⛽ **Fuel Costs:**\n• Maintain steady speeds (50-80 km/h)\n• Remove excess weight\n• Keep tires properly inflated\n• Combine multiple errands\n\n🔧 **Maintenance Costs:**\n• Follow service schedules\n• Check fluids regularly\n• Address issues early\n• Learn basic maintenance\n\n🚗 **Smart Driving:**\n• Avoid rush hour when possible\n• Use cruise control on highways\n• Plan efficient routes"
        
        if user_data and user_data.get('recent_trips'):
            trips = user_data['recent_trips']
            avg_fuel = sum(trip.get('fuel_consumed', 0) for trip in trips) / len(trips)
            total_distance = sum(trip.get('distance_km', 0) for trip in trips)
            
            if avg_fuel > 0:
                efficiency = total_distance / (avg_fuel * len(trips))
                base_tips += f"\n\n📊 **Your Stats:**\n• Current efficiency: ~{efficiency:.1f} km/L\n• Potential savings with 15% improvement: ~{efficiency * 0.15:.1f} km/L"
        
        return base_tips
    
    def _personalized_fuel_advice(self, user_data: Dict) -> str:
        """Personalized fuel efficiency advice based on user data"""
        trips = user_data.get('recent_trips', [])
        if not trips:
            return random.choice(self.responses['fuel_efficiency'])
        
        avg_speed = sum(trip.get('avg_speed_kmph', 0) for trip in trips) / len(trips)
        avg_rpm = sum(trip.get('max_rpm', 0) for trip in trips) / len(trips)
        
        advice = "⛽ **Personalized Fuel Tips for You:**\n\n"
        
        if avg_speed > 85:
            advice += "🐌 **Speed Optimization:** Your average speed is {:.1f} km/h. Reducing to 70-80 km/h could improve fuel efficiency by 15-20%\n\n".format(avg_speed)
        elif avg_speed < 40:
            advice += "🏙️ **City Driving:** Your low average speed suggests city driving. Focus on smooth acceleration and anticipating traffic lights\n\n"
        
        if avg_rpm > 3500:
            advice += "🔧 **RPM Management:** Your average max RPM is {:.0f}. Try shifting earlier or accelerating more gently\n\n".format(avg_rpm)
        
        advice += "💡 **Quick Wins:**\n• Check tire pressure monthly\n• Remove unnecessary weight\n• Plan combined trips\n• Use A/C wisely (windows up at highway speeds)"
        
        return advice
    
    def _personalized_driving_tips(self, user_data: Dict) -> str:
        """Personalized driving tips based on user patterns"""
        trips = user_data.get('recent_trips', [])
        if not trips:
            return random.choice(self.responses['driving_tips'])
        
        avg_brake_events = sum(trip.get('brake_events', 0) for trip in trips) / len(trips)
        avg_speed = sum(trip.get('avg_speed_kmph', 0) for trip in trips) / len(trips)
        
        tips = "🚗 **Personalized Driving Tips:**\n\n"
        
        if avg_brake_events > 12:
            tips += "🛑 **Smooth Driving:** You average {:.1f} brake events per trip. Try:\n• Looking further ahead\n• Coasting to red lights\n• Maintaining steady following distance\n\n".format(avg_brake_events)
        
        if avg_speed > 80:
            tips += "⚡ **Speed Management:** Consider reducing highway speeds slightly for better fuel economy and safety\n\n"
        
        tips += "🎯 **Focus Areas:**\n• Anticipate traffic flow\n• Maintain 3-second following rule\n• Use gentle inputs (steering, braking, acceleration)\n• Stay alert and avoid distractions"
        
        return tips
    
    def _detailed_fuel_tips(self, user_data: Optional[Dict]) -> str:
        """Detailed fuel efficiency explanation"""
        return "🔍 **Detailed Fuel Efficiency Guide:**\n\n🏎️ **Speed & Efficiency:**\n• 50-80 km/h: Optimal efficiency zone\n• Every 10 km/h over 80: ~10% more fuel\n• Highway vs city: 15-20% difference\n\n🚗 **Driving Techniques:**\n• Gradual acceleration (0-60 in 15+ seconds)\n• Anticipate stops (coast vs brake)\n• Maintain steady speeds\n• Use cruise control on highways\n\n🔧 **Vehicle Factors:**\n• Tire pressure: 3% efficiency per 1 PSI low\n• Weight: 2% per 100 lbs excess\n• Aerodynamics: Windows vs A/C at speed\n• Engine maintenance: 4% with proper tune-up"
    
    def _alert_advice(self) -> str:
        """Enhanced alert and warning advice"""
        return "⚠️ **Vehicle Alert Guide:**\n\n🚨 **Immediate Action Required:**\n• Engine temperature warning\n• Oil pressure light\n• Brake system warning\n• Battery/charging system\n\n⚡ **Soon (within days):**\n• Low tire pressure\n• Fuel level low\n• Maintenance due\n• Check engine light\n\n📅 **Preventive Monitoring:**\n• Dashboard warning lights\n• Unusual noises or vibrations\n• Changes in performance\n• Fluid leaks\n\n💡 **Pro Tip:** Address warnings early to prevent costly repairs!"
    
    def _gratitude_response(self) -> str:
        """Varied gratitude responses"""
        responses = [
            "You're welcome! Drive safely! 🚗",
            "Happy to help! Stay safe on the roads! 🛣️",
            "Anytime! Feel free to ask more questions. 🤖",
            "Glad I could assist! Keep up the good driving! 👍",
            "My pleasure! Remember, safe driving saves lives and money! 💰"
        ]
        return random.choice(responses)
    
    def _acceleration_advice(self) -> str:
        """Enhanced acceleration advice"""
        return "🚀 **Smart Acceleration Guide:**\n\n⚡ **Fuel-Efficient Acceleration:**\n• 0-60 km/h in 15+ seconds\n• Keep RPM under 3000\n• Use 75% throttle maximum\n• Shift at 2500 RPM (manual)\n\n🏁 **Performance vs Economy:**\n• Aggressive: 0-60 in <10 sec (40% more fuel)\n• Normal: 0-60 in 10-15 sec (balanced)\n• Eco: 0-60 in 15+ sec (optimal efficiency)\n\n🎯 **Technique Tips:**\n• Smooth, progressive pressure\n• Anticipate traffic flow\n• Use eco-mode when available\n• Coast to decelerate when possible"

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
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation"""
        if not self.conversation_history:
            return "No conversation history available."
        
        user_messages = [item.get('user', '') for item in self.conversation_history if 'user' in item]
        topics = []
        
        for message in user_messages:
            message_lower = message.lower()
            for category in self.patterns.keys():
                for pattern in self.patterns[category]:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        if category not in topics:
                            topics.append(category)
        
        if topics:
            return f"📋 **Conversation Summary:**\nTopics discussed: {', '.join(topics)}\nTotal messages: {len(user_messages)}"
        else:
            return "📋 **Conversation Summary:**\nGeneral vehicle assistance discussion"
    
    def get_nlp_insights(self, message: str) -> Dict:
        """Get NLP insights for debugging/analysis"""
        if self.nlp_engine:
            try:
                return self.nlp_engine.analyze_message(message)
            except Exception as e:
                return {'error': str(e)}
        return {'error': 'NLP engine not available'}
    
    def clear_session(self):
        """Clear session data for new conversation"""
        self.session_memory.clear()
        self.conversation_history.clear()
        self.user_context.clear()