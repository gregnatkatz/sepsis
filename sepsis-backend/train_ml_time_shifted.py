"""
Train ML Model with Time-Shifted Labels and Interaction Features
- Labels: "will become septic in 6-12h" (shift labels back in time)
- New features: interaction terms, clinical scores (SOFA-like, qSOFA)
- Goal: Reach 80%+ PPV with proper time-aligned prediction
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
import xgboost as xgb
import lightgbm as lgb
import pickle
import warnings
warnings.filterwarnings('ignore')

def create_time_shifted_labels(df: pd.DataFrame, min_hours: int = 6, max_hours: int = 12) -> pd.DataFrame:
    """
    Create time-shifted labels: "will become septic in 6-12h"
    For each hour, label = 1 if sepsis occurs within next 6-12h
    """
    print(f"Creating time-shifted labels ({min_hours}-{max_hours}h prediction window)...")
    
    df = df.sort_values(['Patient_ID', 'ICULOS']).reset_index(drop=True)
    df['time_shifted_label'] = 0
    
    for patient_id, patient_df in df.groupby('Patient_ID'):
        sepsis_hours = patient_df[patient_df['SepsisLabel'] == 1]
        if len(sepsis_hours) > 0:
            onset_hour = sepsis_hours['ICULOS'].iloc[0]
            
            window_start = max(1, onset_hour - max_hours)
            window_end = onset_hour - min_hours
            
            if window_end >= window_start:
                mask = (df['Patient_ID'] == patient_id) & \
                       (df['ICULOS'] >= window_start) & \
                       (df['ICULOS'] <= window_end)
                df.loc[mask, 'time_shifted_label'] = 1
    
    n_positive = df['time_shifted_label'].sum()
    n_total = len(df)
    print(f"Time-shifted labels: {n_positive:,} positive ({n_positive/n_total*100:.2f}%) out of {n_total:,} hours")
    
    return df

def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add interaction features and clinical scores
    """
    print("Adding interaction features and clinical scores...")
    
    df['resp_score'] = 0
    df.loc[df['O2Sat'] < 90, 'resp_score'] = 1
    df.loc[df['O2Sat'] < 85, 'resp_score'] = 2
    
    df['cardio_score'] = 0
    df.loc[df['MAP'] < 70, 'cardio_score'] = 1
    df.loc[(df['MAP'] < 70) & (df['Lactate'] > 2), 'cardio_score'] = 2
    df.loc[(df['MAP'] < 65) & (df['Lactate'] > 4), 'cardio_score'] = 3
    
    df['renal_score'] = 0
    df.loc[df['Creatinine'] > 1.2, 'renal_score'] = 1
    df.loc[df['Creatinine'] > 2.0, 'renal_score'] = 2
    df.loc[df['Creatinine'] > 3.5, 'renal_score'] = 3
    
    df['coag_score'] = 0
    df.loc[df['Platelets'] < 150, 'coag_score'] = 1
    df.loc[df['Platelets'] < 100, 'coag_score'] = 2
    df.loc[df['Platelets'] < 50, 'coag_score'] = 3
    
    df['sofa_like_score'] = df['resp_score'] + df['cardio_score'] + df['renal_score'] + df['coag_score']
    
    df['qsofa_score'] = 0
    df.loc[df['Resp'] >= 22, 'qsofa_score'] += 1
    df.loc[df['SBP'] <= 100, 'qsofa_score'] += 1
    
    df['sirs_hr_interaction'] = df['sirs_count'] * df['HR']
    df['sirs_temp_interaction'] = df['sirs_count'] * df['Temp']
    df['sirs_map_interaction'] = df['sirs_count'] * df['MAP']
    
    df['lactate_hr_interaction'] = df['Lactate'] * df['HR']
    df['lactate_map_interaction'] = df['Lactate'] * df['MAP']
    df['lactate_temp_interaction'] = df['Lactate'] * df['Temp']
    
    df['shock_index'] = df['HR'] / df['SBP']
    df['shock_index'] = df['shock_index'].replace([np.inf, -np.inf], 0).fillna(0)
    
    df['pulse_pressure'] = df['SBP'] - df['DBP']
    
    df['lactate_clearance_6h'] = df.groupby('Patient_ID')['Lactate'].diff(6)
    df['lactate_clearance_6h'] = df['lactate_clearance_6h'].fillna(0)
    
    trend_cols_6h = [col for col in df.columns if '_trend_6h' in col and '_pct_' not in col]
    df['trend_severity_6h'] = df[trend_cols_6h].abs().sum(axis=1)
    
    trend_cols_12h = [col for col in df.columns if '_trend_12h' in col and '_pct_' not in col]
    df['trend_severity_12h'] = df[trend_cols_12h].abs().sum(axis=1)
    
    df['hr_increasing'] = (df['HR_trend_6h'] > 5).astype(int)
    df['temp_increasing'] = (df['Temp_trend_6h'] > 0.5).astype(int)
    df['lactate_increasing'] = (df['Lactate_trend_6h'] > 0.5).astype(int)
    df['map_decreasing'] = (df['MAP_trend_6h'] < -5).astype(int)
    
    df['worsening_score'] = df['hr_increasing'] + df['temp_increasing'] + \
                            df['lactate_increasing'] + df['map_decreasing']
    
    print(f"Added {len([c for c in df.columns if c not in ['Patient_ID', 'ICULOS', 'SepsisLabel', 'time_shifted_label']])} total features")
    
    return df

