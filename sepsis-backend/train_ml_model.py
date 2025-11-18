"""
Train ML model (XGBoost/LightGBM) with trend features for improved PPV
"""

import requests
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
import xgboost as xgb
import lightgbm as lgb
import pickle
from pathlib import Path

API_URL = "http://127.0.0.1:8000"

def fetch_kaggle_patients():
    """Fetch all Kaggle patients from API"""
    print("Fetching Kaggle patients from API...")
    response = requests.get(f"{API_URL}/api/patients?limit=50000")
    patients = response.json().get('patients', [])
    
    kaggle_patients = [p for p in patients if p.get('id', '').startswith('kaggle-')]
    print(f"Loaded {len(kaggle_patients)} Kaggle patients")
    
    return kaggle_patients

def extract_features(patients):
    """Extract features including trend features from patient data"""
    features_list = []
    labels = []
    
    print("Extracting features and labels...")
    for p in patients:
        cohort_tags = p.get('cohort_tags', [])
        if isinstance(cohort_tags, str):
            cohort_tags = json.loads(cohort_tags)
        
        sepsis_label = 0
        for tag in cohort_tags:
            if tag.startswith('sepsis_'):
                sepsis_label = int(tag.split('_')[1])
                break
        
        # Current risk score (baseline feature)
        risk_score = p.get('risk_score', 0)
        
        # For now, use risk_score as the main feature
        # In a full implementation, we would extract:
        # - SIRS components (temp, HR, RR, WBC)
        # - Vitals (SBP, DBP, MAP, O2Sat)
        # - Labs (Lactate, Creatinine, Glucose, etc.)
        # - Trend features (6-12h changes in vitals/labs)
        
        features_list.append({
            'risk_score': risk_score,
        })
        labels.append(sepsis_label)
    
    return pd.DataFrame(features_list), np.array(labels)

def train_xgboost_model(X_train, y_train, X_test, y_test):
    """Train XGBoost model"""
    print("\n=== Training XGBoost Model ===")
    
    # Handle class imbalance
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"Class imbalance ratio: {scale_pos_weight:.1f}")
    
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='auc'
    )
    
    model.fit(X_train, y_train, 
              eval_set=[(X_test, y_test)],
              verbose=False)
    
    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    auroc = roc_auc_score(y_test, y_pred_proba)
    auprc = average_precision_score(y_test, y_pred_proba)
    
    print(f"Test AUROC: {auroc:.3f}")
    print(f"Test AUPRC: {auprc:.3f}")
    
    # PPV at different thresholds
    print("\nPPV at different thresholds:")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sensitivity':<12} {'Specificity'}")
    print("-" * 50)
    
    for thresh in [0.1, 0.2, 0.3, 0.4, 0.5]:
        y_pred = (y_pred_proba >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        print(f"{thresh:<12.1f} {ppv*100:<10.1f}% {sensitivity*100:<12.1f}% {specificity*100:.1f}%")
    
    return model, auroc, auprc

def train_lightgbm_model(X_train, y_train, X_test, y_test):
    """Train LightGBM model"""
    print("\n=== Training LightGBM Model ===")
    
    # Handle class imbalance
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    
    model = lgb.LGBMClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbose=-1
    )
    
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              eval_metric='auc')
    
    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    auroc = roc_auc_score(y_test, y_pred_proba)
    auprc = average_precision_score(y_test, y_pred_proba)
    
    print(f"Test AUROC: {auroc:.3f}")
    print(f"Test AUPRC: {auprc:.3f}")
    
    # PPV at different thresholds
    print("\nPPV at different thresholds:")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sensitivity':<12} {'Specificity'}")
    print("-" * 50)
    
    for thresh in [0.1, 0.2, 0.3, 0.4, 0.5]:
        y_pred = (y_pred_proba >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        print(f"{thresh:<12.1f} {ppv*100:<10.1f}% {sensitivity*100:<12.1f}% {specificity*100:.1f}%")
    
    return model, auroc, auprc

def main():
    patients = fetch_kaggle_patients()
    
    X, y = extract_features(patients)
    
    print(f"\nDataset: {len(X)} patients")
    print(f"Sepsis: {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"Non-sepsis: {(1-y).sum()} ({(1-y.mean())*100:.1f}%)")
    print(f"Features: {list(X.columns)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTrain: {len(X_train)} patients")
    print(f"Test: {len(X_test)} patients")
    
    # Train XGBoost
    xgb_model, xgb_auroc, xgb_auprc = train_xgboost_model(X_train, y_train, X_test, y_test)
    
    # Train LightGBM
    lgb_model, lgb_auroc, lgb_auprc = train_lightgbm_model(X_train, y_train, X_test, y_test)
    
    # Compare models
    print("\n=== Model Comparison ===")
    print(f"{'Model':<15} {'AUROC':<10} {'AUPRC'}")
    print("-" * 35)
    print(f"{'XGBoost':<15} {xgb_auroc:<10.3f} {xgb_auprc:.3f}")
    print(f"{'LightGBM':<15} {lgb_auroc:<10.3f} {lgb_auprc:.3f}")
    
    # Save best model
    if xgb_auprc > lgb_auprc:
        print(f"\nSaving XGBoost model (AUPRC: {xgb_auprc:.3f})")
        with open('ml_model_xgb.pkl', 'wb') as f:
            pickle.dump(xgb_model, f)
    else:
        print(f"\nSaving LightGBM model (AUPRC: {lgb_auprc:.3f})")
        with open('ml_model_lgb.pkl', 'wb') as f:
            pickle.dump(lgb_model, f)
    
    print("\n=== Summary ===")
    print("Note: Current implementation uses only risk_score as feature")
    print("To achieve 80%+ PPV, we need to:")
    print("1. Extract raw SIRS components, vitals, and labs")
    print("2. Add trend features (6-12h changes)")
    print("3. Implement per-hour risk scoring (evaluation fix)")
    print("4. Optimize threshold based on clinical requirements")

if __name__ == "__main__":
    main()
