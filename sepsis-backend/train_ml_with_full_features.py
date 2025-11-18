"""
Train ML model with full feature set including trend features
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
import xgboost as xgb
import lightgbm as lgb
import pickle

def load_features():
    """Load extracted features"""
    print("Loading features...")
    df = pd.read_csv('kaggle_features_with_trends.csv')
    print(f"Loaded {len(df)} patients with {len(df.columns)} features")
    return df

def prepare_data(df):
    """Prepare features and labels"""
    # Separate features and labels
    feature_cols = [col for col in df.columns if col not in ['sepsis_label', 'patient_id']]
    X = df[feature_cols]
    y = df['sepsis_label']
    
    print(f"\nFeatures: {len(feature_cols)}")
    print(f"Sepsis cases: {y.sum()} ({y.mean()*100:.1f}%)")
    
    return X, y, feature_cols

def train_and_evaluate_xgboost(X_train, y_train, X_test, y_test, feature_names):
    """Train and evaluate XGBoost model"""
    print("\n=== Training XGBoost with Full Features ===")
    
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"Class imbalance ratio: {scale_pos_weight:.1f}")
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='auc',
        subsample=0.8,
        colsample_bytree=0.8
    )
    
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              verbose=False)
    
    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    auroc = roc_auc_score(y_test, y_pred_proba)
    auprc = average_precision_score(y_test, y_pred_proba)
    
    print(f"\nTest AUROC: {auroc:.3f}")
    print(f"Test AUPRC: {auprc:.3f}")
    
    # Feature importance
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print(f"\nTop 10 Most Important Features:")
    print(feature_importance.head(10).to_string(index=False))
    
    # PPV at different thresholds
    print(f"\nPPV at different thresholds:")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sensitivity':<12} {'Specificity':<12} {'F1'}")
    print("-" * 60)
    
    best_f1 = 0
    best_thresh = 0.5
    
    for thresh in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
        y_pred = (y_pred_proba >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
        
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh
        
        print(f"{thresh:<12.2f} {ppv*100:<10.1f}% {sensitivity*100:<12.1f}% {specificity*100:<12.1f}% {f1:.3f}")
    
    print(f"\nBest F1 threshold: {best_thresh:.2f} (F1: {best_f1:.3f})")
    
    return model, auroc, auprc, best_thresh

def train_and_evaluate_lightgbm(X_train, y_train, X_test, y_test, feature_names):
    """Train and evaluate LightGBM model"""
    print("\n=== Training LightGBM with Full Features ===")
    
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    
    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbose=-1,
        subsample=0.8,
        colsample_bytree=0.8
    )
    
    model.fit(X_train, y_train,
              eval_set=[(X_test, y_test)],
              eval_metric='auc')
    
    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    auroc = roc_auc_score(y_test, y_pred_proba)
    auprc = average_precision_score(y_test, y_pred_proba)
    
    print(f"\nTest AUROC: {auroc:.3f}")
    print(f"Test AUPRC: {auprc:.3f}")
    
    # Feature importance
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print(f"\nTop 10 Most Important Features:")
    print(feature_importance.head(10).to_string(index=False))
    
    # PPV at different thresholds
    print(f"\nPPV at different thresholds:")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sensitivity':<12} {'Specificity':<12} {'F1'}")
    print("-" * 60)
    
    best_f1 = 0
    best_thresh = 0.5
    
    for thresh in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]:
        y_pred = (y_pred_proba >= thresh).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
        
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh
        
        print(f"{thresh:<12.2f} {ppv*100:<10.1f}% {sensitivity*100:<12.1f}% {specificity*100:<12.1f}% {f1:.3f}")
    
    print(f"\nBest F1 threshold: {best_thresh:.2f} (F1: {best_f1:.3f})")
    
    return model, auroc, auprc, best_thresh

def main():
    df = load_features()
    X, y, feature_names = prepare_data(df)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTrain: {len(X_train)} patients ({y_train.sum()} sepsis)")
    print(f"Test: {len(X_test)} patients ({y_test.sum()} sepsis)")
    
    # Train XGBoost
    xgb_model, xgb_auroc, xgb_auprc, xgb_thresh = train_and_evaluate_xgboost(
        X_train, y_train, X_test, y_test, feature_names
    )
    
    # Train LightGBM
    lgb_model, lgb_auroc, lgb_auprc, lgb_thresh = train_and_evaluate_lightgbm(
        X_train, y_train, X_test, y_test, feature_names
    )
    
    # Compare models
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    print(f"{'Model':<15} {'AUROC':<10} {'AUPRC':<10} {'Best Threshold'}")
    print("-" * 60)
    print(f"{'XGBoost':<15} {xgb_auroc:<10.3f} {xgb_auprc:<10.3f} {xgb_thresh:.2f}")
    print(f"{'LightGBM':<15} {lgb_auroc:<10.3f} {lgb_auprc:<10.3f} {lgb_thresh:.2f}")
    
    # Save best model
    if xgb_auprc >= lgb_auprc:
        print(f"\nSaving XGBoost model (AUPRC: {xgb_auprc:.3f})")
        with open('ml_model_full_features.pkl', 'wb') as f:
            pickle.dump({
                'model': xgb_model,
                'feature_names': feature_names,
                'best_threshold': xgb_thresh,
                'auroc': xgb_auroc,
                'auprc': xgb_auprc
            }, f)
    else:
        print(f"\nSaving LightGBM model (AUPRC: {lgb_auprc:.3f})")
        with open('ml_model_full_features.pkl', 'wb') as f:
            pickle.dump({
                'model': lgb_model,
                'feature_names': feature_names,
                'best_threshold': lgb_thresh,
                'auroc': lgb_auroc,
                'auprc': lgb_auprc
            }, f)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Trained ML models with {len(feature_names)} features including:")
    print("- SIRS components (temp, HR, RR, WBC)")
    print("- Vitals (SBP, DBP, MAP, O2Sat)")
    print("- Labs (Lactate, Creatinine, Glucose, Hct, Platelets)")
    print("- Trend features (6h and 12h changes)")
    print("- Demographics (age, gender, ICU LOS)")
    print(f"\nBest model AUROC: {max(xgb_auroc, lgb_auroc):.3f}")
    print(f"Best model AUPRC: {max(xgb_auprc, lgb_auprc):.3f}")

if __name__ == "__main__":
    main()
