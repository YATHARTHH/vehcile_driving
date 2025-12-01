# #!/usr/bin/env python3
# """
# model_utils.py - ML Model Loading Utilities
# -------------------------------------------
# Loads model, scaler, label encoder, and metadata for predictions.
# """
# import os
# import json
# import joblib
# import numpy as np

# def load_artifacts(out_dir='ml_model'):
#     paths = {
#         'model': os.path.join(out_dir, 'driving_model.pkl'),
#         'scaler': os.path.join(out_dir, 'scaler.pkl'),
#         'le': os.path.join(out_dir, 'label_encoder.pkl'),
#         'info': os.path.join(out_dir, 'model_info.json')
#     }
#     missing = [p for p in paths.values() if not os.path.exists(p)]
#     if missing:
#         raise FileNotFoundError(f"Missing artifacts: {missing}. Run benchmark or optimize first.")

#     model = joblib.load(paths['model'])
#     scaler = joblib.load(paths['scaler'])
#     le = joblib.load(paths['le'])
#     with open(paths['info'], 'r') as f:
#         info = json.load(f)

#     le.classes_ = np.array(info['target_classes'])
#     print(f"Loaded {info['best_model_name']} (Acc={info['accuracy']:.3f}, F1={info['f1_score']:.3f})")
#     return model, scaler, le, info


# def predict_behavior(trip_data, model, scaler, le, info):
#     features = info['features']
#     values = [float(trip_data.get(f, 0.0) or 0.0) for f in features]
#     X = np.array(values).reshape(1, -1)
#     if info.get('needs_scaling'):
#         X = scaler.transform(X)

#     pred = model.predict(X)[0]
#     conf = 0.0
#     try:
#         conf = max(model.predict_proba(X)[0]) * 100
#     except:
#         pass
#     label = le.inverse_transform([pred])[0]

#     return {
#         'behavior_class': label,
#         'confidence': conf,
#         'model_used': info['best_model_name'],
#         'features_used': features,
#         'feature_values': values
#     }
"""
model_utils.py - ML Model Loading Utilities
-------------------------------------------
Utility functions for loading trained ML model artifacts for dashboard use.
"""
import json
import joblib
import os
import numpy as np

def load_artifacts():
    """
    Load all ML model artifacts (model, scaler, label encoder, metadata)
    
    Returns:
        tuple: (model, scaler, label_encoder, model_info)
    
    Raises:
        FileNotFoundError: If any required artifacts are missing
    """
    paths = {
        "model": "ml_model/driving_model.pkl",
        "scaler": "ml_model/scaler.pkl", 
        "le": "ml_model/label_encoder.pkl",
        "info": "ml_model/model_info.json"
    }
    
    # Check if all files exist
    missing_files = [path for path in paths.values() if not os.path.exists(path)]
    if missing_files:
        raise FileNotFoundError(
            f"Missing ML artifacts: {missing_files}. "
            "Please run 'python -m ml_model.benchmark_models' first."
        )
    
    try:
        # Load artifacts
        model = joblib.load(paths["model"])
        scaler = joblib.load(paths["scaler"])
        le = joblib.load(paths["le"])
        
        with open(paths["info"], 'r') as f:
            info = json.load(f)
        
        print(f"✅ Loaded {info['best_model_name']} model "
              f"(Accuracy: {info['accuracy']:.1%}, F1: {info['f1_score']:.3f})")
        
        return model, scaler, le, info
        
    except Exception as e:
        raise RuntimeError(f"Error loading ML artifacts: {str(e)}")

def predict_behavior(trip_data, model, scaler, le, model_info):
    """
    Predict driving behavior using loaded model artifacts
    
    Args:
        trip_data (dict): Trip data containing required features
        model: Trained ML model
        scaler: Fitted StandardScaler
        le: Fitted LabelEncoder
        model_info (dict): Model metadata
    
    Returns:
        dict: Prediction results with behavior class, confidence, etc.
    """
    try:
        # Extract features in correct order
        features = model_info['features']
        feature_values = []
        
        for feature in features:
            if feature in trip_data:
                value = trip_data[feature]
                # Handle None values
                if value is None:
                    value = 0.0
                feature_values.append(float(value))
            else:
                # Default value for missing features
                feature_values.append(0.0)
        
        # Convert to numpy array
        X = np.array(feature_values).reshape(1, -1)
        
        # Apply scaling if needed
        if model_info['needs_scaling']:
            X = scaler.transform(X)
        
        # Make prediction
        prediction = model.predict(X)[0]
        
        # Get prediction probabilities if available
        try:
            prediction_proba = model.predict_proba(X)[0]
            confidence = float(max(prediction_proba)) * 100
        except:
            confidence = 0.0
        
        # Convert prediction back to label
        behavior_class = le.inverse_transform([prediction])[0]
        
        return {
            'behavior_class': behavior_class,
            'confidence': confidence,
            'model_used': model_info['best_model_name'],
            'features_used': features,
            'feature_values': feature_values
        }
        
    except Exception as e:
        return {
            'behavior_class': 'Unknown',
            'confidence': 0.0,
            'model_used': 'Error',
            'error': str(e)
        }

def get_model_summary():
    """
    Get a summary of the loaded model without loading the actual artifacts
    
    Returns:
        dict: Model summary information
    """
    try:
        with open('ml_model/model_info.json', 'r') as f:
            info = json.load(f)
        return info
    except FileNotFoundError:
        return None
    except Exception as e:
        return {'error': str(e)}