def extract_features_with_interactions(csv_path: str) -> pd.DataFrame:
    """
    Extract features from Kaggle dataset with time-shifted labels and interactions
    """
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    df = df.sort_values(['Patient_ID', 'ICULOS']).reset_index(drop=True)
    
    features = pd.DataFrame()
    features['temp'] = df['Temp'].fillna(37.0)
    features['hr'] = df['HR'].fillna(80.0)
    features['resp'] = df['Resp'].fillna(16.0)
    features['wbc'] = df['WBC'].fillna(8.0)
    
    features['sirs_temp'] = ((df['Temp'] < 36) | (df['Temp'] > 38)).astype(int)
    features['sirs_hr'] = (df['HR'] > 90).astype(int)
    features['sirs_resp'] = (df['Resp'] > 20).astype(int)
    features['sirs_wbc'] = ((df['WBC'] < 4) | (df['WBC'] > 12)).astype(int)
    features['sirs_count'] = features['sirs_temp'] + features['sirs_hr'] + features['sirs_resp'] + features['sirs_wbc']
    
    features['sbp'] = df['SBP'].fillna(120.0)
    features['dbp'] = df['DBP'].fillna(80.0)
    features['map'] = df['MAP'].fillna(93.0)
    features['o2sat'] = df['O2Sat'].fillna(98.0)
    
    features['lactate'] = df['Lactate'].fillna(1.0)
    features['creatinine'] = df['Creatinine'].fillna(1.0)
    features['glucose'] = df['Glucose'].fillna(100.0)
    features['hct'] = df['Hct'].fillna(40.0)
    features['platelets'] = df['Platelets'].fillna(200.0)
    
    features['age'] = df['Age'].fillna(65.0)
    features['gender'] = df['Gender'].fillna(0.0)
    features['iculos'] = df['ICULOS'].fillna(1.0)
    
    print("Computing 6h trend features...")
    for col_kaggle in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC', 
                      'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
        past_6h = df.groupby('Patient_ID')[col_kaggle].shift(6)
        current = df[col_kaggle]
        
        features[f'{col_kaggle}_trend_6h'] = (current - past_6h).fillna(0)
        pct_change = ((current - past_6h) / past_6h * 100).fillna(0)
        pct_change = pct_change.replace([np.inf, -np.inf], 0)
        features[f'{col_kaggle}_pct_change_6h'] = pct_change
    
    print("Computing 12h trend features...")
    for col_kaggle in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC',
                      'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
        past_12h = df.groupby('Patient_ID')[col_kaggle].shift(12)
        current = df[col_kaggle]
        
        features[f'{col_kaggle}_trend_12h'] = (current - past_12h).fillna(0)
        pct_change = ((current - past_12h) / past_12h * 100).fillna(0)
        pct_change = pct_change.replace([np.inf, -np.inf], 0)
        features[f'{col_kaggle}_pct_change_12h'] = pct_change
    
    features['Patient_ID'] = df['Patient_ID'].values
    features['ICULOS'] = df['ICULOS'].values
    features['SepsisLabel'] = df['SepsisLabel'].values
    
    for col in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC', 
                'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
        features[col] = df[col].fillna(0)
    
    features = add_interaction_features(features)
    
    features = create_time_shifted_labels(features, min_hours=6, max_hours=12)
    
    return features

def train_and_evaluate(features_df: pd.DataFrame):
    """
    Train and evaluate ML models with time-shifted labels
    """
    exclude_cols = ['Patient_ID', 'ICULOS', 'SepsisLabel', 'time_shifted_label',
                   'HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC',
                   'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']
    
    feature_cols = [col for col in features_df.columns if col not in exclude_cols]
    
    X = features_df[feature_cols].fillna(0)
    y = features_df['time_shifted_label']
    
    print(f"\nFeatures: {len(feature_cols)}")
    print(f"Positive labels: {y.sum():,} ({y.mean()*100:.2f}%)")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Train: {len(X_train):,} samples ({y_train.sum():,} positive)")
    print(f"Test: {len(X_test):,} samples ({y_test.sum():,} positive)")
    
    print("\n=== Training LightGBM with Time-Shifted Labels ===")
    
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"Class imbalance ratio: {scale_pos_weight:.1f}")
    
    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        subsample=0.8,
        colsample_bytree=0.8,
        verbose=-1
    )
    
    model.fit(X_train, y_train)
    
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    auroc = roc_auc_score(y_test, y_pred_proba)
    auprc = average_precision_score(y_test, y_pred_proba)
    
    print(f"\nTest AUROC: {auroc:.3f}")
    print(f"Test AUPRC: {auprc:.3f}")
    
    print("\nTop 15 Most Important Features:")
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(15).iterrows():
        print(f"  {row['feature']:<30} {row['importance']:.0f}")
    
    print("\nPPV at different thresholds:")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sensitivity':<12} {'Specificity':<12} {'F1':<10}")
    print("-" * 60)
    
    thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
    
    for threshold in thresholds:
        y_pred = (y_pred_proba >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
        
        print(f"{threshold:<12.2f} {ppv:<10.1%} {sensitivity:<12.1%} {specificity:<12.1%} {f1:<10.3f}")
    
    model_dict = {
        'model': model,
        'feature_names': feature_cols,
        'auroc': auroc,
        'auprc': auprc
    }
    
    model_path = 'ml_model_time_shifted.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model_dict, f)
    print(f"\nModel saved to {model_path}")
    
    return model_dict

if __name__ == "__main__":
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    
    print("=" * 80)
    print("TRAINING ML MODEL WITH TIME-SHIFTED LABELS AND INTERACTION FEATURES")
    print("=" * 80)
    
    features_df = extract_features_with_interactions(csv_path)
    
    print("\nSaving features to CSV...")
    features_df.to_csv('kaggle_features_time_shifted.csv', index=False)
    print("Features saved to kaggle_features_time_shifted.csv")
    
    model_dict = train_and_evaluate(features_df)
    
    print("\n" + "=" * 80)
    print("Training complete!")
    print("=" * 80)
