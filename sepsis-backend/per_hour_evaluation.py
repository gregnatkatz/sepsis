"""
Per-Hour Risk Scoring Evaluation
Evaluates sepsis prediction at each hour in the patient's time-series
Detects sepsis within 6-12 hours before onset
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
from pathlib import Path
import pickle
from typing import Dict, List, Tuple

def calculate_sirs_criteria(row: pd.Series) -> int:
    """Calculate SIRS criteria count from vitals"""
    sirs = 0
    
    if pd.notna(row['Temp']):
        if row['Temp'] < 36 or row['Temp'] > 38:
            sirs += 1
    
    if pd.notna(row['HR']):
        if row['HR'] > 90:
            sirs += 1
    
    if pd.notna(row['Resp']):
        if row['Resp'] > 20:
            sirs += 1
    
    if pd.notna(row['WBC']):
        if row['WBC'] < 4 or row['WBC'] > 12:
            sirs += 1
    
    return sirs

def calculate_risk_score(row: pd.Series, sirs: int) -> float:
    """Calculate risk score (0-100) from clinical parameters"""
    score = 0.0
    
    score += sirs * 10
    
    if pd.notna(row['HR']) and row['HR'] > 100:
        score += min((row['HR'] - 100) / 2, 15)
    
    if pd.notna(row['SBP']) and row['SBP'] < 100:
        score += min((100 - row['SBP']) / 2, 15)
    
    if pd.notna(row['Temp']) and row['Temp'] > 38:
        score += min((row['Temp'] - 38) * 5, 10)
    
    if pd.notna(row['Lactate']) and row['Lactate'] > 2:
        score += min((row['Lactate'] - 2) * 5, 15)
    
    if pd.notna(row['WBC']):
        if row['WBC'] > 12:
            score += min((row['WBC'] - 12) / 2, 10)
        elif row['WBC'] < 4:
            score += min((4 - row['WBC']) * 2, 10)
    
    return min(score, 100)

def extract_features_for_hour(row: pd.Series, patient_df: pd.DataFrame, hour_idx: int) -> np.ndarray:
    """
    Extract features for ML model prediction at a specific hour
    
    Args:
        row: Current hour's data
        patient_df: Full patient time-series
        hour_idx: Index of current hour in patient_df
    
    Returns:
        Feature vector for ML model
    """
    features = []
    
    sirs = calculate_sirs_criteria(row)
    features.extend([
        row.get('Temp', 37.0),
        row.get('HR', 80.0),
        row.get('Resp', 16.0),
        row.get('WBC', 8.0),
        1 if row.get('Temp', 37.0) < 36 or row.get('Temp', 37.0) > 38 else 0,
        1 if row.get('HR', 80.0) > 90 else 0,
        1 if row.get('Resp', 16.0) > 20 else 0,
        1 if row.get('WBC', 8.0) < 4 or row.get('WBC', 8.0) > 12 else 0,
        sirs
    ])
    
    features.extend([
        row.get('SBP', 120.0),
        row.get('DBP', 80.0),
        row.get('MAP', 93.0),
        row.get('O2Sat', 98.0)
    ])
    
    features.extend([
        row.get('Lactate', 1.0),
        row.get('Creatinine', 1.0),
        row.get('Glucose', 100.0),
        row.get('Hct', 40.0),
        row.get('Platelets', 200.0)
    ])
    
    features.extend([
        row.get('Age', 65.0),
        row.get('Gender', 0.0),
        row.get('ICULOS', 1.0)
    ])
    
    if hour_idx >= 6:
        past_6h = patient_df.iloc[hour_idx - 6]
        for col in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC', 'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
            current_val = row.get(col, 0)
            past_val = past_6h.get(col, 0)
            if pd.notna(current_val) and pd.notna(past_val) and past_val != 0:
                features.append(current_val - past_val)  # Absolute change
                features.append((current_val - past_val) / past_val * 100)  # Percent change
            else:
                features.append(0)
                features.append(0)
    else:
        features.extend([0] * 26)  # 13 features * 2 (absolute + percent)
    
    if hour_idx >= 12:
        past_12h = patient_df.iloc[hour_idx - 12]
        for col in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat', 'WBC', 'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
            current_val = row.get(col, 0)
            past_val = past_12h.get(col, 0)
            if pd.notna(current_val) and pd.notna(past_val) and past_val != 0:
                features.append(current_val - past_val)  # Absolute change
                features.append((current_val - past_val) / past_val * 100)  # Percent change
            else:
                features.append(0)
                features.append(0)
    else:
        features.extend([0] * 26)  # 13 features * 2 (absolute + percent)
    
    return np.array(features)

def evaluate_per_hour(
    csv_path: str,
    model_path: str = None,
    threshold: float = 0.5,
    prediction_window: Tuple[int, int] = (6, 12)
) -> Dict:
    """
    Evaluate sepsis prediction with per-hour risk scoring
    
    Args:
        csv_path: Path to Kaggle Dataset.csv
        model_path: Path to trained ML model (if None, use rule-based scoring)
        threshold: Prediction threshold (0-1 for ML, 0-100 for rule-based)
        prediction_window: (min_hours, max_hours) before sepsis onset to consider as positive
    
    Returns:
        Dictionary with evaluation metrics
    """
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    ml_model = None
    if model_path and Path(model_path).exists():
        print(f"Loading ML model from {model_path}...")
        with open(model_path, 'rb') as f:
            model_dict = pickle.load(f)
            if isinstance(model_dict, dict) and 'model' in model_dict:
                ml_model = model_dict['model']
            else:
                ml_model = model_dict
        print("ML model loaded successfully")
    
    min_hours_before, max_hours_before = prediction_window
    
    results = []
    
    for patient_id, patient_df in df.groupby('Patient_ID'):
        patient_df = patient_df.sort_values('ICULOS').reset_index(drop=True)
        
        sepsis_hours = patient_df[patient_df['SepsisLabel'] == 1]
        has_sepsis = len(sepsis_hours) > 0
        sepsis_onset_hour = sepsis_hours.index[0] if has_sepsis else None
        
        predictions = []
        for hour_idx, row in patient_df.iterrows():
            if ml_model:
                features = extract_features_for_hour(row, patient_df, hour_idx)
                pred_proba = ml_model.predict_proba([features])[0][1]
                predictions.append(pred_proba)
            else:
                sirs = calculate_sirs_criteria(row)
                risk_score = calculate_risk_score(row, sirs)
                predictions.append(risk_score / 100.0)  # Normalize to 0-1
        
        if has_sepsis:
            window_start = max(0, sepsis_onset_hour - max_hours_before)
            window_end = max(0, sepsis_onset_hour - min_hours_before)
            
            if window_end > window_start:
                window_predictions = predictions[window_start:window_end]
                predicted_positive = any(p >= threshold for p in window_predictions)
            else:
                window_predictions = predictions[:sepsis_onset_hour] if sepsis_onset_hour > 0 else []
                predicted_positive = any(p >= threshold for p in window_predictions) if window_predictions else False
        else:
            predicted_positive = any(p >= threshold for p in predictions)
        
        results.append({
            'patient_id': patient_id,
            'has_sepsis': has_sepsis,
            'predicted_positive': predicted_positive,
            'max_prediction': max(predictions) if predictions else 0,
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
    print("PER-HOUR EVALUATION WITH ML MODEL")
    print("=" * 80)
    
    thresholds = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]
    
    print("\nEvaluating at multiple thresholds...")
    for threshold in thresholds:
        print(f"\n--- Threshold: {threshold} ---")
        results = evaluate_per_hour(
            csv_path=csv_path,
            model_path=model_path,
            threshold=threshold,
            prediction_window=(6, 12)
        )
        
        print(f"Patients: {results['n_patients']} ({results['n_sepsis']} sepsis, {results['n_non_sepsis']} non-sepsis)")
        print(f"AUROC: {results['metrics']['auroc']:.3f}")
        print(f"AUPRC: {results['metrics']['auprc']:.3f}")
        print(f"PPV: {results['metrics']['ppv']:.1%}")
        print(f"Sensitivity: {results['metrics']['sensitivity']:.1%}")
        print(f"Specificity: {results['metrics']['specificity']:.1%}")
        print(f"F1: {results['metrics']['f1_score']:.3f}")
        print(f"Confusion Matrix: TP={results['confusion_matrix']['tp']}, FP={results['confusion_matrix']['fp']}, TN={results['confusion_matrix']['tn']}, FN={results['confusion_matrix']['fn']}")
