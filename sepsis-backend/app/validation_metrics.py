"""
External Validation Metrics for Kaggle Dataset
Calculates AUROC, AUPRC, F1, Calibration, and other metrics
"""

from typing import Dict, List, Any, Optional
from sklearn.metrics import (
    roc_auc_score, 
    average_precision_score, 
    f1_score, 
    confusion_matrix,
    roc_curve,
    precision_recall_curve
)
import numpy as np
import os
from pathlib import Path

def calculate_validation_metrics(patients: List[Dict[str, Any]], use_calibration: bool = False) -> Dict[str, Any]:
    """
    Calculate external validation metrics for Kaggle patients
    
    Args:
        patients: List of patient records with risk_score and sepsis_label
        use_calibration: If True, use calibrated probabilities instead of raw risk scores
    
    Returns:
        Dictionary of validation metrics
    """
    kaggle_patients = [
        p for p in patients 
        if p.get('id', '').startswith('kaggle-')
    ]
    
    if not kaggle_patients:
        return {
            "error": "No Kaggle patients found",
            "n_patients": 0
        }
    
    y_true = []
    risk_scores = []
    
    for p in kaggle_patients:
        cohort_tags = p.get('cohort_tags', [])
        if isinstance(cohort_tags, str):
            import json
            cohort_tags = json.loads(cohort_tags)
        
        sepsis_label = 0
        for tag in cohort_tags:
            if tag.startswith('sepsis_'):
                sepsis_label = int(tag.split('_')[1])
                break
        
        y_true.append(sepsis_label)
        risk_scores.append(p.get('risk_score', 0))
    
    y_true = np.array(y_true)
    risk_scores = np.array(risk_scores)
    
    if use_calibration:
        try:
            from app.model_calibration import RiskScoreCalibrator
            calibrator_path = Path(__file__).parent.parent / 'calibrator.pkl'
            if calibrator_path.exists():
                calibrator = RiskScoreCalibrator()
                calibrator.load(str(calibrator_path))
                y_pred_proba = calibrator.predict_proba(risk_scores)
            else:
                y_pred_proba = risk_scores / 100.0
        except Exception as e:
            print(f"Warning: Could not load calibrator: {e}")
            y_pred_proba = risk_scores / 100.0
    else:
        y_pred_proba = risk_scores / 100.0
    
    y_pred = (y_pred_proba >= 0.5).astype(int)
    
    try:
        auroc = roc_auc_score(y_true, y_pred_proba)
        auprc = average_precision_score(y_true, y_pred_proba)
    except:
        auroc = 0.0
        auprc = 0.0
    
    try:
        f1 = f1_score(y_true, y_pred)
    except:
        f1 = 0.0
    
    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    except:
        tn, fp, fn, tp = 0, 0, 0, 0
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    
    return {
        "dataset": "kaggle",
        "n_patients": len(kaggle_patients),
        "n_sepsis": int(y_true.sum()),
        "n_non_sepsis": int((1 - y_true).sum()),
        "prevalence": float(y_true.mean()),
        "metrics": {
            "auroc": float(auroc),
            "auprc": float(auprc),
            "f1_score": float(f1),
            "accuracy": float(accuracy),
            "sensitivity": float(sensitivity),
            "specificity": float(specificity),
            "ppv": float(ppv),
            "npv": float(npv)
        },
        "confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn)
        }
    }
