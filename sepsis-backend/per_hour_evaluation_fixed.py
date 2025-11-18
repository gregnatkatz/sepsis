"""
Per-Hour Risk Scoring Evaluation (Fixed)
- Proper feature alignment with model's expected 73 features
- Persistence logic: require N consecutive hours above threshold
- Windowing: 6-12h before onset for sepsis, matched window for non-sepsis
- Threshold sweep to find PPV 80% threshold
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
from pathlib import Path
import pickle
from typing import Dict, List, Tuple

def calculate_sirs_criteria(row: pd.Series) -> Dict[str, float]:
    """Calculate SIRS criteria from vitals"""
    sirs_temp = 1 if pd.notna(row.get('Temp')) and (row['Temp'] < 36 or row['Temp'] > 38) else 0
    sirs_hr = 1 if pd.notna(row.get('HR')) and row['HR'] > 90 else 0
    sirs_resp = 1 if pd.notna(row.get('Resp')) and row['Resp'] > 20 else 0
    sirs_wbc = 1 if pd.notna(row.get('WBC')) and (row['WBC'] < 4 or row['WBC'] > 12) else 0
    sirs_count = sirs_temp + sirs_hr + sirs_resp + sirs_wbc
    
    return {
        'sirs_temp': sirs_temp,
        'sirs_hr': sirs_hr,
        'sirs_resp': sirs_resp,
        'sirs_wbc': sirs_wbc,
        'sirs_count': sirs_count
    }

def extract_features_for_hour(row: pd.Series, patient_df: pd.DataFrame, hour_idx: int, feature_names: List[str]) -> pd.DataFrame:
    """
    Extract features for ML model prediction at a specific hour
    Returns DataFrame with exact feature names expected by model
    """
    features = {}
    
    features['temp'] = row.get('Temp', 37.0)
    features['hr'] = row.get('HR', 80.0)
    features['resp'] = row.get('Resp', 16.0)
    features['wbc'] = row.get('WBC', 8.0)
    
    sirs = calculate_sirs_criteria(row)
    features.update(sirs)
    
    features['sbp'] = row.get('SBP', 120.0)
    features['dbp'] = row.get('DBP', 80.0)
    features['map'] = row.get('MAP', 93.0)
    features['o2sat'] = row.get('O2Sat', 98.0)
    
    features['lactate'] = row.get('Lactate', 1.0)
    features['creatinine'] = row.get('Creatinine', 1.0)
    features['glucose'] = row.get('Glucose', 100.0)
    features['hct'] = row.get('Hct', 40.0)
    features['platelets'] = row.get('Platelets', 200.0)
    
    features['age'] = row.get('Age', 65.0)
    features['gender'] = row.get('Gender', 0.0)
    features['iculos'] = row.get('ICULOS', 1.0)
    
    if hour_idx >= 6:
        past_6h = patient_df.iloc[hour_idx - 6]
        for col_kaggle, col_lower in [('HR', 'hr'), ('Temp', 'temp'), ('SBP', 'sbp'), ('DBP', 'dbp'), 
                                       ('MAP', 'map'), ('Resp', 'resp'), ('O2Sat', 'o2sat'), ('WBC', 'wbc'),
                                       ('Lactate', 'lactate'), ('Creatinine', 'creatinine'), ('Glucose', 'glucose'),
                                       ('Hct', 'hct'), ('Platelets', 'platelets')]:
            current_val = row.get(col_kaggle, 0)
            past_val = past_6h.get(col_kaggle, 0)
            if pd.notna(current_val) and pd.notna(past_val) and past_val != 0:
                features[f'{col_kaggle}_trend_6h'] = current_val - past_val
                features[f'{col_kaggle}_pct_change_6h'] = (current_val - past_val) / past_val * 100
            else:
                features[f'{col_kaggle}_trend_6h'] = 0
                features[f'{col_kaggle}_pct_change_6h'] = 0
    else:
        for col_kaggle in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC', 
                          'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
            features[f'{col_kaggle}_trend_6h'] = 0
            features[f'{col_kaggle}_pct_change_6h'] = 0
    
    if hour_idx >= 12:
        past_12h = patient_df.iloc[hour_idx - 12]
        for col_kaggle in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC',
                          'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
            current_val = row.get(col_kaggle, 0)
            past_val = past_12h.get(col_kaggle, 0)
            if pd.notna(current_val) and pd.notna(past_val) and past_val != 0:
                features[f'{col_kaggle}_trend_12h'] = current_val - past_val
                features[f'{col_kaggle}_pct_change_12h'] = (current_val - past_val) / past_val * 100
            else:
                features[f'{col_kaggle}_trend_12h'] = 0
                features[f'{col_kaggle}_pct_change_12h'] = 0
    else:
        for col_kaggle in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC',
                          'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
            features[f'{col_kaggle}_trend_12h'] = 0
            features[f'{col_kaggle}_pct_change_12h'] = 0
    
    feature_dict = {name: features.get(name, 0) for name in feature_names}
    return pd.DataFrame([feature_dict])

def detect_alert(predictions: List[float], threshold: float, persistence: int = 2) -> bool:
    """
    Detect alert with persistence requirement
    Returns True if there are >= persistence consecutive hours above threshold
    """
    if len(predictions) < persistence:
        return False
    
    consecutive = 0
    for pred in predictions:
        if pred >= threshold:
            consecutive += 1
            if consecutive >= persistence:
                return True
        else:
            consecutive = 0
    
    return False

def evaluate_per_hour_fixed(
    csv_path: str,
    model_path: str,
    threshold: float = 0.5,
    prediction_window: Tuple[int, int] = (6, 12),
    persistence: int = 2
) -> Dict:
    """
    Evaluate sepsis prediction with per-hour risk scoring (fixed version)
    
    Args:
        csv_path: Path to Kaggle Dataset.csv
        model_path: Path to trained ML model
        threshold: Prediction threshold (0-1)
        prediction_window: (min_hours, max_hours) before sepsis onset
        persistence: Number of consecutive hours required above threshold
    
    Returns:
        Dictionary with evaluation metrics
    """
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    print(f"Loading ML model from {model_path}...")
    with open(model_path, 'rb') as f:
        model_dict = pickle.load(f)
        ml_model = model_dict['model']
        feature_names = model_dict['feature_names']
    print(f"ML model loaded with {len(feature_names)} features")
    
    min_hours_before, max_hours_before = prediction_window
    
    results = []
    
    for patient_id, patient_df in df.groupby('Patient_ID'):
        patient_df = patient_df.sort_values('ICULOS').reset_index(drop=True)
        
        sepsis_hours = patient_df[patient_df['SepsisLabel'] == 1]
        has_sepsis = len(sepsis_hours) > 0
        sepsis_onset_hour = sepsis_hours.index[0] if has_sepsis else None
        
        all_features = []
        for hour_idx, row in patient_df.iterrows():
            features_df = extract_features_for_hour(row, patient_df, hour_idx, feature_names)
            all_features.append(features_df)
        
        if all_features:
            features_batch = pd.concat(all_features, ignore_index=True)
            predictions = ml_model.predict_proba(features_batch)[:, 1]
        else:
            predictions = []
        
        if has_sepsis:
            if sepsis_onset_hour and sepsis_onset_hour >= min_hours_before:
                window_start = max(0, sepsis_onset_hour - max_hours_before)
                window_end = sepsis_onset_hour - min_hours_before
                
                if window_end > window_start:
                    window_predictions = predictions[window_start:window_end]
                    predicted_positive = detect_alert(window_predictions, threshold, persistence)
                else:
                    predicted_positive = False
            else:
                predicted_positive = False
        else:
            if len(predictions) >= max_hours_before:
                window_predictions = predictions[-max_hours_before:]
                predicted_positive = detect_alert(window_predictions, threshold, persistence)
            else:
                predicted_positive = False
        
        results.append({
            'patient_id': patient_id,
            'has_sepsis': has_sepsis,
            'predicted_positive': predicted_positive,
            'max_prediction': max(predictions) if len(predictions) > 0 else 0,
            'sepsis_onset_hour': sepsis_onset_hour
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
        'prevalence': sum(y_true) / len(y_true),
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
    print("PER-HOUR EVALUATION WITH FIXED FEATURE ALIGNMENT")
    print("=" * 80)
    
    print("\n=== Testing with 1000 patients ===")
    df = pd.read_csv(csv_path)
    sample_patients = df['Patient_ID'].unique()[:1000]
    df_sample = df[df['Patient_ID'].isin(sample_patients)]
    df_sample.to_csv('/tmp/sample_dataset_1000.csv', index=False)
    
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
    
    print("\nThreshold sweep with persistence=2:")
    print(f"{'Threshold':<12} {'PPV':<8} {'Sens':<8} {'Spec':<8} {'F1':<8} {'TP':<6} {'FP':<6} {'TN':<6} {'FN':<6}")
    print("-" * 80)
    
    for threshold in thresholds:
        results = evaluate_per_hour_fixed(
            csv_path='/tmp/sample_dataset_1000.csv',
            model_path=model_path,
            threshold=threshold,
            prediction_window=(6, 12),
            persistence=2
        )
        
        print(f"{threshold:<12.2f} {results['metrics']['ppv']:<8.1%} {results['metrics']['sensitivity']:<8.1%} "
              f"{results['metrics']['specificity']:<8.1%} {results['metrics']['f1_score']:<8.3f} "
              f"{results['confusion_matrix']['tp']:<6} {results['confusion_matrix']['fp']:<6} "
              f"{results['confusion_matrix']['tn']:<6} {results['confusion_matrix']['fn']:<6}")
    
    print("\n" + "=" * 80)
    print("Sample evaluation complete. Ready to run on full dataset.")
