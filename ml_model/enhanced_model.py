#!/usr/bin/env python3
"""
Enhanced ML Model with All 14 Features + Predictive Maintenance
================================================================
Improves the existing model by:
1. Using all 14 collected features instead of just 6
2. Adding predictive maintenance capabilities
3. Keeping existing Random Forest, SVM, etc. models
"""

import pandas as pd
import numpy as np
import sqlite3
import joblib
import json
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

class EnhancedVehicleML:
    def __init__(self, db_path='instance/trips.db'):
        self.db_path = db_path
        self.behavior_model = None
        self.maintenance_models = {}
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # All 14 features we collect
        self.all_features = [
            'avg_speed_kmph', 'max_speed', 'max_rpm', 'fuel_consumed',
            'brake_events', 'steering_angle', 'angular_velocity', 
            'acceleration', 'gear_position', 'tire_pressure',
            'engine_load', 'throttle_position', 'brake_pressure', 
            'trip_duration'
        ]
        
        # Maintenance prediction targets
        self.maintenance_targets = {
            'brake_wear': 'brake_events',
            'tire_wear': 'tire_pressure', 
            'engine_stress': 'max_rpm',
            'fuel_efficiency': 'fuel_consumed'
        }

    def load_data(self):
        """Load trip data from database"""
        print("Loading data from database...")
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
        
        # Convert all feature columns to numeric, handling any data type issues
        for feature in self.all_features + ['distance_km']:
            if feature in df.columns:
                df[feature] = pd.to_numeric(df[feature], errors='coerce')
        
        # Clean data
        df_clean = df.dropna(subset=self.all_features).copy()
        df_clean = df_clean[df_clean['distance_km'] > 0]  # Valid trips only
        
        print(f"Loaded {len(df_clean)} clean trips with all 14 features")
        return df_clean

    def create_behavior_labels(self, df):
        """Enhanced behavior labeling using all features"""
        def enhanced_label(row):
            try:
                # Multi-factor scoring with safe division
                speed_score = 1 if float(row['avg_speed_kmph']) > 80 else 0
                rpm_score = 1 if float(row['max_rpm']) < 4000 else 0
                brake_score = 1 if float(row['brake_events']) < 10 else 0
                
                # Safe fuel efficiency calculation
                distance = float(row['distance_km'])
                fuel = float(row['fuel_consumed'])
                fuel_score = 1 if distance > 0 and (fuel / distance) < 0.08 else 0
                
                engine_score = 1 if float(row['engine_load']) < 70 else 0
                
                total_score = speed_score + rpm_score + brake_score + fuel_score + engine_score
                
                if total_score >= 4:
                    return "Safe"
                elif total_score >= 2:
                    return "Moderate" 
                else:
                    return "Aggressive"
            except (ValueError, ZeroDivisionError, TypeError):
                return "Moderate"  # Default for problematic data
        
        df['behavior_enhanced'] = df.apply(enhanced_label, axis=1)
        return df

    def train_behavior_model(self, df):
        """Train enhanced behavior prediction model"""
        print("\nTraining enhanced behavior model with all 14 features...")
        
        # Prepare data
        X = df[self.all_features]
        y = df['behavior_enhanced']
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        
        # Train Random Forest (keeping existing model type)
        self.behavior_model = RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=3,
            random_state=42, class_weight='balanced'
        )
        
        self.behavior_model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.behavior_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Enhanced Model Accuracy: {accuracy:.3f}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))
        
        return accuracy

    def train_maintenance_models(self, df):
        """Train predictive maintenance models"""
        print("\nTraining predictive maintenance models...")
        
        maintenance_scores = {}
        
        for component, target_feature in self.maintenance_targets.items():
            print(f"Training {component} prediction model...")
            
            # Create maintenance score based on usage patterns
            if component == 'brake_wear':
                # Higher brake events = more wear
                df[f'{component}_score'] = np.clip(df['brake_events'].astype(float) / 20.0, 0, 1)
                
            elif component == 'tire_wear':
                # Deviation from optimal pressure (32 PSI) = more wear
                df[f'{component}_score'] = np.clip(abs(df['tire_pressure'].astype(float) - 32) / 10.0, 0, 1)
                
            elif component == 'engine_stress':
                # High RPM + high load = more stress
                rpm_norm = df['max_rpm'].astype(float) / 6000.0
                load_norm = df['engine_load'].astype(float) / 100.0
                df[f'{component}_score'] = np.clip((rpm_norm + load_norm) / 2.0, 0, 1)
                
            elif component == 'fuel_efficiency':
                # Higher fuel consumption per km = lower efficiency
                # Safe division to avoid division by zero
                distance = df['distance_km'].astype(float)
                fuel = df['fuel_consumed'].astype(float)
                efficiency = np.where(distance > 0, fuel / distance, 0)
                df[f'{component}_score'] = np.clip(efficiency / 0.15, 0, 1)
            
            # Train regression model
            X = df[self.all_features].astype(float)
            y = df[f'{component}_score'].astype(float)
            
            X_scaled = self.scaler.fit_transform(X)
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            
            self.maintenance_models[component] = model
            maintenance_scores[component] = mse
            
            print(f"{component} model MSE: {mse:.4f}")
        
        return maintenance_scores

    def predict_behavior(self, trip_data):
        """Predict driving behavior with enhanced features"""
        if self.behavior_model is None:
            return {"error": "Model not trained"}
        
        try:
            # Extract all 14 features
            features = []
            for feature in self.all_features:
                value = trip_data.get(feature, 0.0)
                if value is None:
                    value = 0.0
                features.append(float(value))
            
            # Scale and predict
            X = np.array(features).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            prediction = self.behavior_model.predict(X_scaled)[0]
            probabilities = self.behavior_model.predict_proba(X_scaled)[0]
            
            behavior = self.label_encoder.inverse_transform([prediction])[0]
            confidence = float(max(probabilities)) * 100
            
            return {
                'behavior_class': behavior,
                'confidence': confidence,
                'model_used': 'Enhanced Random Forest (14 features)',
                'features_used': self.all_features,
                'feature_count': len(self.all_features)
            }
            
        except Exception as e:
            return {"error": str(e)}

    def predict_maintenance(self, trip_data):
        """Predict maintenance needs"""
        if not self.maintenance_models:
            return {"error": "Maintenance models not trained"}
        
        try:
            # Extract features
            features = []
            for feature in self.all_features:
                value = trip_data.get(feature, 0.0)
                if value is None:
                    value = 0.0
                features.append(float(value))
            
            X = np.array(features).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            predictions = {}
            alerts = []
            
            for component, model in self.maintenance_models.items():
                score = model.predict(X_scaled)[0]
                predictions[component] = {
                    'wear_score': float(score),
                    'status': self._get_maintenance_status(score),
                    'days_until_service': self._estimate_service_days(score)
                }
                
                # Generate alerts
                if score > 0.7:
                    alerts.append({
                        'component': component,
                        'severity': 'high',
                        'message': f"{component.replace('_', ' ').title()} needs attention soon",
                        'estimated_days': self._estimate_service_days(score)
                    })
                elif score > 0.5:
                    alerts.append({
                        'component': component,
                        'severity': 'medium', 
                        'message': f"Monitor {component.replace('_', ' ')} closely",
                        'estimated_days': self._estimate_service_days(score)
                    })
            
            return {
                'predictions': predictions,
                'alerts': alerts,
                'overall_health': self._calculate_overall_health(predictions)
            }
            
        except Exception as e:
            return {"error": str(e)}

    def _get_maintenance_status(self, score):
        """Convert score to status"""
        if score < 0.3:
            return "Good"
        elif score < 0.6:
            return "Fair"
        elif score < 0.8:
            return "Poor"
        else:
            return "Critical"

    def _estimate_service_days(self, score):
        """Estimate days until service needed"""
        if score < 0.3:
            return 90
        elif score < 0.6:
            return 60
        elif score < 0.8:
            return 30
        else:
            return 7

    def _calculate_overall_health(self, predictions):
        """Calculate overall vehicle health score"""
        scores = [pred['wear_score'] for pred in predictions.values()]
        avg_score = np.mean(scores)
        
        if avg_score < 0.3:
            return {"score": 90, "status": "Excellent"}
        elif avg_score < 0.5:
            return {"score": 75, "status": "Good"}
        elif avg_score < 0.7:
            return {"score": 60, "status": "Fair"}
        else:
            return {"score": 40, "status": "Poor"}

    def save_models(self, output_dir='ml_model'):
        """Save all trained models"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save behavior model
        if self.behavior_model:
            joblib.dump(self.behavior_model, f'{output_dir}/enhanced_behavior_model.pkl')
            joblib.dump(self.scaler, f'{output_dir}/enhanced_scaler.pkl')
            joblib.dump(self.label_encoder, f'{output_dir}/enhanced_label_encoder.pkl')
        
        # Save maintenance models
        for component, model in self.maintenance_models.items():
            joblib.dump(model, f'{output_dir}/maintenance_{component}_model.pkl')
        
        # Save model info
        model_info = {
            'model_type': 'Enhanced Random Forest',
            'features': self.all_features,
            'feature_count': len(self.all_features),
            'behavior_classes': self.label_encoder.classes_.tolist() if self.behavior_model else [],
            'maintenance_components': list(self.maintenance_targets.keys()),
            'created_at': datetime.now().isoformat(),
            'improvements': [
                'Uses all 14 collected features instead of 6',
                'Predictive maintenance capabilities',
                'Enhanced behavior classification',
                'Component-specific wear prediction'
            ]
        }
        
        with open(f'{output_dir}/enhanced_model_info.json', 'w') as f:
            json.dump(model_info, f, indent=2)
        
        print(f"\n✅ Enhanced models saved to {output_dir}/")
        return model_info

def main():
    """Train and save enhanced models"""
    print("🚀 Training Enhanced Vehicle ML Models")
    print("=" * 50)
    
    # Initialize enhanced ML system
    ml_system = EnhancedVehicleML()
    
    # Load data
    df = ml_system.load_data()
    
    if len(df) < 50:
        print("❌ Insufficient data for training. Need at least 50 trips.")
        return
    
    # Create enhanced labels
    df = ml_system.create_behavior_labels(df)
    
    # Train models
    behavior_accuracy = ml_system.train_behavior_model(df)
    maintenance_scores = ml_system.train_maintenance_models(df)
    
    # Save models
    model_info = ml_system.save_models()
    
    print("\n🎉 Enhanced ML Training Complete!")
    print(f"Behavior Model Accuracy: {behavior_accuracy:.1%}")
    print(f"Features Used: {len(ml_system.all_features)} (vs 6 in original)")
    print(f"Maintenance Components: {len(ml_system.maintenance_models)}")
    
    # Test prediction
    print("\n🧪 Testing Enhanced Prediction...")
    sample_trip = {
        'avg_speed_kmph': 75, 'max_speed': 95, 'max_rpm': 3500,
        'fuel_consumed': 4.2, 'brake_events': 8, 'steering_angle': 15,
        'angular_velocity': 2.1, 'acceleration': 3.2, 'gear_position': 4,
        'tire_pressure': 32, 'engine_load': 65, 'throttle_position': 45,
        'brake_pressure': 25, 'trip_duration': 35, 'distance_km': 25
    }
    
    behavior_result = ml_system.predict_behavior(sample_trip)
    maintenance_result = ml_system.predict_maintenance(sample_trip)
    
    print(f"Behavior: {behavior_result.get('behavior_class')} ({behavior_result.get('confidence', 0):.1f}% confidence)")
    print(f"Overall Health: {maintenance_result.get('overall_health', {}).get('status', 'Unknown')}")
    
    return ml_system

if __name__ == "__main__":
    main()