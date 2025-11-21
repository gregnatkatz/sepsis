import sys
import os
from typing import Dict

# Add current directory to path to import mock_patients
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mock_patients import MOCK_PATIENTS

def is_patient_high_risk(patient: Dict) -> bool:
    """
    Determine if a patient is high risk using Smart Logic to improve PPV.
    Criteria:
    1. Risk Score >= 60 (Standard High Risk)
    OR
    2. Risk Score >= 50 AND (SIRS >= 3 OR Lactate > 2.0) (Catch missed cases like Necrotizing Fasciitis)
    """
    risk_score = patient.get("risk_score", 0)
    
    # Criteria 1: High base risk
    if risk_score >= 60:
        return True
        
    # Criteria 2: Moderate risk with clinical warning signs
    if risk_score >= 50:
        # Check SIRS
        sirs_count = patient.get("sirs_criteria", 0)
        if isinstance(sirs_count, dict): # Handle if it's a dict from calculate_sirs_criteria
            sirs_count = sirs_count.get("count", 0)
            
        # Check Lactate
        lactate = 0.0
        if "labs" in patient and "current" in patient["labs"]:
             lactate = patient["labs"]["current"].get("lactate", 0.0)
             
        if sirs_count >= 3 or lactate > 2.0:
            return True
            
    return False

def calculate_metrics():
    """
    Calculate PPV, Sensitivity, and Specificity based on Smart Logic.
    """
    tp = 0
    fp = 0
    tn = 0
    fn = 0
    
    false_positives = []
    false_negatives = []
    
    print(f"Analyzing {len(MOCK_PATIENTS)} patients with Smart Logic...")
    print("Criteria: Risk >= 60 OR (Risk >= 50 AND (SIRS >= 3 OR Lactate > 2.0))")
    
    for patient in MOCK_PATIENTS:
        # Check ground truth - handle missing key gracefully
        ground_truth = patient.get("ground_truth", {})
        is_septic = ground_truth.get("sepsis_confirmed", False)
        
        is_alert = is_patient_high_risk(patient)
        
        if is_alert and is_septic:
            tp += 1
        elif is_alert and not is_septic:
            fp += 1
            false_positives.append(patient)
        elif not is_alert and not is_septic:
            tn += 1
        elif not is_alert and is_septic:
            fn += 1
            false_negatives.append(patient)
            
    # Calculate metrics
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    
    print("\n" + "="*40)
    print(f"METRICS (Smart Logic)")
    print("="*40)
    print(f"True Positives (TP): {tp}")
    print(f"False Positives (FP): {fp}")
    print(f"True Negatives (TN): {tn}")
    print(f"False Negatives (FN): {fn}")
    print("-" * 20)
    print(f"PPV (Precision): {ppv:.2%}")
    print(f"Sensitivity (Recall): {sensitivity:.2%}")
    print(f"Specificity: {specificity:.2%}")
    print("="*40)
    
    if false_positives:
        print("\n[!] FALSE POSITIVES (Alerted but No Sepsis):")
        for p in false_positives:
            print(f"  - {p['name']} (ID: {p['id']}) | Risk: {p['risk_score']} | Diagnosis: {p['diagnosis']}")
            
    if false_negatives:
        print("\n[x] FALSE NEGATIVES (Sepsis but No Alert):")
        for p in false_negatives:
            print(f"  - {p['name']} (ID: {p['id']}) | Risk: {p['risk_score']} | Diagnosis: {p['diagnosis']}")

if __name__ == "__main__":
    calculate_metrics()
