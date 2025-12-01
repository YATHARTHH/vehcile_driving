import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, precision_score, recall_score
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import joblib
import os
import json

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier

# --- 1. Load Data From Database ---
print("Loading data from database...")
DB_PATH = 'instance/trips.db'
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM trips;", conn)
conn.close()
print(f"Loaded {len(df)} trips from the database.")

# --- 2. Preprocess Data ---
features = [
    'avg_speed_kmph',
    'max_speed',
    'throttle_position',
    'engine_load',
    'trip_duration',
    'distance_km'
]
target = 'score'

df_clean = df.dropna(subset=features + [target]).copy()
df_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
valid_scores = ['Good', 'Average', 'Risky']
df_clean = df_clean[df_clean[target].isin(valid_scores)]

for col in features:
    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

df_clean.dropna(subset=features, inplace=True)

# --- Check for duplicate rows ---
duplicates = df_clean.duplicated(subset=features)
print(f"Duplicate feature rows: {duplicates.sum()}")

if len(df_clean) < 20:
    print("Not enough clean data to train. Exiting.")
    exit(1)

X = df_clean[features]
y = df_clean[target]

le = LabelEncoder()
y_encoded = le.fit_transform(y)
print(f"Target classes: {le.classes_}")

# Scale data for applicable models
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# --- 3. Define Models with Regularization ---
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    "Decision Tree": DecisionTreeClassifier(random_state=42, max_depth=6),
    "k-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5),
    "SVM (RBF Kernel)": SVC(random_state=42, probability=True),
    "Random Forest": RandomForestClassifier(
        random_state=42,
        n_estimators=300,
        max_depth=11,
        min_samples_leaf=5,
        max_features='sqrt'
    ),
    "Gradient Boosting": GradientBoostingClassifier(
        random_state=42,
        learning_rate=0.01,
        n_estimators=150,
        max_depth=2,
        subsample=0.7,
        min_samples_leaf=15,
        max_features='sqrt',
        n_iter_no_change=5,
        validation_fraction=0.2
    ),
    "MLP (Neural Network)": MLPClassifier(max_iter=1000, random_state=42, hidden_layer_sizes=(64, 32))
}

# --- 4. Evaluate Models with Stratified K-Fold ---
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
results = {}

for name, model in models.items():
    print(f"\n--- Evaluating {name} ---")
    use_scaled = name in ["Logistic Regression", "k-Nearest Neighbors", "SVM (RBF Kernel)", "MLP (Neural Network)"]
    X_data = X_scaled if use_scaled else X.values

    scores = cross_val_score(model, X_data, y_encoded, cv=skf, scoring='f1_macro')
    print(f"F1 Macro CV: {scores.mean():.4f} ± {scores.std():.4f}")

    results[name] = {
        "f1_macro_cv_mean": scores.mean(),
        "f1_macro_cv_std": scores.std()
    }

# --- 4b. Final Model Comparison Table ---
comparison_results = []

for name, model in models.items():
    use_scaled = name in ["Logistic Regression", "k-Nearest Neighbors", "SVM (RBF Kernel)", "MLP (Neural Network)"]
    X_data = X_scaled if use_scaled else X.values

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_data, y_encoded, test_size=0.3, random_state=42, stratify=y_encoded
    )

    model.fit(X_train_c, y_train_c)
    y_pred_c = model.predict(X_test_c)

    comparison_results.append({
        'Model': name,
        'Accuracy': accuracy_score(y_test_c, y_pred_c),
        'Precision (macro)': precision_score(y_test_c, y_pred_c, average='macro', zero_division=0),
        'Recall (macro)': recall_score(y_test_c, y_pred_c, average='macro', zero_division=0),
        'F1-Score (macro)': classification_report(y_test_c, y_pred_c, output_dict=True)['macro avg']['f1-score']
    })

comparison_df = pd.DataFrame(comparison_results)
comparison_df = comparison_df.sort_values(by='F1-Score (macro)', ascending=False)

print("\n=== Final Model Comparison ===")
print(comparison_df.to_string(index=False, float_format='%.6f'))

# --- 5. Select and Train Best Model ---
best_model_name = max(results, key=lambda k: results[k]['f1_macro_cv_mean'])
print(f"\nBest Model: {best_model_name}")
best_model = models[best_model_name]
use_scaled = best_model_name in ["Logistic Regression", "k-Nearest Neighbors", "SVM (RBF Kernel)", "MLP (Neural Network)"]
X_final = X_scaled if use_scaled else X.values

X_train, X_test, y_train, y_test = train_test_split(X_final, y_encoded, test_size=0.3, random_state=42, stratify=y_encoded)
best_model.fit(X_train, y_train)
y_pred = best_model.predict(X_test)

final_accuracy = accuracy_score(y_test, y_pred)
final_report = classification_report(y_test, y_pred, target_names=le.classes_)
print(f"\nFinal Accuracy: {final_accuracy:.4f}")
print("\nClassification Report:")
print(final_report)

cv_post_scores = cross_val_score(best_model, X_final, y_encoded, cv=skf, scoring='f1_macro')
print(f"Post-fit F1 Macro CV: {cv_post_scores.mean():.4f} ± {cv_post_scores.std():.4f}")

# --- 6. Show Confusion Matrix ---
cm = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=le.classes_, yticklabels=le.classes_)
plt.title(f'Confusion Matrix - {best_model_name}')
plt.xlabel('Predicted Label')
plt.ylabel('True Label')
plt.tight_layout()
plt.show()

# --- 7. Feature Importance (for tree-based models) ---
if hasattr(best_model, 'feature_importances_'):
    importance_df = pd.DataFrame({
        'Feature': features,
        'Importance': best_model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    print("\nFeature Importances:")
    print(importance_df.to_string(index=False))

    plt.figure(figsize=(8, 4))
    sns.barplot(data=importance_df, x='Importance', y='Feature', palette='viridis')
    plt.title(f'Feature Importance - {best_model_name}')
    plt.tight_layout()
    plt.show()

# --- 8. Save Model and Artifacts ---
os.makedirs('ml_model', exist_ok=True)
joblib.dump(best_model, 'ml_model/driving_model.pkl')
joblib.dump(scaler, 'ml_model/scaler.pkl')
joblib.dump(le, 'ml_model/label_encoder.pkl')

model_info = {
    'best_model_name': best_model_name,
    'features': features,
    'accuracy': float(final_accuracy),
    'f1_score': results[best_model_name]['f1_macro_cv_mean'],
    'post_fit_cv_f1': cv_post_scores.mean(),
    'needs_scaling': use_scaled,
    'target_classes': le.classes_.tolist(),
    'training_data_size': len(df_clean),
    'test_split_size': len(X_test)
}

with open('ml_model/model_info.json', 'w') as f:
    json.dump(model_info, f, indent=2)

print("\n✅ Model artifacts saved successfully, Now go for optimized!")
