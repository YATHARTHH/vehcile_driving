#!/usr/bin/env python3
"""
Model Comparison Script
======================
Compare the original 6-feature model with the enhanced 14-feature model
"""

import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def compare_models():
    print("🔍 ML Model Comparison")
    print("=" * 50)
    
    # Check original model
    original_info_path = 'ml_model/model_info.json'
    enhanced_info_path = 'ml_model/enhanced_model_info.json'
    
    print("📊 ORIGINAL MODEL:")
    if os.path.exists(original_info_path):
        with open(original_info_path, 'r') as f:
            original_info = json.load(f)
        
        print(f"  Model Type: {original_info.get('best_model_name', 'Unknown')}")
        print(f"  Features: {len(original_info.get('features', []))} features")
        print(f"  Feature List: {', '.join(original_info.get('features', []))}")
        print(f"  Accuracy: {original_info.get('accuracy', 0):.1%}")
        print(f"  F1 Score: {original_info.get('f1_score', 0):.3f}")
        print(f"  Training Data: {original_info.get('training_data_size', 0)} samples")
    else:
        print("  ❌ Original model not found")
    
    print("\n🚀 ENHANCED MODEL:")
    if os.path.exists(enhanced_info_path):
        with open(enhanced_info_path, 'r') as f:
            enhanced_info = json.load(f)
        
        print(f"  Model Type: {enhanced_info.get('model_type', 'Unknown')}")
        print(f"  Features: {enhanced_info.get('feature_count', 0)} features")
        print(f"  Behavior Classes: {', '.join(enhanced_info.get('behavior_classes', []))}")
        print(f"  Maintenance Components: {len(enhanced_info.get('maintenance_components', []))}")
        print(f"  Components: {', '.join(enhanced_info.get('maintenance_components', []))}")
        print(f"  Created: {enhanced_info.get('created_at', 'Unknown')}")
        
        print("\n  🎯 IMPROVEMENTS:")
        for improvement in enhanced_info.get('improvements', []):
            print(f"    ✅ {improvement}")
    else:
        print("  ❌ Enhanced model not found")
        print("  💡 Run 'python train_enhanced_model.py' to create it")
    
    print("\n📈 FEATURE COMPARISON:")
    if os.path.exists(original_info_path) and os.path.exists(enhanced_info_path):
        with open(original_info_path, 'r') as f:
            original_info = json.load(f)
        with open(enhanced_info_path, 'r') as f:
            enhanced_info = json.load(f)
        
        original_features = set(original_info.get('features', []))
        enhanced_features = set(enhanced_info.get('features', []))
        
        new_features = enhanced_features - original_features
        
        print(f"  Original Features ({len(original_features)}): {', '.join(sorted(original_features))}")
        print(f"  Enhanced Features ({len(enhanced_features)}): {', '.join(sorted(enhanced_features))}")
        
        if new_features:
            print(f"  🆕 New Features Added ({len(new_features)}): {', '.join(sorted(new_features))}")
        
        improvement_pct = ((len(enhanced_features) - len(original_features)) / len(original_features)) * 100
        print(f"  📊 Feature Increase: +{improvement_pct:.0f}%")
    
    print("\n🔧 CAPABILITIES COMPARISON:")
    print("  Original Model:")
    print("    ✅ Driving behavior prediction")
    print("    ❌ Predictive maintenance")
    print("    ❌ Component wear analysis")
    print("    ❌ Maintenance scheduling")
    
    print("  Enhanced Model:")
    print("    ✅ Driving behavior prediction (improved)")
    print("    ✅ Predictive maintenance")
    print("    ✅ Component wear analysis")
    print("    ✅ Maintenance scheduling")
    print("    ✅ Health scoring")
    print("    ✅ Alert generation")

def test_prediction_comparison():
    """Test both models with sample data"""
    print("\n🧪 PREDICTION COMPARISON TEST")
    print("=" * 30)
    
    # Sample trip data
    sample_trip = {
        'avg_speed_kmph': 75,
        'max_speed': 95, 
        'max_rpm': 3500,
        'fuel_consumed': 4.2,
        'brake_events': 8,
        'steering_angle': 15,
        'angular_velocity': 2.1,
        'acceleration': 3.2,
        'gear_position': 4,
        'tire_pressure': 32,
        'engine_load': 65,
        'throttle_position': 45,
        'brake_pressure': 25,
        'trip_duration': 35,
        'distance_km': 25
    }
    
    print("Sample Trip Data:")
    for key, value in sample_trip.items():
        print(f"  {key}: {value}")
    
    # Test original model
    print("\n📊 Original Model Prediction:")
    try:
        from ml_model.model_utils import load_artifacts, predict_behavior
        model, scaler, le, model_info = load_artifacts()
        result = predict_behavior(sample_trip, model, scaler, le, model_info)
        
        print(f"  Behavior: {result.get('behavior_class', 'Unknown')}")
        print(f"  Confidence: {result.get('confidence', 0):.1f}%")
        print(f"  Model: {result.get('model_used', 'Unknown')}")
        print(f"  Features Used: {len(result.get('features_used', []))}")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
    
    # Test enhanced model
    print("\n🚀 Enhanced Model Prediction:")
    try:
        from ml_model.enhanced_model_utils import (
            load_enhanced_artifacts, predict_enhanced_behavior, predict_maintenance_needs
        )
        
        loaded, msg = load_enhanced_artifacts()
        if loaded:
            behavior_result = predict_enhanced_behavior(sample_trip)
            maintenance_result = predict_maintenance_needs(sample_trip)
            
            print(f"  Behavior: {behavior_result.get('behavior_class', 'Unknown')}")
            print(f"  Confidence: {behavior_result.get('confidence', 0):.1f}%")
            print(f"  Model: {behavior_result.get('model_used', 'Unknown')}")
            print(f"  Features Used: {behavior_result.get('features_used', 0)}")
            
            if not maintenance_result.get('error'):
                overall_health = maintenance_result.get('overall_health', {})
                alerts = maintenance_result.get('alerts', [])
                
                print(f"  Overall Health: {overall_health.get('score', 0)}/100 ({overall_health.get('status', 'Unknown')})")
                print(f"  Maintenance Alerts: {len(alerts)}")
                
                for alert in alerts[:2]:  # Show first 2 alerts
                    print(f"    - {alert['component']}: {alert['severity']} priority")
        else:
            print(f"  ❌ {msg}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")

if __name__ == "__main__":
    compare_models()
    test_prediction_comparison()
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Train the enhanced model: python train_enhanced_model.py")
    print("2. Restart your Flask app to use enhanced predictions")
    print("3. Check trip details for improved analysis")
    print("4. Monitor maintenance predictions for proactive care")