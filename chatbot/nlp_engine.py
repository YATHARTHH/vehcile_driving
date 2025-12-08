import re
from typing import Dict, List, Tuple, Optional
import logging
try:
    import torch
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    torch = None
    pipeline = None

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    nltk = None
    SentimentIntensityAnalyzer = None

class NLPEngine:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        self._init_models()
        
    def _init_models(self):
        """Initialize NLP models with fallback handling"""
        self.intent_classifier = None
        self.sentiment_analyzer = None
        
        # Try NLTK sentiment analyzer first (lightweight)
        if NLTK_AVAILABLE:
            try:
                nltk.download('vader_lexicon', quiet=True)
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
            except:
                pass
        
        # Try transformers as fallback (if available)
        if TRANSFORMERS_AVAILABLE and not self.sentiment_analyzer:
            try:
                self.sentiment_analyzer = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english",
                    device=self.device
                )
            except:
                pass
            
        # Entity patterns for vehicle domain
        self.entity_patterns = {
            'speed': r'\b(\d+(?:\.\d+)?)\s*(?:km/h|kmh|mph|kph)\b',
            'distance': r'\b(\d+(?:\.\d+)?)\s*(?:km|miles|mi)\b',
            'fuel': r'\b(\d+(?:\.\d+)?)\s*(?:l|liters?|gallons?|gal)\b',
            'rpm': r'\b(\d+)\s*(?:rpm|revolutions?)\b',
            'time': r'\b(\d{1,2}:\d{2}|\d+\s*(?:hours?|hrs?|minutes?|mins?))\b',
            'vehicle_part': r'\b(engine|brake|tire|battery|oil|fuel|transmission|clutch)\b',
            'location': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        }
        
        # Enhanced intent keywords
        self.intent_keywords = {
            'question': ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'is', 'are', 'can', 'could', 'should', 'would'],
            'request': ['please', 'help', 'show', 'tell', 'give', 'provide', 'explain'],
            'complaint': ['problem', 'issue', 'wrong', 'bad', 'terrible', 'awful', 'broken', 'not working'],
            'praise': ['good', 'great', 'excellent', 'amazing', 'perfect', 'love', 'like', 'awesome'],
            'comparison': ['vs', 'versus', 'compare', 'better', 'worse', 'difference', 'between'],
            'improvement': ['improve', 'better', 'optimize', 'enhance', 'increase', 'reduce', 'save']
        }

    def analyze_message(self, message: str) -> Dict:
        """Comprehensive message analysis"""
        result = {
            'original_message': message,
            'cleaned_message': self._clean_text(message),
            'intent': self._detect_intent(message),
            'sentiment': self._analyze_sentiment(message),
            'entities': self._extract_entities(message),
            'keywords': self._extract_keywords(message),
            'confidence': 0.0
        }
        
        # Calculate overall confidence
        result['confidence'] = self._calculate_confidence(result)
        return result

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        return text

    def _detect_intent(self, message: str) -> Dict:
        """Enhanced intent detection"""
        message_lower = message.lower()
        detected_intents = {}
        
        # Rule-based intent detection
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                detected_intents[intent] = score / len(keywords)
        
        # ML-based intent detection (if available)
        if self.intent_classifier:
            try:
                ml_results = self.intent_classifier(message)
                if ml_results:
                    if isinstance(ml_results, list) and len(ml_results) > 0:
                        result = ml_results[0]
                        label = result['label'].lower()
                        detected_intents[f'ml_{label}'] = result['score']
            except:
                pass
        
        # Determine primary intent
        primary_intent = max(detected_intents.items(), key=lambda x: x[1]) if detected_intents else ('unknown', 0.0)
        
        return {
            'primary': primary_intent[0],
            'confidence': primary_intent[1],
            'all_intents': detected_intents
        }

    def _analyze_sentiment(self, message: str) -> Dict:
        """Analyze message sentiment"""
        # Rule-based sentiment
        positive_words = ['good', 'great', 'excellent', 'love', 'like', 'amazing', 'perfect', 'awesome', 'thanks']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'problem', 'issue', 'wrong', 'broken', 'frustrated']
        
        message_lower = message.lower()
        pos_score = sum(1 for word in positive_words if word in message_lower)
        neg_score = sum(1 for word in negative_words if word in message_lower)
        
        rule_sentiment = 'positive' if pos_score > neg_score else 'negative' if neg_score > pos_score else 'neutral'
        rule_confidence = abs(pos_score - neg_score) / max(len(message.split()), 1)
        
        # ML-based sentiment (if available)
        ml_sentiment = {'label': 'neutral', 'score': 0.5}
        if self.sentiment_analyzer:
            try:
                if hasattr(self.sentiment_analyzer, 'polarity_scores'):  # NLTK
                    scores = self.sentiment_analyzer.polarity_scores(message)
                    compound = scores['compound']
                    if compound >= 0.05:
                        ml_sentiment = {'label': 'positive', 'score': abs(compound)}
                    elif compound <= -0.05:
                        ml_sentiment = {'label': 'negative', 'score': abs(compound)}
                    else:
                        ml_sentiment = {'label': 'neutral', 'score': 0.5}
                else:  # Transformers
                    ml_result = self.sentiment_analyzer(message)[0]
                    ml_sentiment = {
                        'label': ml_result['label'].lower(),
                        'score': ml_result['score']
                    }
            except:
                pass
        
        return {
            'rule_based': {'label': rule_sentiment, 'confidence': rule_confidence},
            'ml_based': ml_sentiment,
            'final': ml_sentiment['label'] if ml_sentiment['score'] > 0.7 else rule_sentiment
        }

    def _extract_entities(self, message: str) -> Dict:
        """Extract domain-specific entities"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities

    def _extract_keywords(self, message: str) -> List[str]:
        """Extract important keywords"""
        # Vehicle-specific keywords
        vehicle_keywords = [
            'fuel', 'gas', 'efficiency', 'mileage', 'consumption', 'speed', 'rpm', 'brake',
            'engine', 'maintenance', 'service', 'oil', 'tire', 'battery', 'transmission',
            'safety', 'accident', 'crash', 'route', 'navigation', 'traffic', 'cost',
            'save', 'money', 'performance', 'driving', 'trip', 'distance'
        ]
        
        message_lower = message.lower()
        found_keywords = [kw for kw in vehicle_keywords if kw in message_lower]
        
        # Add extracted numbers as potential keywords
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', message)
        found_keywords.extend(numbers)
        
        return found_keywords

    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate overall analysis confidence"""
        factors = []
        
        # Intent confidence
        factors.append(analysis['intent']['confidence'])
        
        # Sentiment confidence
        if analysis['sentiment']['ml_based']['score'] > 0.7:
            factors.append(analysis['sentiment']['ml_based']['score'])
        else:
            factors.append(analysis['sentiment']['rule_based']['confidence'])
        
        # Entity extraction confidence
        entity_confidence = len(analysis['entities']) / 5  # Normalize by expected max entities
        factors.append(min(entity_confidence, 1.0))
        
        # Keyword confidence
        keyword_confidence = len(analysis['keywords']) / 10  # Normalize by expected max keywords
        factors.append(min(keyword_confidence, 1.0))
        
        return sum(factors) / len(factors) if factors else 0.0

    def get_response_strategy(self, analysis: Dict) -> Dict:
        """Determine response strategy based on analysis"""
        strategy = {
            'tone': 'neutral',
            'detail_level': 'medium',
            'personalization': False,
            'follow_up_questions': []
        }
        
        # Adjust tone based on sentiment
        sentiment = analysis['sentiment']['final']
        if sentiment == 'negative':
            strategy['tone'] = 'empathetic'
            strategy['detail_level'] = 'high'
        elif sentiment == 'positive':
            strategy['tone'] = 'enthusiastic'
        
        # Adjust detail level based on intent
        primary_intent = analysis['intent']['primary']
        if 'question' in primary_intent:
            strategy['detail_level'] = 'high'
        elif 'request' in primary_intent:
            strategy['detail_level'] = 'medium'
        
        # Enable personalization if entities found
        if analysis['entities']:
            strategy['personalization'] = True
        
        # Generate follow-up questions
        if 'fuel' in analysis['keywords']:
            strategy['follow_up_questions'].append("Would you like specific fuel-saving tips?")
        if 'maintenance' in analysis['keywords']:
            strategy['follow_up_questions'].append("Do you need a maintenance schedule?")
        
        return strategy

    def enhance_response(self, base_response: str, analysis: Dict, strategy: Dict) -> str:
        """Enhance response based on NLP analysis"""
        enhanced = base_response
        
        # Add personalized elements
        if strategy['personalization'] and analysis['entities']:
            entities = analysis['entities']
            if 'speed' in entities:
                enhanced += f"\n\n💡 I noticed you mentioned {entities['speed'][0]} - that's a good reference point for optimization!"
            if 'fuel' in entities:
                enhanced += f"\n\n⛽ Regarding the {entities['fuel'][0]} fuel consumption you mentioned, here are some tips..."
        
        # Adjust tone
        if strategy['tone'] == 'empathetic':
            enhanced = "I understand your concern. " + enhanced
        elif strategy['tone'] == 'enthusiastic':
            enhanced = enhanced + " 🎉"
        
        # Add follow-up questions
        if strategy['follow_up_questions']:
            enhanced += f"\n\n❓ {strategy['follow_up_questions'][0]}"
        
        return enhanced