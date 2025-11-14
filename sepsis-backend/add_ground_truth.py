#!/usr/bin/env python3
"""
Add clinical ground truth labels to all 34 patients for validation.
"""

import sys
sys.path.insert(0, '/home/ubuntu/sepsis-copilot/sepsis-backend')

from mock_patients import MOCK_PATIENTS
from datetime import datetime, timedelta
import json

def calculate_qsofa(patient):
    """Calculate qSOFA score (0-3)"""
    score = 0
    vitals = patient['vitals']['current']
    
    # Altered mental status (using notes as proxy)
    if any('lethargic' in note['note'].lower() or 'confused' in note['note'].lower() 
           for note in patient.get('notes', [])):
        score += 1
    
    # SBP ≤ 100 mmHg
    bp = vitals['blood_pressure'].split('/')
    if int(bp[0]) <= 100:
        score += 1
    
    # RR ≥ 22
    if vitals['respiratory_rate'] >= 22:
        score += 1
    
    return score

def calculate_sofa(patient):
    """Calculate SOFA score (0-24)"""
    score = 0
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    
    # Respiration (PaO2/FiO2 ratio - using SpO2 as proxy)
    if vitals['spo2'] < 90:
        score += 3
    elif vitals['spo2'] < 94:
        score += 2
    elif vitals['spo2'] < 96:
        score += 1
    
    # Coagulation (platelets - not in our data, skip)
    
    # Liver (bilirubin)
    if labs['bilirubin'] >= 12.0:
        score += 4
    elif labs['bilirubin'] >= 6.0:
        score += 3
    elif labs['bilirubin'] >= 2.0:
        score += 2
    elif labs['bilirubin'] >= 1.2:
        score += 1
    
    # Cardiovascular (MAP and vasopressors - using BP as proxy)
    bp = vitals['blood_pressure'].split('/')
    map_pressure = (int(bp[0]) + 2 * int(bp[1])) / 3
    if map_pressure < 70:
        score += 1
    
    # CNS (Glasgow Coma Scale - using notes as proxy)
    if any('lethargic' in note['note'].lower() or 'difficult to arouse' in note['note'].lower() 
           for note in patient.get('notes', [])):
        score += 2
    elif any('confused' in note['note'].lower() or 'disoriented' in note['note'].lower() 
             for note in patient.get('notes', [])):
        score += 1
    
    # Renal (creatinine and urine output)
    if labs['creatinine'] >= 5.0:
        score += 4
    elif labs['creatinine'] >= 3.5:
        score += 3
    elif labs['creatinine'] >= 2.0:
        score += 2
    elif labs['creatinine'] >= 1.2:
        score += 1
    
    return score

