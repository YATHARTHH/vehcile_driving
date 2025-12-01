"""
optimize_model.py
-----------------
Performs hyperparameter tuning on a Random Forest classifier
to achieve optimal performance for driver behavior classification.

How to run (from project root):
    python -m ml_model.optimize_model
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import time
import joblib
import json
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, f1_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# --- 1. Load and Prepare Data ---
logger.info("Loading data from database...")
DB_PATH = 'instance/trips.db'
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM trips;", conn)
conn.close()
logger.info(f"Loaded {len(df)} trips from the database.")

features = [
    'avg_speed_kmph', 'max_speed', 'throttle_position',
    'engine_load', 'trip_duration', 'distance_km'
]
target = 'score'

# Clean the data
df_clean = df.dropna(subset=features + [target]).copy()
df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
valid_scores = ['Good', 'Average', 'Risky']
df_clean = df_clean[df_clean[target].isin(valid_scores)]

for col in features:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
df_clean.dropna(subset=features, inplace=True)

# Remove duplicates
duplicates = df_clean.duplicated(subset=features)
logger.info(f"Duplicate feature rows removed: {duplicates.sum()}")
df_clean = df_clean.drop_duplicates(subset=features)

# Check minimum data
if len(df_clean) < 20:
    logger.warning("Not enough clean data to train. Exiting.")
    exit()

# --- 2. Encode Target and Scale Features ---
X = df_clean[features]
y = df_clean[target]
logger.info(f"Class distribution:\n{y.value_counts()}")

le = LabelEncoder()
y_encoded = le.fit_transform(y)
logger.info(f"Target classes: {le.classes_.tolist()}")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_encoded, test_size=0.3, random_state=42, stratify=y_encoded
)

# --- 3. Dummy Classifier Baseline ---
dummy = DummyClassifier(strategy='most_frequent')
dummy.fit(X_train, y_train)
dummy_pred = dummy.predict(X_test)
dummy_f1 = f1_score(y_test, dummy_pred, average='macro')
logger.info("--- Dummy Classifier Baseline ---")
logger.info("\n" + classification_report(y_test, dummy_pred, target_names=le.classes_))

# --- 4. Baseline Random Forest ---
baseline_rf = RandomForestClassifier(random_state=42)
baseline_rf.fit(X_train, y_train)
baseline_pred = baseline_rf.predict(X_test)
baseline_accuracy = accuracy_score(y_test, baseline_pred)
baseline_f1 = f1_score(y_test, baseline_pred, average='macro')
logger.info("--- Baseline Random Forest ---")
logger.info(f"Baseline Accuracy: {baseline_accuracy:.4f}")
logger.info(f"Baseline F1 Score: {baseline_f1:.4f}")

# --- 5. Grid Search for Optimized RF ---
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [6, 10, 15, None],
    'min_samples_leaf': [1, 2, 4],
    'min_samples_split': [2, 5],
    'max_features': ['sqrt', 'log2'],
    'bootstrap': [True, False]
}

logger.info("Starting GridSearchCV...")
start_time = time.time()

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
rf = RandomForestClassifier(random_state=42)

grid_search = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    scoring='f1_macro',
    cv=skf,
    n_jobs=-1,
    verbose=1
)
grid_search.fit(X_train, y_train)
end_time = time.time()

logger.info(f"Grid Search completed in {end_time - start_time:.2f} seconds")
logger.info("Best Parameters:")
logger.info(json.dumps(grid_search.best_params_, indent=2))

best_model = grid_search.best_estimator_

# --- 6. Evaluate Optimized Model ---
y_pred = best_model.predict(X_test)
optimized_accuracy = accuracy_score(y_test, y_pred)
optimized_f1 = f1_score(y_test, y_pred, average='macro')
logger.info(f"Optimized Accuracy: {optimized_accuracy:.4f}")
logger.info(f"Optimized F1 Score: {optimized_f1:.4f}")
logger.info("--- Classification Report ---\n" + classification_report(y_test, y_pred, target_names=le.classes_))

if optimized_accuracy >= 0.99:
    logger.warning("⚠️ Accuracy is suspiciously high. Check for data leakage.")

# --- 7. Post-Fit Cross-Validation ---
cv_scores = cross_val_score(best_model, X_scaled, y_encoded, cv=skf, scoring='f1_macro')
logger.info(f"Post-fit F1 Macro CV: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# --- 8. Confusion Matrix ---
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=le.classes_, yticklabels=le.classes_)
plt.title('Confusion Matrix - Optimized Random Forest')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.tight_layout()
conf_matrix_path = 'ml_model/confusion_matrix.png'
plt.savefig(conf_matrix_path)
plt.close()
logger.info(f"Confusion matrix saved to {conf_matrix_path}")

# --- 9. Feature Importance ---
importance_df = pd.DataFrame({
    'Feature': features,
    'Importance': best_model.feature_importances_
}).sort_values(by='Importance', ascending=False)

logger.info("Feature Importances:\n" + importance_df.to_string(index=False))

plt.figure(figsize=(8, 4))
sns.barplot(data=importance_df, x='Importance', y='Feature', palette='viridis')
plt.title('Feature Importance - Optimized Random Forest')
plt.tight_layout()
feat_imp_path = 'ml_model/feature_importance.png'
plt.savefig(feat_imp_path)
plt.close()
logger.info(f"Feature importance plot saved to {feat_imp_path}")

# --- 10. Save Artifacts ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs('ml_model', exist_ok=True)

joblib.dump(best_model, f'ml_model/driving_model_{timestamp}.pkl')
joblib.dump(scaler, f'ml_model/scaler_{timestamp}.pkl')
joblib.dump(le, f'ml_model/label_encoder_{timestamp}.pkl')

model_info = {
    'best_model_name': 'Optimized Random Forest',
    'features': features,
    'accuracy': float(optimized_accuracy),
    'baseline_accuracy': float(baseline_accuracy),
    'dummy_f1': float(dummy_f1),
    'baseline_f1': float(baseline_f1),
    'optimized_f1': float(optimized_f1),
    'f1_score_cv': grid_search.best_score_,
    'post_fit_cv_f1': cv_scores.mean(),
    'needs_scaling': True,
    'target_classes': le.classes_.tolist(),
    'training_data_size': len(df_clean),
    'test_split_size': len(X_test),
    'best_params': grid_search.best_params_,
    'timestamp': timestamp
}

with open(f'ml_model/model_info_{timestamp}.json', 'w') as f:
    json.dump(model_info, f, indent=2)

# --- 11. Final Model Comparison ---
logger.info("=== Final Model Comparison Summary ===")
comparison_df = pd.DataFrame({
    'Model': ['Dummy', 'Baseline RF', 'Optimized RF'],
    'Accuracy': [
        accuracy_score(y_test, dummy_pred),
        baseline_accuracy,
        optimized_accuracy
    ],
    'F1-Score': [
        dummy_f1,
        baseline_f1,
        grid_search.best_score_
    ],
    'Parameters': ['Most Frequent', 'Default', 'Tuned']
})
logger.info("\n" + comparison_df.to_string(index=False))

logger.info("✅ Optimized model and all artifacts saved successfully!")
