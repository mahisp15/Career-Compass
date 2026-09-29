import pandas as pd
import numpy as np
import json
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent.parent

AI_JOBS_FILE = BASE_DIR / "data" / "processed" / "ai_jobs_clean.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

SALARY_MODEL_FILE = MODEL_DIR / "salary_model.pkl"
SALARY_PREPROCESSOR_FILE = MODEL_DIR / "salary_preprocessor.pkl"
SALARY_METADATA_FILE = MODEL_DIR / "salary_model_metadata.json"

df = pd.read_csv(AI_JOBS_FILE)
print(f"Loaded dataset: {df.shape}")

# Target: salary_midpoint
# Features: all except salary-related fields
exclude_cols = [
    "job_id", "annual_salary_usd", "salary_min_usd", "salary_max_usd",
    "salary_midpoint", "salary_range", "salary_tier", "posting_date",
    "posting_year", "posting_month"
]

feature_cols = [c for c in df.columns if c not in exclude_cols]

print(f"\nFeature columns ({len(feature_cols)}):")
for c in feature_cols:
    print(f"  {c}: {df[c].dtype}")

# Prepare target
y = df["salary_midpoint"].values

# Prepare features
X = df[feature_cols].copy()

# Process required_skills - create multi-hot encoding for top skills
print("\nProcessing required_skills...")
skill_counts = {}
for skills_str in X["required_skills"].fillna(""):
    for s in skills_str.split("|"):
        s = s.strip()
        if s:
            skill_counts[s] = skill_counts.get(s, 0) + 1

top_skills = sorted(skill_counts.items(), key=lambda x: -x[1])[:50]
top_skill_names = [s[0] for s in top_skills]
print(f"Top 50 skills used as features")

# Create binary features for top skills
for skill in top_skill_names:
    X[f"skill_{skill}"] = X["required_skills"].fillna("").apply(
        lambda x: 1 if skill in [s.strip() for s in x.split("|")] else 0
    )

# Drop original required_skills
X = X.drop(columns=["required_skills"])

# Handle categorical columns
categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
numerical_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()

print(f"\nCategorical columns ({len(categorical_cols)}): {categorical_cols}")
print(f"Numerical columns ({len(numerical_cols)}): {numerical_cols}")

# Fill missing values
for col in categorical_cols:
    X[col] = X[col].fillna("Unknown")

for col in numerical_cols:
    X[col] = X[col].fillna(X[col].median())

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTrain size: {X_train.shape}, Test size: {X_test.shape}")

# Define preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols),
        ("num", StandardScaler(), numerical_cols)
    ],
    remainder="passthrough"
)

# Fit preprocessor
X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

print(f"Processed train shape: {X_train_processed.shape}")

# Get feature names after preprocessing
cat_feature_names = preprocessor.named_transformers_["cat"].get_feature_names_out(categorical_cols)
feature_names = list(cat_feature_names) + numerical_cols

# Train XGBoost (preferred model per report)
print("\n=== Training XGBoost (Primary Model) ===")
xgb_model = xgb.XGBRegressor(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbosity=0
)
xgb_model.fit(X_train_processed, y_train)
xgb_pred = xgb_model.predict(X_test_processed)
xgb_mae = mean_absolute_error(y_test, xgb_pred)
xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
xgb_r2 = r2_score(y_test, xgb_pred)
print(f"MAE: ${xgb_mae:,.0f}")
print(f"RMSE: ${xgb_rmse:,.0f}")
print(f"R²: {xgb_r2:.4f}")

# Cross-validation
print("\n=== Cross-Validation (5-fold) ===")
cv_scores = cross_val_score(
    xgb_model, X_train_processed, y_train,
    cv=5, scoring="neg_mean_absolute_error", n_jobs=-1
)
cv_mae = -cv_scores.mean()
cv_std = cv_scores.std()
print(f"CV MAE: ${cv_mae:,.0f} (+/- ${cv_std*2:,.0f})")

# Also train LightGBM for comparison
print("\n=== Training LightGBM (Alternative) ===")
import lightgbm as lgb
lgb_model = lgb.LGBMRegressor(
    n_estimators=300,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbosity=-1
)
lgb_model.fit(X_train_processed, y_train)
lgb_pred = lgb_model.predict(X_test_processed)
lgb_mae = mean_absolute_error(y_test, lgb_pred)
lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
lgb_r2 = r2_score(y_test, lgb_pred)
print(f"MAE: ${lgb_mae:,.0f}")
print(f"RMSE: ${lgb_rmse:,.0f}")
print(f"R²: {lgb_r2:.4f}")

# Feature importance
importances = xgb_model.feature_importances_
feature_importance = list(zip(feature_names, importances))
feature_importance.sort(key=lambda x: -x[1])
print("\nTop 30 Feature Importances (XGBoost):")
for name, imp in feature_importance[:30]:
    print(f"  {name}: {imp:.4f}")

# Save XGBoost as primary model
joblib.dump(xgb_model, SALARY_MODEL_FILE)
joblib.dump(preprocessor, SALARY_PREPROCESSOR_FILE)

# Save metadata
metadata = {
    "model_type": "XGBoost",
    "model_params": {
        "n_estimators": 300,
        "max_depth": 8,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42
    },
    "feature_columns": feature_cols,
    "categorical_columns": categorical_cols,
    "numerical_columns": numerical_cols,
    "top_skills": top_skill_names,
    "feature_names_after_preprocessing": feature_names,
    "metrics": {
        "test_MAE": float(xgb_mae),
        "test_RMSE": float(xgb_rmse),
        "test_R2": float(xgb_r2),
        "cv_MAE": float(cv_mae),
        "cv_MAE_std": float(cv_std)
    },
    "alternative_model_metrics": {
        "LightGBM": {"MAE": float(lgb_mae), "RMSE": float(lgb_rmse), "R2": float(lgb_r2)}
    },
    "target": "salary_midpoint",
    "train_size": int(X_train.shape[0]),
    "test_size": int(X_test.shape[0]),
    "note": "Target is salary_midpoint. Features exclude all salary fields (annual_salary_usd, salary_min_usd, salary_max_usd, salary_midpoint, salary_range, salary_tier) to prevent leakage. NOTE: In this dataset, salary_midpoint has only 19 unique values and is nearly deterministic per job_title, resulting in very low prediction error. This is a dataset limitation - real-world data would have more variance."
}

with open(SALARY_METADATA_FILE, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"\nModel saved to: {SALARY_MODEL_FILE}")
print(f"Preprocessor saved to: {SALARY_PREPROCESSOR_FILE}")
print(f"Metadata saved to: {SALARY_METADATA_FILE}")

# Test prediction on a few samples
print("\n=== Sample Predictions ===")
for i in range(min(5, len(X_test))):
    sample = X_test.iloc[i:i+1]
    sample_processed = preprocessor.transform(sample)
    pred = xgb_model.predict(sample_processed)[0]
    actual = y_test[i]
    print(f"Sample {i}: Predicted=${pred:,.0f}, Actual=${actual:,.0f}, Diff=${abs(pred-actual):,.0f}")
    print(f"  Features: {dict(sample.iloc[0][['job_title', 'job_category', 'experience_level', 'country', 'company_size', 'industry']])}")

# Show salary by job_title for reference
print("\n=== Salary by Job Title (from training data) ===")
salary_by_title = df.groupby("job_title")["salary_midpoint"].first().sort_values()
for title, sal in salary_by_title.items():
    print(f"  {title}: ${sal:,.0f}")