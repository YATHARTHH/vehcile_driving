#!/usr/bin/env python3
"""
Enhanced Model Utilities
========================
Utilities for loading and using the enhanced ML models with all 14 features
and predictive maintenance capabilities.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings

class EnhancedModelLoader:
    def __init__(self, model_dir='ml_model'):
        self.model_dir = model_dir
        self.behavior_model = None
        self.maintenance_models = {}
        self.scaler = None
        self.label_encoder = None
        self.model_info = None
        
        # All 14 features
        self.all_features = [
            'avg_speed_kmph', 'max_speed', 'max_rpm', 'fuel_consumed',
            'brake_events', 'steering_angle', 'angular_velocity', 
            'acceleration', 'gear_position', 'tire_pressure',
            'engine_load', 'throttle_position', 'brake_pressure', 
            'trip_duration'
        ]

    def load_enhanced_models(self):
        """Load all enhanced models"""
        try:
            # Check if enhanced models exist
            enhanced_info_path = os.path.join(self.model_dir, 'enhanced_model_info.json')
            if not os.path.exists(enhanced_info_path):
                return False, "Enhanced models not found. Run enhanced_model.py first."
            
            # Load model info
            with open(enhanced_info_path, 'r') as f:
                self.model_info = json.load(f)
            
            # Load behavior model components
            behavior_model_path = os.path.join(self.model_dir, 'enhanced_behavior_model.pkl')
            scaler_path = os.path.join(self.model_dir, 'enhanced_scaler.pkl')
            encoder_path = os.path.join(self.model_dir, 'enhanced_label_encoder.pkl')
            
            if all(os.path.exists(p) for p in [behavior_model_path, scaler_path, encoder_path]):
                self.behavior_model = joblib.load(behavior_model_path)
                self.scaler = joblib.load(scaler_path)
                self.label_encoder = joblib.load(encoder_path)
            else:
                return False, "Enhanced behavior model files missing"
            
            # Load maintenance models
            maintenance_components = ['brake_wear', 'tire_wear', 'engine_stress', 'fuel_efficiency']
            for component in maintenance_components:
                model_path = os.path.join(self.model_dir, f'maintenance_{component}_model.pkl')
                if os.path.exists(model_path):
                    self.maintenance_models[component] = joblib.load(model_path)
            
            return True, f"Enhanced models loaded successfully ({len(self.all_features)} features)"
            
        except Exception as e:
            return False, f"Error loading enhanced models: {str(e)}"

    def predict_enhanced_behavior(self, trip_data):
        """Predict behavior using enhanced model with all 14 features"""
        if not self.behavior_model:
            return {"error": "Enhanced behavior model not loaded"}
        
        try:
            # Extract all 14 features in correct order
            features = []
            missing_features = []
            
            for feature in self.all_features:
                value = trip_data.get(feature)
                if value is None or value == '':
                    missing_features.append(feature)
                    value = 0.0  # Default value
                features.append(float(value))
            
            # Scale features using DataFrame to maintain feature names
            X_df = pd.DataFrame([features], columns=self.all_features)
            X_scaled = self.scaler.transform(X_df)
            
            # Predict
            prediction = self.behavior_model.predict(X_scaled)[0]
            probabilities = self.behavior_model.predict_proba(X_scaled)[0]
            
            # Convert to label
            behavior_class = self.label_encoder.inverse_transform([prediction])[0]
            confidence = float(max(probabilities)) * 100
            
            result = {
                'behavior_class': behavior_class,
                'confidence': confidence,
                'model_used': 'Enhanced Random Forest (14 features)',
                'features_used': len(self.all_features),
                'missing_features': missing_features,
                'enhancement_info': {
                    'original_features': 6,
                    'enhanced_features': 14,
                    'improvement': 'Uses all collected sensor data'
                }
            }
            
            if missing_features:
                result['warning'] = f"Missing features: {', '.join(missing_features)}"
            
            return result
            
        except Exception as e:
            return {"error": f"Enhanced prediction failed: {str(e)}"}

    def predict_maintenance(self, trip_data):
        """Predict maintenance needs for vehicle components"""
        if not self.maintenance_models:
            return {"error": "Maintenance models not loaded"}
        
        try:
            # Extract features
            features = []
            for feature in self.all_features:
                value = trip_data.get(feature, 0.0)
                if value is None:
                    value = 0.0
                features.append(float(value))
            
            # Scale features using DataFrame to maintain feature names
            X_df = pd.DataFrame([features], columns=self.all_features)
            X_scaled = self.scaler.transform(X_df)
            
            predictions = {}
            alerts = []
            
            # Predict for each component
            for component, model in self.maintenance_models.items():
                wear_score = float(model.predict(X_scaled)[0])
                
                predictions[component] = {
                    'wear_score': wear_score,
                    'status': self._get_status(wear_score),
                    'days_until_service': self._estimate_days(wear_score),
                    'recommendation': self._get_recommendation(component, wear_score)
                }
                
                # Generate alerts for high wear
                if wear_score > 0.7:
                    alerts.append({
                        'component': component.replace('_', ' ').title(),
                        'severity': 'high',
                        'message': f"{component.replace('_', ' ').title()} requires immediate attention",
                        'days_remaining': self._estimate_days(wear_score),
                        'icon': self._get_component_icon(component)
                    })
                elif wear_score > 0.5:
                    alerts.append({
                        'component': component.replace('_', ' ').title(),
                        'severity': 'medium',
                        'message': f"Schedule {component.replace('_', ' ')} maintenance soon",
                        'days_remaining': self._estimate_days(wear_score),
                        'icon': self._get_component_icon(component)
                    })
            
            # Calculate overall health
            overall_health = self._calculate_health(predictions)
            
            return {
                'predictions': predictions,
                'alerts': alerts,
                'overall_health': overall_health,
                'summary': {
                    'components_checked': len(predictions),
                    'high_priority_alerts': len([a for a in alerts if a['severity'] == 'high']),
                    'medium_priority_alerts': len([a for a in alerts if a['severity'] == 'medium'])
                }
            }
            
        except Exception as e:
            return {"error": f"Maintenance prediction failed: {str(e)}"}

    def _get_status(self, score):
        """Convert wear score to status"""
        if score < 0.25:
            return "Excellent"
        elif score < 0.5:
            return "Good"
        elif score < 0.75:
            return "Fair"
        else:
            return "Poor"

    def _estimate_days(self, score):
        """Estimate days until maintenance needed"""
        if score < 0.25:
            return 120
        elif score < 0.5:
            return 90
        elif score < 0.75:
            return 30
        else:
            return 7

    def _get_recommendation(self, component, score):
        """Get specific recommendation for component"""
        recommendations = {
            'brake_wear': {
                'low': 'Brakes in good condition. Continue normal driving.',
                'medium': 'Monitor brake performance. Avoid hard braking.',
                'high': 'Schedule brake inspection immediately.'
            },
            'tire_wear': {
                'low': 'Tire pressure optimal. Check monthly.',
                'medium': 'Adjust tire pressure to 32 PSI.',
                'high': 'Inspect tires for wear. Consider replacement.'
            },
            'engine_stress': {
                'low': 'Engine running efficiently. Maintain regular service.',
                'medium': 'Reduce high RPM driving. Check engine oil.',
                'high': 'Engine showing stress. Schedule diagnostic check.'
            },
            'fuel_efficiency': {
                'low': 'Excellent fuel efficiency. Keep up good driving habits.',
                'medium': 'Fuel consumption slightly high. Check driving style.',
                'high': 'Poor fuel efficiency. Check engine and driving habits.'
            }
        }
        
        if score < 0.5:
            level = 'low'
        elif score < 0.75:
            level = 'medium'
        else:
            level = 'high'
        
        return recommendations.get(component, {}).get(level, 'Monitor component condition.')

    def _get_component_icon(self, component):
        """Get icon for component"""
        icons = {
            'brake_wear': 'fa-car-burst',
            'tire_wear': 'fa-tire',
            'engine_stress': 'fa-car',
            'fuel_efficiency': 'fa-gas-pump'
        }
        return icons.get(component, 'fa-wrench')

    def _calculate_health(self, predictions):
        """Calculate overall vehicle health"""
        if not predictions:
            return {"score": 0, "status": "Unknown"}
        
        scores = [pred['wear_score'] for pred in predictions.values()]
        avg_score = np.mean(scores)
        
        # Invert score (lower wear = higher health)
        health_score = int((1 - avg_score) * 100)
        
        if health_score >= 80:
            status = "Excellent"
        elif health_score >= 60:
            status = "Good"
        elif health_score >= 40:
            status = "Fair"
        else:
            status = "Poor"
        
        return {
            "score": health_score,
            "status": status,
            "components": len(predictions)
        }

    def get_model_info(self):
        """Get enhanced model information"""
        if not self.model_info:
            return None
        
        return {
            **self.model_info,
            'loaded_components': {
                'behavior_model': self.behavior_model is not None,
                'maintenance_models': len(self.maintenance_models),
                'scaler': self.scaler is not None,
                'label_encoder': self.label_encoder is not None
            }
        }

# Global instance for easy import
enhanced_loader = EnhancedModelLoader()

def load_enhanced_artifacts():
    """Load enhanced model artifacts"""
    return enhanced_loader.load_enhanced_models()

def predict_enhanced_behavior(trip_data):
    """Predict behavior with enhanced model"""
    return enhanced_loader.predict_enhanced_behavior(trip_data)

def predict_maintenance_needs(trip_data):
    """Predict maintenance needs"""
    return enhanced_loader.predict_maintenance(trip_data)

def get_enhanced_model_info():
    """Get enhanced model information"""
    return enhanced_loader.get_model_info()