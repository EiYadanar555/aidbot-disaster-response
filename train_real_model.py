# train_real_model.py
from pathlib import Path
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
import joblib

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True, parents=True)

print("Loading disaster data...")
df = pd.read_csv('Asia_1900_2021_DISASTERS.csv')
print(f"Loaded {len(df)} rows")

TARGET = 'Disaster Type'
numeric_features = ['Start Year', 'Start Month', 'Start Day', 'Total Deaths', 'No Injured', 'No Affected', 'Total Affected']
categorical_features = ['Country', 'Region', 'Continent', 'Disaster Group']

print("\nCleaning data...")
df = df[df[TARGET].notna()].copy()

for col in numeric_features:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
df[numeric_features] = df[numeric_features].fillna(0)
df[categorical_features] = df[categorical_features].fillna('Unknown')

print(f"After cleaning: {len(df)} rows")
print(f"\nDisaster types in dataset:")
print(df[TARGET].value_counts())

# FILTER OUT RARE CLASSES - Keep only disaster types with at least 20 examples
value_counts = df[TARGET].value_counts()
common_disasters = value_counts[value_counts >= 20].index
df = df[df[TARGET].isin(common_disasters)].copy()

print(f"\nAfter filtering rare disasters: {len(df)} rows")
print(f"Keeping disaster types: {list(common_disasters)}")

X = df[numeric_features + categorical_features].copy()
y = df[TARGET].copy()

print(f"\nFeatures shape: {X.shape}")
print(f"Target shape: {y.shape}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set: {len(X_train)} samples")
print(f"Test set: {len(X_test)} samples")

preprocessor = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ]
)

pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', DecisionTreeClassifier(max_depth=10, random_state=42, min_samples_split=20))
])

print("\nTraining model...")
pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted', zero_division=0)

try:
    y_pred_proba = pipeline.predict_proba(X_test)
    label_encoder = LabelEncoder()
    y_test_encoded = label_encoder.fit_transform(y_test)
    roc_auc = roc_auc_score(y_test_encoded, y_pred_proba, multi_class='ovr', average='weighted')
except Exception as e:
    print(f"Could not calculate ROC-AUC: {e}")
    roc_auc = 0.0

print(f"\n=== Model Performance ===")
print(f"Accuracy:  {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall:    {recall:.3f}")
print(f"F1 Score:  {f1:.3f}")
print(f"ROC-AUC:   {roc_auc:.3f}")

joblib.dump(pipeline, MODELS_DIR / "tree_baseline.joblib")
print(f"\n✓ Saved tree_baseline.joblib")

metrics = {
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "roc_auc": float(roc_auc)
}

with open(MODELS_DIR / "metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print("✓ Saved metrics.json")

sample_for_prediction = X_test.head(20).copy()
sample_for_prediction.to_csv(MODELS_DIR / "sample_features_for_prediction.csv", index=False)
print("✓ Saved sample_features_for_prediction.csv")

print("\n" + "="*50)
print("SUCCESS! Real disaster model trained.")
print("="*50)