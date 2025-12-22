import pandas as pd
import sqlite3
from sklearn.model_selection import GridSearchCV, train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
import seaborn as sns

print("=== HYPERPARAMETER OPTIMIZATION FOR RANDOM FOREST ===")
print("Baseline Random Forest achieved: 91.67% accuracy")
print("Applying GridSearchCV to optimize further...\n")

# Load and clean data
DB_PATH = 'instance/trips.db'
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM trips;", conn)
conn.close()

features = ['avg_speed_kmph', 'max_speed', 'throttle_position', 'engine_load']
target = 'score'

df_clean = df.dropna(subset=features + [target]).copy()
df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
df_clean = df_clean[df_clean[target].isin(['Good', 'Average', 'Risky'])]

# Convert to numeric
for col in features:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

df_clean.dropna(subset=features, inplace=True)

X = df_clean[features].values  # Convert to numpy array
y = df_clean[target]

le = LabelEncoder()
y_encoded = le.fit_transform(y)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.3, random_state=42, stratify=y_encoded)

# Define smaller parameter grid for faster optimization
param_grid = {
    'n_estimators': [100, 150, 200],
    'max_depth': [6, 8, 10],
    'min_samples_leaf': [8, 10, 15],
    'max_features': ['sqrt', 0.8]
}

print(f"Testing {len(param_grid['n_estimators']) * len(param_grid['max_depth']) * len(param_grid['min_samples_leaf']) * len(param_grid['max_features'])} parameter combinations...")

# GridSearchCV with 3-fold cross-validation for speed
rf = RandomForestClassifier(random_state=42)
grid_search = GridSearchCV(
    rf, 
    param_grid, 
    cv=3, 
    scoring='f1_macro',
    n_jobs=-1,
    verbose=1
)

# Fit the grid search
grid_search.fit(X_train, y_train)

# Get best model
best_rf = grid_search.best_estimator_
y_pred = best_rf.predict(X_test)

# Calculate metrics
optimized_accuracy = accuracy_score(y_test, y_pred)
optimized_f1 = grid_search.best_score_

print("\n=== OPTIMIZATION RESULTS ===")
print(f"Best parameters: {grid_search.best_params_}")
print(f"Best F1-score (CV): {optimized_f1:.6f}")
print(f"Optimized accuracy: {optimized_accuracy:.6f}")
print(f"Improvement: {optimized_accuracy - 0.916667:.4f} ({((optimized_accuracy/0.916667 - 1)*100):+.2f}%)")

print("\nClassification Report (Optimized):")
print(classification_report(y_test, y_pred, target_names=le.classes_))

# Feature importance
feature_importance = pd.DataFrame({
    'Feature': features,
    'Importance': best_rf.feature_importances_
}).sort_values('Importance', ascending=False)

print("\nOptimized Feature Importance:")
print(feature_importance.to_string(index=False, float_format='%.6f'))

# Generate Charts
print("\nGenerating optimization charts...")

# 1. Confusion Matrix
plt.figure(figsize=(8, 6))
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=le.classes_, yticklabels=le.classes_)
plt.title('Confusion Matrix - Optimized Random Forest')
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.tight_layout()
plt.savefig('ml_model/optimized_confusion_matrix.png', dpi=300, bbox_inches='tight')
plt.show()

# 2. Feature Importance Chart
plt.figure(figsize=(10, 6))
sns.barplot(data=feature_importance, x='Importance', y='Feature', palette='viridis')
plt.title('Feature Importance - Optimized Random Forest')
plt.xlabel('Importance Score')
plt.tight_layout()
plt.savefig('ml_model/optimized_feature_importance.png', dpi=300, bbox_inches='tight')
plt.show()

# 3. Performance Comparison Chart
performance_data = pd.DataFrame({
    'Model': ['Baseline RF', 'Optimized RF'],
    'Accuracy': [0.916667, optimized_accuracy],
    'F1-Score': [0.798001, optimized_f1]
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Accuracy comparison
sns.barplot(data=performance_data, x='Model', y='Accuracy', ax=ax1, palette=['lightcoral', 'lightgreen'])
ax1.set_title('Accuracy Comparison')
ax1.set_ylim(0.85, 0.95)
for i, v in enumerate(performance_data['Accuracy']):
    ax1.text(i, v + 0.005, f'{v:.4f}', ha='center', va='bottom', fontweight='bold')

# F1-Score comparison
sns.barplot(data=performance_data, x='Model', y='F1-Score', ax=ax2, palette=['lightcoral', 'lightgreen'])
ax2.set_title('F1-Score Comparison')
ax2.set_ylim(0.75, 0.82)
for i, v in enumerate(performance_data['F1-Score']):
    ax2.text(i, v + 0.002, f'{v:.4f}', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('ml_model/performance_comparison.png', dpi=300, bbox_inches='tight')
plt.show()

# 4. Parameter Impact Visualization
results_df = pd.DataFrame(grid_search.cv_results_)
top_10_results = results_df.nlargest(10, 'mean_test_score')

plt.figure(figsize=(12, 8))
params_str = top_10_results.apply(lambda x: f"n_est:{x['param_n_estimators']}\ndepth:{x['param_max_depth']}\nleaf:{x['param_min_samples_leaf']}", axis=1)
sns.barplot(x=top_10_results['mean_test_score'], y=range(len(top_10_results)), palette='viridis')
plt.yticks(range(len(top_10_results)), params_str)
plt.xlabel('F1-Score (CV)')
plt.ylabel('Parameter Combinations')
plt.title('Top 10 Parameter Combinations Performance')
plt.tight_layout()
plt.savefig('ml_model/parameter_impact.png', dpi=300, bbox_inches='tight')
plt.show()

# Save optimized model
joblib.dump(best_rf, 'ml_model/optimized_driving_model.pkl')
joblib.dump(le, 'ml_model/optimized_label_encoder.pkl')

# Save optimization info
optimization_info = {
    'baseline_accuracy': 0.916667,
    'optimized_accuracy': float(optimized_accuracy),
    'improvement': float(optimized_accuracy - 0.916667),
    'best_params': grid_search.best_params_,
    'best_f1_cv': float(optimized_f1),
    'feature_importance': feature_importance.to_dict('records')
}

with open('ml_model/optimization_results.json', 'w') as f:
    json.dump(optimization_info, f, indent=2)

print(f"\nOptimized model saved with {optimized_accuracy:.4f} accuracy!")
print("Charts saved: confusion_matrix.png, feature_importance.png, performance_comparison.png, parameter_impact.png")