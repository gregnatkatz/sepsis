"""
Evaluate Time-Shifted Model with Per-Hour Risk Scoring
- Use time-shifted model (predicts sepsis 6-12h in advance)
- Per-hour evaluation with windowing and persistence
- Find threshold that achieves 80%+ PPV
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
from pathlib import Path
import pickle
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

def compute_features_bulk(df: pd.DataFrame, feature_names: List[str]) -> pd.DataFrame:
    """
    Compute all features in bulk using vectorized operations
    Returns DataFrame with exact feature names expected by model
    """
    print("Computing features in bulk...")
    
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
    
    print("Adding interaction features...")
    
    features['resp_score'] = 0
    features.loc[features['o2sat'] < 90, 'resp_score'] = 1
    features.loc[features['o2sat'] < 85, 'resp_score'] = 2
    
    features['cardio_score'] = 0
    features.loc[features['map'] < 70, 'cardio_score'] = 1
    features.loc[(features['map'] < 70) & (features['lactate'] > 2), 'cardio_score'] = 2
    features.loc[(features['map'] < 65) & (features['lactate'] > 4), 'cardio_score'] = 3
    
    features['renal_score'] = 0
    features.loc[features['creatinine'] > 1.2, 'renal_score'] = 1
    features.loc[features['creatinine'] > 2.0, 'renal_score'] = 2
    features.loc[features['creatinine'] > 3.5, 'renal_score'] = 3
    
    features['coag_score'] = 0
    features.loc[features['platelets'] < 150, 'coag_score'] = 1
    features.loc[features['platelets'] < 100, 'coag_score'] = 2
    features.loc[features['platelets'] < 50, 'coag_score'] = 3
    
    features['sofa_like_score'] = features['resp_score'] + features['cardio_score'] + features['renal_score'] + features['coag_score']
    
    features['qsofa_score'] = 0
    features.loc[features['resp'] >= 22, 'qsofa_score'] += 1
    features.loc[features['sbp'] <= 100, 'qsofa_score'] += 1
    
    features['sirs_hr_interaction'] = features['sirs_count'] * features['hr']
    features['sirs_temp_interaction'] = features['sirs_count'] * features['temp']
    features['sirs_map_interaction'] = features['sirs_count'] * features['map']
    
    features['lactate_hr_interaction'] = features['lactate'] * features['hr']
    features['lactate_map_interaction'] = features['lactate'] * features['map']
    features['lactate_temp_interaction'] = features['lactate'] * features['temp']
    
    features['shock_index'] = features['hr'] / features['sbp']
    features['shock_index'] = features['shock_index'].replace([np.inf, -np.inf], 0).fillna(0)
    
    features['pulse_pressure'] = features['sbp'] - features['dbp']
    
    features['lactate_clearance_6h'] = features.groupby(df['Patient_ID'])['lactate'].diff(6).fillna(0)
    
    trend_cols_6h = [col for col in features.columns if '_trend_6h' in col and '_pct_' not in col]
    features['trend_severity_6h'] = features[trend_cols_6h].abs().sum(axis=1)
    
    trend_cols_12h = [col for col in features.columns if '_trend_12h' in col and '_pct_' not in col]
    features['trend_severity_12h'] = features[trend_cols_12h].abs().sum(axis=1)
    
    features['hr_increasing'] = (features['HR_trend_6h'] > 5).astype(int)
    features['temp_increasing'] = (features['Temp_trend_6h'] > 0.5).astype(int)
    features['lactate_increasing'] = (features['Lactate_trend_6h'] > 0.5).astype(int)
    features['map_decreasing'] = (features['MAP_trend_6h'] < -5).astype(int)
    
    features['worsening_score'] = features['hr_increasing'] + features['temp_increasing'] + \
                                  features['lactate_increasing'] + features['map_decreasing']
    
    features = features[feature_names]
    
    features['Patient_ID'] = df['Patient_ID'].values
    features['ICULOS'] = df['ICULOS'].values
    features['SepsisLabel'] = df['SepsisLabel'].values
    
    print(f"Computed {len(features)} rows with {len(feature_names)} features")
    return features

def detect_alert_vectorized(predictions: np.ndarray, threshold: float, persistence: int = 2) -> bool:
    """
    Detect alert with persistence requirement (vectorized)
    Returns True if there are >= persistence consecutive hours above threshold
    """
    if len(predictions) < persistence:
        return False
    
    above_threshold = (predictions >= threshold).astype(int)
    
    if persistence == 1:
        return np.any(above_threshold)
    
    for i in range(len(above_threshold) - persistence + 1):
        if np.all(above_threshold[i:i+persistence]):
            return True
    
    return False

def evaluate_per_hour(features_df: pd.DataFrame, threshold: float, 
                     min_hours_before: int = 6, max_hours_before: int = 12,
                     persistence: int = 2) -> Dict:
    """
    Evaluate per-hour with windowing and persistence
    """
    results = []
    
    for patient_id, patient_df in features_df.groupby('Patient_ID'):
        patient_df = patient_df.sort_values('ICULOS').reset_index(drop=True)
        
        sepsis_hours = patient_df[patient_df['SepsisLabel'] == 1]
        has_sepsis = len(sepsis_hours) > 0
        sepsis_onset_hour = sepsis_hours.index[0] if has_sepsis else None
        
        preds = patient_df['prediction'].values
        
        if has_sepsis:
            if sepsis_onset_hour and sepsis_onset_hour >= min_hours_before:
                window_start = max(0, sepsis_onset_hour - max_hours_before)
                window_end = sepsis_onset_hour - min_hours_before
                
                if window_end > window_start:
                    window_preds = preds[window_start:window_end]
                    predicted_positive = detect_alert_vectorized(window_preds, threshold, persistence)
                else:
                    predicted_positive = False
            else:
                predicted_positive = False
        else:
            if len(preds) >= max_hours_before:
                window_preds = preds[-max_hours_before:]
                predicted_positive = detect_alert_vectorized(window_preds, threshold, persistence)
            else:
                predicted_positive = False
        
        results.append({
            'patient_id': patient_id,
            'has_sepsis': has_sepsis,
            'predicted_positive': predicted_positive
        })
    
    results_df = pd.DataFrame(results)
    
    tp = ((results_df['has_sepsis'] == True) & (results_df['predicted_positive'] == True)).sum()
    fp = ((results_df['has_sepsis'] == False) & (results_df['predicted_positive'] == True)).sum()
    tn = ((results_df['has_sepsis'] == False) & (results_df['predicted_positive'] == False)).sum()
    fn = ((results_df['has_sepsis'] == True) & (results_df['predicted_positive'] == False)).sum()
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
    
    return {
        'threshold': threshold,
        'ppv': ppv,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'f1': f1,
        'tp': tp,
        'fp': fp,
        'tn': tn,
        'fn': fn
    }

if __name__ == "__main__":
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    model_path = "ml_model_time_shifted.pkl"
    
    print("=" * 80)
    print("EVALUATING TIME-SHIFTED MODEL WITH PER-HOUR RISK SCORING")
    print("=" * 80)
    
    print(f"\nLoading time-shifted model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_dict = pickle.load(f)
    
    model = model_dict['model']
    feature_names = model_dict['feature_names']
    print(f"Model loaded with {len(feature_names)} features")
    
    print("\n=== Threshold Sweep on 5000 Patients ===\n")
    print(f"{'Threshold':<12} {'PPV':<10} {'Sens':<10} {'Spec':<10} {'F1':<10} {'TP':<8} {'FP':<8} {'TN':<8} {'FN':<8}")
    print("-" * 90)
    
    thresholds = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.15, 0.20]
    best_threshold = 0.05
    best_ppv_diff = float('inf')
    
    for threshold in thresholds:
        print(f"\nProcessing threshold {threshold}...")
        df = pd.read_csv(csv_path)
        sample_patients = df['Patient_ID'].unique()[:5000]
        df = df[df['Patient_ID'].isin(sample_patients)]
        
        features_df = compute_features_bulk(df, feature_names)
        
        X = features_df[feature_names].fillna(0)
        predictions = model.predict_proba(X)[:, 1]
        features_df['prediction'] = predictions
        
        metrics = evaluate_per_hour(features_df, threshold)
        
        print(f"{threshold:<12.2f} {metrics['ppv']:<10.1%} {metrics['sensitivity']:<10.1%} {metrics['specificity']:<10.1%} {metrics['f1']:<10.3f} {metrics['tp']:<8} {metrics['fp']:<8} {metrics['tn']:<8} {metrics['fn']:<8}")
        
        ppv_diff = abs(metrics['ppv'] - 0.80)
        if ppv_diff < best_ppv_diff:
            best_ppv_diff = ppv_diff
            best_threshold = threshold
    
    print(f"\n{'=' * 80}")
    print(f"Best threshold for PPV ~80%: {best_threshold}")
    print(f"{'=' * 80}")
    
    print(f"\n=== Running Full Dataset with Threshold {best_threshold} ===")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    features_df = compute_features_bulk(df, feature_names)
    
    print("Batch predicting all hours...")
    X = features_df[feature_names].fillna(0)
    predictions = model.predict_proba(X)[:, 1]
    features_df['prediction'] = predictions
    
    print("Evaluating per patient...")
    metrics = evaluate_per_hour(features_df, best_threshold)
    
    n_sepsis = (features_df.groupby('Patient_ID')['SepsisLabel'].max() == 1).sum()
    n_total = features_df['Patient_ID'].nunique()
    n_non_sepsis = n_total - n_sepsis
    
    print(f"\nFinal Results (All {n_total:,} Patients):")
    print(f"Patients: {n_total} ({n_sepsis} sepsis, {n_non_sepsis} non-sepsis)")
    print(f"PPV: {metrics['ppv']:.1%}")
    print(f"Sensitivity: {metrics['sensitivity']:.1%}")
    print(f"Specificity: {metrics['specificity']:.1%}")
    print(f"F1: {metrics['f1']:.3f}")
    print(f"Confusion Matrix: TP={metrics['tp']}, FP={metrics['fp']}, TN={metrics['tn']}, FN={metrics['fn']}")
    
    print("\n" + "=" * 80)
    print("Evaluation complete!")
    print("=" * 80)
