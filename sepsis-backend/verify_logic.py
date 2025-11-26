import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from mock_patients import MOCK_PATIENTS
from typing import Dict

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

count = 0
print("High Risk Patients:")
for p in MOCK_PATIENTS:
    if is_patient_high_risk(p):
        count += 1
        print(f"- {p['name']} (Risk: {p['risk_score']})")

print(f"Total High Risk: {count}")
