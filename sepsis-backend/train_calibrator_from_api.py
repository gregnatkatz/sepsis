"""
Train calibration model on Kaggle dataset from API
"""

import requests
import json
import numpy as np
from app.model_calibration import RiskScoreCalibrator
from sklearn.calibration import calibration_curve

API_URL = "http://127.0.0.1:8000"

def main():
    print("Fetching ALL patients from API (this may take a moment)...")
    response = requests.get(f"{API_URL}/api/patients?limit=50000")
    response_data = response.json()
    
    patients = response_data.get('patients', [])
    total = response_data.get('total', 0)
    
    print(f"Loaded {len(patients)} of {total} total patients")
    
    kaggle_patients = [p for p in patients if p.get('id', '').startswith('kaggle-')]
    print(f"Found {len(kaggle_patients)} Kaggle patients")
    
    if not kaggle_patients:
        print("ERROR: No Kaggle patients found!")
        return
    
    risk_scores = []
    labels = []
    
    for p in kaggle_patients:
        cohort_tags = p.get('cohort_tags', [])
        if isinstance(cohort_tags, str):
            cohort_tags = json.loads(cohort_tags)
        
        sepsis_label = 0
        for tag in cohort_tags:
            if tag.startswith('sepsis_'):
                sepsis_label = int(tag.split('_')[1])
                break
        
        risk_scores.append(p.get('risk_score', 0))
        labels.append(sepsis_label)
    
    risk_scores = np.array(risk_scores)
    labels = np.array(labels)
    
    print(f"\nDataset Statistics:")
    print(f"  Total patients: {len(kaggle_patients)}")
    print(f"  Sepsis cases: {labels.sum()} ({labels.mean()*100:.1f}%)")
    print(f"  Non-sepsis: {(1-labels).sum()} ({(1-labels.mean())*100:.1f}%)")
    print(f"  Risk score range: {risk_scores.min():.1f} - {risk_scores.max():.1f}")
    print(f"  Risk score mean: {risk_scores.mean():.1f}")
    
    print("\nTraining calibrator...")
    calibrator = RiskScoreCalibrator()
    metrics = calibrator.fit(risk_scores, labels)
    
    calibrator.save('calibrator.pkl')
    print("Calibrator saved to calibrator.pkl")
    
    print("\nCalibration Metrics:")
    print(json.dumps(metrics, indent=2))
    
    test_scores = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
    calibrated_probs = calibrator.predict_proba(test_scores)
    
    print("\nCalibrated Probabilities:")
    print("Risk Score -> Calibrated Probability")
    for score, prob in zip(test_scores, calibrated_probs):
        print(f"{score:3.0f} -> {prob:.4f} ({prob*100:.2f}%)")
    
    print("\n" + "="*60)
    print("CALIBRATION IMPACT ANALYSIS")
    print("="*60)
    
    original_probs = risk_scores / 100.0
    
    calibrated_probs_all = calibrator.predict_proba(risk_scores)
    
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    print("\nPerformance at different probability thresholds:")
    print(f"{'Threshold':<12} {'Original PPV':<15} {'Calibrated PPV':<15} {'Improvement'}")
    print("-" * 60)
    
    for thresh in thresholds:
        orig_pred = (original_probs >= thresh).astype(int)
        orig_tp = ((orig_pred == 1) & (labels == 1)).sum()
        orig_fp = ((orig_pred == 1) & (labels == 0)).sum()
        orig_ppv = orig_tp / (orig_tp + orig_fp) if (orig_tp + orig_fp) > 0 else 0
        
        cal_pred = (calibrated_probs_all >= thresh).astype(int)
        cal_tp = ((cal_pred == 1) & (labels == 1)).sum()
        cal_fp = ((cal_pred == 1) & (labels == 0)).sum()
        cal_ppv = cal_tp / (cal_tp + cal_fp) if (cal_tp + cal_fp) > 0 else 0
        
        improvement = ((cal_ppv - orig_ppv) / orig_ppv * 100) if orig_ppv > 0 else 0
        
        print(f"{thresh:<12.1f} {orig_ppv*100:<15.1f} {cal_ppv*100:<15.1f} {improvement:+.1f}%")

if __name__ == "__main__":
    main()