def determine_ground_truth(patient):
    """Determine clinical ground truth for each patient"""
    risk_level = patient['risk_level']
    diagnosis = patient['diagnosis'].lower()
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    
    # Determine sepsis confirmation
    sepsis_confirmed = False
    sepsis_source = None
    onset_time = None
    
    if risk_level == 'CRITICAL':
        sepsis_confirmed = True
        if 'uti' in diagnosis or 'urinary' in diagnosis:
            sepsis_source = 'urinary_tract'
        elif 'pneumonia' in diagnosis or 'cap' in diagnosis or 'respiratory' in diagnosis:
            sepsis_source = 'pneumonia'
        elif 'abdominal' in diagnosis or 'peritonitis' in diagnosis:
            sepsis_source = 'abdominal'
        else:
            sepsis_source = 'unknown'
        # Onset 6-12 hours ago for CRITICAL
        onset_time = (datetime.now() - timedelta(hours=8)).isoformat() + 'Z'
    
    elif risk_level == 'HIGH':
        sepsis_confirmed = True
        if 'pneumonia' in diagnosis or 'cap' in diagnosis:
            sepsis_source = 'pneumonia'
        elif 'uti' in diagnosis:
            sepsis_source = 'urinary_tract'
        elif 'cellulitis' in diagnosis or 'abscess' in diagnosis:
            sepsis_source = 'skin_soft_tissue'
        else:
            sepsis_source = 'unknown'
        # Onset 3-6 hours ago for HIGH
        onset_time = (datetime.now() - timedelta(hours=4)).isoformat() + 'Z'
    
    elif risk_level == 'MODERATE':
        # Some MODERATE patients have early sepsis, others have SIRS without sepsis
        if patient['sirs_criteria'] >= 3 and labs['lactate'] > 2.0:
            sepsis_confirmed = True
            if 'cholecystitis' in diagnosis or 'pancreatitis' in diagnosis:
                sepsis_source = 'abdominal'
            elif 'pneumonia' in diagnosis:
                sepsis_source = 'pneumonia'
            else:
                sepsis_source = 'unknown'
            onset_time = (datetime.now() - timedelta(hours=2)).isoformat() + 'Z'
        else:
            sepsis_confirmed = False
            sepsis_source = None
            onset_time = None
    
    else:  # LOW
        sepsis_confirmed = False
        sepsis_source = None
        onset_time = None
    
    # Determine organ dysfunction
    organ_dysfunction = {}
    
    bp = vitals['blood_pressure'].split('/')
    if int(bp[0]) < 90:
        organ_dysfunction['hypotension'] = True
    
    if vitals['spo2'] < 90:
        organ_dysfunction['hypoxemia'] = True
    
    if any('lethargic' in note['note'].lower() or 'confused' in note['note'].lower() or 'difficult to arouse' in note['note'].lower()
           for note in patient.get('notes', [])):
        organ_dysfunction['altered_mental_status'] = True
    
    if any('urine output' in note['note'].lower() and ('decreased' in note['note'].lower() or 'low' in note['note'].lower())
           for note in patient.get('notes', [])):
        organ_dysfunction['oliguria'] = True
    
    if labs['bilirubin'] > 2.0:
        organ_dysfunction['hyperbilirubinemia'] = True
    
    if labs['creatinine'] > 2.0:
        organ_dysfunction['acute_kidney_injury'] = True
    
    # Calculate scores
    qsofa = calculate_qsofa(patient)
    sofa = calculate_sofa(patient)
    
    return {
        'sepsis_confirmed': sepsis_confirmed,
        'sepsis_onset_time': onset_time,
        'sepsis_source': sepsis_source,
        'organ_dysfunction': organ_dysfunction,
        'qsofa_score': qsofa,
        'sofa_score': sofa
    }

# Add ground truth to all patients
for patient in MOCK_PATIENTS:
    ground_truth = determine_ground_truth(patient)
    patient['ground_truth'] = ground_truth

# Print summary
print("Ground Truth Summary:")
print(f"Total patients: {len(MOCK_PATIENTS)}")
print(f"Sepsis confirmed: {sum(1 for p in MOCK_PATIENTS if p['ground_truth']['sepsis_confirmed'])}")
print(f"No sepsis: {sum(1 for p in MOCK_PATIENTS if not p['ground_truth']['sepsis_confirmed'])}")
print()

print("By Risk Level:")
for level in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
    patients_at_level = [p for p in MOCK_PATIENTS if p['risk_level'] == level]
    sepsis_at_level = sum(1 for p in patients_at_level if p['ground_truth']['sepsis_confirmed'])
    print(f"{level}: {len(patients_at_level)} patients, {sepsis_at_level} with confirmed sepsis")

print()
print("Sepsis Sources:")
sources = {}
for p in MOCK_PATIENTS:
    if p['ground_truth']['sepsis_confirmed']:
        source = p['ground_truth']['sepsis_source']
        sources[source] = sources.get(source, 0) + 1
for source, count in sorted(sources.items()):
    print(f"  {source}: {count}")

print()
print("qSOFA Distribution:")
qsofa_dist = {}
for p in MOCK_PATIENTS:
    score = p['ground_truth']['qsofa_score']
    qsofa_dist[score] = qsofa_dist.get(score, 0) + 1
for score in sorted(qsofa_dist.keys()):
    print(f"  qSOFA {score}: {qsofa_dist[score]} patients")

print()
print("SOFA Distribution:")
sofa_dist = {}
for p in MOCK_PATIENTS:
    score = p['ground_truth']['sofa_score']
    sofa_dist[score] = sofa_dist.get(score, 0) + 1
for score in sorted(sofa_dist.keys()):
    print(f"  SOFA {score}: {sofa_dist[score]} patients")

# Write updated patients to file
with open('/home/ubuntu/sepsis-copilot/sepsis-backend/mock_patients_with_ground_truth.py', 'w') as f:
    f.write('\nMOCK_PATIENTS = ')
    f.write(json.dumps(MOCK_PATIENTS, indent=4))
    f.write('\n')

print()
print("✅ Ground truth labels added to all 34 patients")
print("✅ Saved to mock_patients_with_ground_truth.py")
