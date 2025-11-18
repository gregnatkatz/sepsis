"""
Fast Vectorized Per-Hour Risk Scoring Evaluation
- Bulk feature computation with groupby/shift
- Batch prediction for all hours
- Windowing: 6-12h before onset for sepsis, last 12h for non-sepsis
- Persistence: require N consecutive hours above threshold
- Threshold sweep to find PPV 80%
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

def evaluate_per_hour_fast(
    csv_path: str,
    model_path: str,
    threshold: float = 0.5,
    prediction_window: Tuple[int, int] = (6, 12),
    persistence: int = 2,
    max_patients: int = None
) -> Dict:
    """
    Fast vectorized per-hour evaluation
    
    Args:
        csv_path: Path to Kaggle Dataset.csv
        model_path: Path to trained ML model
        threshold: Prediction threshold (0-1)
        prediction_window: (min_hours, max_hours) before sepsis onset
        persistence: Number of consecutive hours required above threshold
        max_patients: Maximum number of patients to evaluate (None = all)
    
    Returns:
        Dictionary with evaluation metrics
    """
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    if max_patients:
        patient_ids = df['Patient_ID'].unique()[:max_patients]
        df = df[df['Patient_ID'].isin(patient_ids)]
        print(f"Sampled {max_patients} patients")
    
    print(f"Loading ML model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_dict = pickle.load(f)
        ml_model = model_dict['model']
        feature_names = model_dict['feature_names']
    print(f"ML model loaded with {len(feature_names)} features")
    
    features_df = compute_features_bulk(df, feature_names)
    
    print("Batch predicting all hours...")
    X = features_df[feature_names]
    predictions = ml_model.predict_proba(X)[:, 1]
    features_df['prediction'] = predictions
    
    min_hours_before, max_hours_before = prediction_window
    
    print("Evaluating per patient...")
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
            'predicted_positive': predicted_positive,
            'max_prediction': np.max(preds) if len(preds) > 0 else 0
        })
    
    y_true = [r['has_sepsis'] for r in results]
    y_pred = [r['predicted_positive'] for r in results]
    y_pred_proba = [r['max_prediction'] for r in results]
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
    
    try:
        auroc = roc_auc_score(y_true, y_pred_proba)
        auprc = average_precision_score(y_true, y_pred_proba)
    except:
        auroc = 0.0
        auprc = 0.0
    
    return {
        'n_patients': len(results),
        'n_sepsis': sum(y_true),
        'n_non_sepsis': len(y_true) - sum(y_true),
        'prevalence': sum(y_true) / len(y_true) if len(y_true) > 0 else 0,
        'threshold': threshold,
        'persistence': persistence,
        'prediction_window': f'{min_hours_before}-{max_hours_before}h before onset',
        'metrics': {
            'auroc': float(auroc),
            'auprc': float(auprc),
            'sensitivity': float(sensitivity),
            'specificity': float(specificity),
            'ppv': float(ppv),
            'npv': float(npv),
            'accuracy': float(accuracy),
            'f1_score': float(f1)
        },
        'confusion_matrix': {
            'tp': int(tp),
            'fp': int(fp),
            'tn': int(tn),
            'fn': int(fn)
        }
    }

if __name__ == "__main__":
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    model_path = "/home/ubuntu/sepsis/sepsis-backend/ml_model_full_features.pkl"
    
    print("=" * 80)
    print("FAST VECTORIZED PER-HOUR EVALUATION")
    print("=" * 80)
    
    print("\n=== Threshold Sweep on 5000 Patients ===")
    
    thresholds = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    
    print(f"\n{'Threshold':<12} {'PPV':<10} {'Sens':<10} {'Spec':<10} {'F1':<10} {'TP':<8} {'FP':<8} {'TN':<8} {'FN':<8}")
    print("-" * 90)
    
    best_threshold = None
    best_ppv_diff = float('inf')
    
    for threshold in thresholds:
        results = evaluate_per_hour_fast(
            csv_path=csv_path,
            model_path=model_path,
            threshold=threshold,
            prediction_window=(6, 12),
            persistence=2,
            max_patients=5000
        )
        
        ppv = results['metrics']['ppv']
        sens = results['metrics']['sensitivity']
        spec = results['metrics']['specificity']
        f1 = results['metrics']['f1_score']
        tp = results['confusion_matrix']['tp']
        fp = results['confusion_matrix']['fp']
        tn = results['confusion_matrix']['tn']
        fn = results['confusion_matrix']['fn']
        
        print(f"{threshold:<12.2f} {ppv:<10.1%} {sens:<10.1%} {spec:<10.1%} {f1:<10.3f} {tp:<8} {fp:<8} {tn:<8} {fn:<8}")
        
        ppv_diff = abs(ppv - 0.80)
        if ppv_diff < best_ppv_diff:
            best_ppv_diff = ppv_diff
            best_threshold = threshold
    
    print("\n" + "=" * 80)
    print(f"Best threshold for PPV ~80%: {best_threshold:.2f}")
    print("=" * 80)
    
    print(f"\n=== Running Full Dataset with Threshold {best_threshold:.2f} ===")
    final_results = evaluate_per_hour_fast(
        csv_path=csv_path,
        model_path=model_path,
        threshold=best_threshold,
        prediction_window=(6, 12),
        persistence=2,
        max_patients=None
    )
    
    print(f"\nFinal Results (All 40,336 Patients):")
    print(f"Patients: {final_results['n_patients']} ({final_results['n_sepsis']} sepsis, {final_results['n_non_sepsis']} non-sepsis)")
    print(f"AUROC: {final_results['metrics']['auroc']:.3f}")
    print(f"AUPRC: {final_results['metrics']['auprc']:.3f}")
    print(f"PPV: {final_results['metrics']['ppv']:.1%}")
    print(f"Sensitivity: {final_results['metrics']['sensitivity']:.1%}")
    print(f"Specificity: {final_results['metrics']['specificity']:.1%}")
    print(f"F1: {final_results['metrics']['f1_score']:.3f}")
    print(f"Confusion Matrix: TP={final_results['confusion_matrix']['tp']}, FP={final_results['confusion_matrix']['fp']}, TN={final_results['confusion_matrix']['tn']}, FN={final_results['confusion_matrix']['fn']}")
