"""
ETL Script for Kaggle Sepsis Dataset Integration
Maps Kaggle PhysioNet Challenge 2019 data to our patient model
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import random

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", 
               "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
               "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White"]

DIAGNOSES = [
    "Pneumonia", "Urinary Tract Infection", "Cellulitis", "Bacteremia",
    "Intra-abdominal Infection", "Surgical Site Infection", "Meningitis",
    "Endocarditis", "Osteomyelitis", "Septic Arthritis"
]

def generate_patient_name(patient_id: int) -> str:
    """Generate deterministic patient name from ID"""
    random.seed(patient_id)
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"

def generate_mrn(patient_id: int) -> str:
    """Generate deterministic MRN from patient ID"""
    return f"KGL-{patient_id:06d}"

def generate_room(patient_id: int) -> str:
    """Generate deterministic room assignment"""
    random.seed(patient_id)
    floor = random.randint(2, 5)
    room = random.randint(1, 30)
    return f"ICU-{floor}-{room:02d}"

def generate_diagnosis(patient_id: int) -> str:
    """Generate deterministic diagnosis"""
    random.seed(patient_id)
    return random.choice(DIAGNOSES)

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

def determine_risk_level(risk_score: float) -> str:
    """Determine risk level from score"""
    if risk_score >= 70:
        return "CRITICAL"
    elif risk_score >= 50:
        return "HIGH"
    elif risk_score >= 30:
        return "MODERATE"
    else:
        return "LOW"

def load_kaggle_dataset(csv_path: str, max_patients: Optional[int] = None, sample_strategy: str = "balanced") -> pd.DataFrame:
    """
    Load and process Kaggle sepsis dataset
    
    Args:
        csv_path: Path to Dataset.csv
        max_patients: Maximum number of patients to load (None = all)
        sample_strategy: "balanced" (equal sepsis/non-sepsis), "random", or "all"
    
    Returns:
        Processed DataFrame with patient records
    """
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    
    if max_patients and max_patients < df['Patient_ID'].nunique():
        if sample_strategy == "balanced":
            sepsis_patients = df[df['SepsisLabel'] == 1]['Patient_ID'].unique()
            non_sepsis_patients = df[df['SepsisLabel'] == 0]['Patient_ID'].unique()
            
            n_sepsis = min(max_patients // 2, len(sepsis_patients))
            n_non_sepsis = max_patients - n_sepsis
            
            selected_sepsis = np.random.choice(sepsis_patients, n_sepsis, replace=False)
            selected_non_sepsis = np.random.choice(non_sepsis_patients, n_non_sepsis, replace=False)
            
            selected_patients = np.concatenate([selected_sepsis, selected_non_sepsis])
            print(f"Sampled {len(selected_patients)} patients ({n_sepsis} sepsis, {n_non_sepsis} non-sepsis)")
        else:
            all_patients = df['Patient_ID'].unique()
            selected_patients = np.random.choice(all_patients, max_patients, replace=False)
            print(f"Randomly sampled {len(selected_patients)} patients")
        
        df = df[df['Patient_ID'].isin(selected_patients)]
    
    return df

def transform_to_patient_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Transform Kaggle dataset to our patient model format
    
    Returns:
        List of patient dictionaries compatible with our API
    """
    patients = []
    
    for patient_id, patient_df in df.groupby('Patient_ID'):
        latest = patient_df.iloc[-1]
        
        sirs = calculate_sirs_criteria(latest)
        risk_score = calculate_risk_score(latest, sirs)
        risk_level = determine_risk_level(risk_score)
        
        has_sepsis = patient_df['SepsisLabel'].max() == 1
        
        name = generate_patient_name(int(patient_id))
        mrn = generate_mrn(int(patient_id))
        room = generate_room(int(patient_id))
        diagnosis = generate_diagnosis(int(patient_id))
        
        patient = {
            "id": f"kaggle-{patient_id}",
            "name": name,
            "age": int(latest['Age']) if pd.notna(latest['Age']) else 65,
            "gender": "Male" if latest['Gender'] == 1 else "Female",
            "mrn": mrn,
            "room": room,
            "diagnosis": diagnosis,
            "admission_date": (datetime.now() - timedelta(hours=int(latest['ICULOS']))).isoformat(),
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "sirs_criteria": sirs,
            "sepsis_label": int(has_sepsis),  # Ground truth for validation
            "dataset_source": "kaggle",
            "vitals": {
                "current": {
                    "heart_rate": float(latest['HR']) if pd.notna(latest['HR']) else None,
                    "blood_pressure": f"{int(latest['SBP'])}/{int(latest['DBP'])}" if pd.notna(latest['SBP']) and pd.notna(latest['DBP']) else None,
                    "temperature": float(latest['Temp']) if pd.notna(latest['Temp']) else None,
                    "respiratory_rate": float(latest['Resp']) if pd.notna(latest['Resp']) else None,
                    "oxygen_saturation": float(latest['O2Sat']) if pd.notna(latest['O2Sat']) else None,
                    "map": float(latest['MAP']) if pd.notna(latest['MAP']) else None,
                }
            },
            "labs": {
                "current": {
                    "wbc": float(latest['WBC']) if pd.notna(latest['WBC']) else None,
                    "lactate": float(latest['Lactate']) if pd.notna(latest['Lactate']) else None,
                    "creatinine": float(latest['Creatinine']) if pd.notna(latest['Creatinine']) else None,
                    "glucose": float(latest['Glucose']) if pd.notna(latest['Glucose']) else None,
                    "hematocrit": float(latest['Hct']) if pd.notna(latest['Hct']) else None,
                    "platelets": float(latest['Platelets']) if pd.notna(latest['Platelets']) else None,
                }
            },
            "devices": [],  # No device info in Kaggle dataset
            "history_hours": int(latest['ICULOS']),  # ICU length of stay
            "time_series": patient_df[['Hour', 'HR', 'Temp', 'SBP', 'MAP', 'DBP', 'Resp', 'O2Sat', 
                                       'WBC', 'Lactate', 'Creatinine', 'Glucose']].to_dict('records')
        }
        
        patients.append(patient)
    
    return patients

def calculate_validation_metrics(patients: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate external validation metrics
    
    Args:
        patients: List of patient records with predictions and ground truth
    
    Returns:
        Dictionary of validation metrics
    """
    from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, confusion_matrix
    
    y_true = [p['sepsis_label'] for p in patients]
    y_pred_proba = [p['risk_score'] / 100.0 for p in patients]  # Normalize to 0-1
    
    y_pred = [1 if score >= 50 else 0 for score in [p['risk_score'] for p in patients]]
    
    auroc = roc_auc_score(y_true, y_pred_proba)
    auprc = average_precision_score(y_true, y_pred_proba)
    f1 = f1_score(y_true, y_pred)
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0
    
    return {
        "n_patients": len(patients),
        "n_sepsis": sum(y_true),
        "prevalence": sum(y_true) / len(y_true),
        "auroc": auroc,
        "auprc": auprc,
        "f1_score": f1,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "ppv": ppv,
        "npv": npv,
        "confusion_matrix": {
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn)
        }
    }

if __name__ == "__main__":
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    
    df = load_kaggle_dataset(csv_path, max_patients=100, sample_strategy="balanced")
    
    patients = transform_to_patient_records(df)
    
    print(f"\n=== Transformed {len(patients)} patients ===")
    print(f"Sample patient:")
    import json
    print(json.dumps(patients[0], indent=2, default=str))
    
    metrics = calculate_validation_metrics(patients)
    print(f"\n=== Validation Metrics ===")
    print(json.dumps(metrics, indent=2))
