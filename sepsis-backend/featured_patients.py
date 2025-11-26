"""
Featured Patients for Clinical Workflow Demo
4 realistic patients with different sepsis presentations and comprehensive EHR-like data.
Each patient has 120-hour history data similar to what you'd see in EPIC.
"""

from datetime import datetime, timedelta
import random

def generate_120hr_vitals_history(base_vitals: dict, trajectory: str = "worsening") -> list:
    """Generate 120 hours of vitals history (every 4 hours = 30 data points)"""
    history = []
    now = datetime.now()
    
    for i in range(30):  # 30 readings over 120 hours
        hours_ago = 120 - (i * 4)
        timestamp = now - timedelta(hours=hours_ago)
        
        # Calculate progression factor (0 to 1 over 120 hours)
        progress = i / 29
        
        if trajectory == "worsening":
            hr_delta = progress * 30  # HR increases by 30 over time
            temp_delta = progress * 1.5  # Temp increases by 1.5C
            bp_delta = -progress * 20  # BP drops by 20
            rr_delta = progress * 10  # RR increases by 10
            spo2_delta = -progress * 8  # SpO2 drops by 8
        elif trajectory == "improving":
            hr_delta = -progress * 20
            temp_delta = -progress * 1.0
            bp_delta = progress * 15
            rr_delta = -progress * 6
            spo2_delta = progress * 5
        else:  # stable
            hr_delta = random.uniform(-5, 5)
            temp_delta = random.uniform(-0.3, 0.3)
            bp_delta = random.uniform(-5, 5)
            rr_delta = random.uniform(-2, 2)
            spo2_delta = random.uniform(-1, 1)
        
        # Add some noise
        noise = random.uniform(-3, 3)
        
        vitals_point = {
            "timestamp": timestamp.isoformat(),
            "heart_rate": round(base_vitals["heart_rate"] + hr_delta + noise),
            "temperature": round(base_vitals["temperature"] + temp_delta + random.uniform(-0.2, 0.2), 1),
            "systolic_bp": round(base_vitals["systolic_bp"] + bp_delta + noise),
            "diastolic_bp": round(base_vitals["diastolic_bp"] + (bp_delta * 0.6) + noise * 0.5),
            "respiratory_rate": round(base_vitals["respiratory_rate"] + rr_delta + random.uniform(-2, 2)),
            "spo2": min(100, max(80, round(base_vitals["spo2"] + spo2_delta + random.uniform(-1, 1))))
        }
        history.append(vitals_point)
    
    return history


def generate_120hr_labs_history(base_labs: dict, trajectory: str = "worsening") -> list:
    """Generate 120 hours of labs history (every 8 hours = 15 data points)"""
    history = []
    now = datetime.now()
    
    for i in range(15):  # 15 readings over 120 hours
        hours_ago = 120 - (i * 8)
        timestamp = now - timedelta(hours=hours_ago)
        
        progress = i / 14
        
        if trajectory == "worsening":
            lactate_delta = progress * 2.5
            wbc_delta = progress * 10
            creatinine_delta = progress * 1.0
            bilirubin_delta = progress * 0.8
        elif trajectory == "improving":
            lactate_delta = -progress * 1.5
            wbc_delta = -progress * 5
            creatinine_delta = -progress * 0.5
            bilirubin_delta = -progress * 0.3
        else:
            lactate_delta = random.uniform(-0.3, 0.3)
            wbc_delta = random.uniform(-1, 1)
            creatinine_delta = random.uniform(-0.1, 0.1)
            bilirubin_delta = random.uniform(-0.1, 0.1)
        
        labs_point = {
            "timestamp": timestamp.isoformat(),
            "lactate": round(max(0.5, base_labs["lactate"] + lactate_delta + random.uniform(-0.2, 0.2)), 1),
            "wbc": round(max(2, base_labs["wbc"] + wbc_delta + random.uniform(-1, 1)), 1),
            "creatinine": round(max(0.5, base_labs["creatinine"] + creatinine_delta + random.uniform(-0.1, 0.1)), 1),
            "bilirubin": round(max(0.2, base_labs["bilirubin"] + bilirubin_delta + random.uniform(-0.1, 0.1)), 1),
            "platelets": round(max(50, 250 - progress * 100 + random.uniform(-20, 20))),
            "procalcitonin": round(max(0.1, progress * 5 + random.uniform(-0.5, 0.5)), 2) if trajectory == "worsening" else round(max(0.1, 2 - progress * 1.5), 2),
            "crp": round(max(1, progress * 150 + random.uniform(-10, 10)), 1) if trajectory == "worsening" else round(max(1, 100 - progress * 80), 1)
        }
        history.append(labs_point)
    
    return history


# Patient 1: Septic Shock from UTI (Critical, Worsening)
PATIENT_UTI_SEPTIC_SHOCK = {
    "id": "DEMO-001",
    "mrn": "MRN-2025-001",
    "name": "Eleanor Martinez",
    "age": 78,
    "gender": "F",
    "room": "ICU-12",
    "bed": "A",
    "admission_date": "2025-11-21",
    "admission_time": "14:30",
    "attending_physician": "Dr. Sarah Chen",
    "primary_nurse": "RN Jennifer Walsh",
    "diagnosis": "Urosepsis with septic shock",
    "chief_complaint": "Altered mental status, fever, decreased urine output",
    "risk_score": 94,
    "risk_level": "CRITICAL",
    "sirs_criteria": 4,
    
    # Current vitals
    "vitals": {
        "current": {
            "heart_rate": 122,
            "blood_pressure": "82/48",
            "respiratory_rate": 28,
            "temperature": 39.4,
            "spo2": 89,
            "map": 59
        },
        "previous": {
            "heart_rate": 108,
            "blood_pressure": "94/58",
            "respiratory_rate": 24,
            "temperature": 38.8,
            "spo2": 92,
            "map": 70
        }
    },
    
    # Current labs
    "labs": {
        "current": {
            "lactate": 4.2,
            "wbc": 22.5,
            "creatinine": 2.8,
            "bilirubin": 2.1,
            "platelets": 98,
            "procalcitonin": 8.5,
            "crp": 185,
            "bun": 45,
            "glucose": 165,
            "potassium": 5.2,
            "sodium": 138,
            "hemoglobin": 10.2,
            "inr": 1.4
        },
        "previous": {
            "lactate": 3.1,
            "wbc": 18.2,
            "creatinine": 2.2,
            "bilirubin": 1.6,
            "platelets": 125,
            "procalcitonin": 5.2,
            "crp": 142
        }
    },
    
    # Devices
    "devices": [
        {"type": "Foley catheter", "days": 5, "inserted": "2025-11-21"},
        {"type": "Central line (R IJ)", "days": 2, "inserted": "2025-11-24"},
        {"type": "Arterial line (L radial)", "days": 1, "inserted": "2025-11-25"},
        {"type": "Peripheral IV x2", "days": 5, "inserted": "2025-11-21"}
    ],
    
    # Medications
    "medications": [
        {"name": "Norepinephrine", "dose": "0.15 mcg/kg/min", "route": "IV", "frequency": "Continuous", "start": "2025-11-25 08:00"},
        {"name": "Piperacillin-Tazobactam", "dose": "4.5g", "route": "IV", "frequency": "Q6H", "start": "2025-11-21 16:00"},
        {"name": "Vancomycin", "dose": "1g", "route": "IV", "frequency": "Q12H", "start": "2025-11-21 16:00"},
        {"name": "Lactated Ringer's", "dose": "125 mL/hr", "route": "IV", "frequency": "Continuous", "start": "2025-11-21 14:30"},
        {"name": "Pantoprazole", "dose": "40mg", "route": "IV", "frequency": "Daily", "start": "2025-11-21 14:30"},
        {"name": "Heparin", "dose": "5000 units", "route": "SQ", "frequency": "Q8H", "start": "2025-11-22 08:00"}
    ],
    
    # Nursing notes (last 24 hours)
    "notes": [
        {"time": "07:00", "author": "RN Walsh", "note": "Patient increasingly lethargic, difficult to arouse. MAP dropped to 59, norepinephrine increased to 0.15 mcg/kg/min. Urine output 15 mL/hr x 3 hours. MD notified."},
        {"time": "05:30", "author": "RN Walsh", "note": "Lactate resulted at 4.2, up from 3.1. Blood cultures x2 drawn from central line and peripheral. Repeat lactate ordered."},
        {"time": "03:00", "author": "RN Walsh", "note": "Patient febrile to 39.4C. Cooling measures initiated. Tylenol 650mg given per rectum."},
        {"time": "23:00", "author": "RN Martinez", "note": "Patient confused, not following commands. Family at bedside, updated on condition. Goals of care discussion pending."},
        {"time": "19:00", "author": "RN Martinez", "note": "Received patient from ED. Sepsis protocol initiated. 30 mL/kg fluid bolus given. Blood cultures sent prior to antibiotics."}
    ],
    
    # Problem list
    "problem_list": [
        {"problem": "Septic shock secondary to urosepsis", "status": "Active", "onset": "2025-11-21"},
        {"problem": "Acute kidney injury (KDIGO Stage 2)", "status": "Active", "onset": "2025-11-22"},
        {"problem": "Thrombocytopenia", "status": "Active", "onset": "2025-11-24"},
        {"problem": "Type 2 Diabetes Mellitus", "status": "Chronic", "onset": "2010"},
        {"problem": "Hypertension", "status": "Chronic", "onset": "2005"},
        {"problem": "Atrial fibrillation", "status": "Chronic", "onset": "2018"},
        {"problem": "Recurrent UTIs", "status": "Chronic", "onset": "2020"}
    ],
    
    # Allergies
    "allergies": [
        {"allergen": "Penicillin", "reaction": "Rash", "severity": "Moderate"},
        {"allergen": "Sulfa drugs", "reaction": "Anaphylaxis", "severity": "Severe"}
    ],
    
    # Sepsis bundle status
    "sepsis_bundle": {
        "lactate_measured": {"status": "complete", "time": "2025-11-21 14:45", "value": 2.8},
        "blood_cultures": {"status": "complete", "time": "2025-11-21 15:00", "result": "Pending"},
        "antibiotics": {"status": "complete", "time": "2025-11-21 16:00", "within_1hr": True},
        "fluid_resuscitation": {"status": "complete", "time": "2025-11-21 15:30", "volume_ml": 2100},
        "vasopressors": {"status": "complete", "time": "2025-11-25 08:00", "agent": "Norepinephrine"},
        "repeat_lactate": {"status": "complete", "time": "2025-11-26 05:30", "value": 4.2}
    },
    
    # Ground truth
    "ground_truth": {
        "sepsis_confirmed": True,
        "sepsis_onset_time": "2025-11-21T14:30:00Z",
        "sepsis_source": "urinary_tract",
        "organism": "E. coli (ESBL)",
        "organ_dysfunction": {
            "hypotension": True,
            "altered_mental_status": True,
            "oliguria": True,
            "acute_kidney_injury": True,
            "thrombocytopenia": True
        },
        "qsofa_score": 3,
        "sofa_score": 11
    }
}


# Patient 2: Pneumonia Sepsis (High Risk, Worsening)
PATIENT_PNEUMONIA_SEPSIS = {
    "id": "DEMO-002",
    "mrn": "MRN-2025-002",
    "name": "Robert Thompson",
    "age": 72,
    "gender": "M",
    "room": "3E-405",
    "bed": "B",
    "admission_date": "2025-11-23",
    "admission_time": "09:15",
    "attending_physician": "Dr. Michael Park",
    "primary_nurse": "RN David Kim",
    "diagnosis": "Severe community-acquired pneumonia with sepsis",
    "chief_complaint": "Productive cough, shortness of breath, fever x 3 days",
    "risk_score": 78,
    "risk_level": "HIGH",
    "sirs_criteria": 3,
    
    "vitals": {
        "current": {
            "heart_rate": 108,
            "blood_pressure": "98/62",
            "respiratory_rate": 26,
            "temperature": 38.9,
            "spo2": 91,
            "map": 74
        },
        "previous": {
            "heart_rate": 98,
            "blood_pressure": "108/68",
            "respiratory_rate": 22,
            "temperature": 38.4,
            "spo2": 94,
            "map": 81
        }
    },
    
    "labs": {
        "current": {
            "lactate": 2.8,
            "wbc": 18.5,
            "creatinine": 1.6,
            "bilirubin": 1.2,
            "platelets": 165,
            "procalcitonin": 4.2,
            "crp": 125,
            "bun": 28,
            "glucose": 142,
            "potassium": 4.1,
            "sodium": 140,
            "hemoglobin": 11.8,
            "pao2": 62,
            "paco2": 32
        },
        "previous": {
            "lactate": 2.1,
            "wbc": 15.2,
            "creatinine": 1.3,
            "bilirubin": 1.0,
            "platelets": 185,
            "procalcitonin": 2.8,
            "crp": 98
        }
    },
    
    "devices": [
        {"type": "Peripheral IV x2", "days": 3, "inserted": "2025-11-23"},
        {"type": "Nasal cannula O2", "days": 3, "inserted": "2025-11-23", "flow": "4L/min"}
    ],
    
    "medications": [
        {"name": "Ceftriaxone", "dose": "2g", "route": "IV", "frequency": "Q24H", "start": "2025-11-23 10:00"},
        {"name": "Azithromycin", "dose": "500mg", "route": "IV", "frequency": "Q24H", "start": "2025-11-23 10:00"},
        {"name": "Normal Saline", "dose": "100 mL/hr", "route": "IV", "frequency": "Continuous", "start": "2025-11-23 09:30"},
        {"name": "Albuterol", "dose": "2.5mg", "route": "Nebulizer", "frequency": "Q4H PRN", "start": "2025-11-23 09:30"},
        {"name": "Acetaminophen", "dose": "650mg", "route": "PO", "frequency": "Q6H PRN", "start": "2025-11-23 09:30"}
    ],
    
    "notes": [
        {"time": "06:30", "author": "RN Kim", "note": "O2 requirement increased, now on 4L NC to maintain SpO2 > 90%. Respiratory therapy consulted for possible BiPAP."},
        {"time": "04:00", "author": "RN Kim", "note": "Patient reports worsening dyspnea. Chest X-ray shows progression of right lower lobe infiltrate with new left lower lobe involvement."},
        {"time": "00:00", "author": "RN Santos", "note": "Febrile to 38.9C. Blood cultures drawn. Lactate 2.8, up from 2.1. MD notified."},
        {"time": "20:00", "author": "RN Santos", "note": "Patient resting comfortably. Cough productive of yellow-green sputum. Sputum culture sent."}
    ],
    
    "problem_list": [
        {"problem": "Severe community-acquired pneumonia", "status": "Active", "onset": "2025-11-23"},
        {"problem": "Sepsis", "status": "Active", "onset": "2025-11-24"},
        {"problem": "Acute hypoxemic respiratory failure", "status": "Active", "onset": "2025-11-25"},
        {"problem": "COPD", "status": "Chronic", "onset": "2015"},
        {"problem": "Former smoker (40 pack-years)", "status": "Chronic", "onset": "1975"},
        {"problem": "Coronary artery disease", "status": "Chronic", "onset": "2019"}
    ],
    
    "allergies": [
        {"allergen": "Codeine", "reaction": "Nausea/vomiting", "severity": "Mild"}
    ],
    
    "sepsis_bundle": {
        "lactate_measured": {"status": "complete", "time": "2025-11-23 09:30", "value": 1.8},
        "blood_cultures": {"status": "complete", "time": "2025-11-24 00:00", "result": "Streptococcus pneumoniae"},
        "antibiotics": {"status": "complete", "time": "2025-11-23 10:00", "within_1hr": True},
        "fluid_resuscitation": {"status": "complete", "time": "2025-11-23 10:30", "volume_ml": 1500},
        "vasopressors": {"status": "not_indicated", "time": None, "agent": None},
        "repeat_lactate": {"status": "complete", "time": "2025-11-26 00:00", "value": 2.8}
    },
    
    "ground_truth": {
        "sepsis_confirmed": True,
        "sepsis_onset_time": "2025-11-24T00:00:00Z",
        "sepsis_source": "pneumonia",
        "organism": "Streptococcus pneumoniae",
        "organ_dysfunction": {
            "hypoxemia": True,
            "tachypnea": True
        },
        "qsofa_score": 2,
        "sofa_score": 5
    }
}


# Patient 3: Necrotizing Fasciitis (Moderate Risk, Rapidly Worsening - Smart Logic catch)
PATIENT_NEC_FASC = {
    "id": "DEMO-003",
    "mrn": "MRN-2025-003",
    "name": "William Chen",
    "age": 58,
    "gender": "M",
    "room": "3E-218",
    "bed": "A",
    "admission_date": "2025-11-25",
    "admission_time": "22:00",
    "attending_physician": "Dr. Lisa Rodriguez",
    "primary_nurse": "RN Amanda Foster",
    "diagnosis": "Cellulitis vs necrotizing fasciitis, left lower extremity",
    "chief_complaint": "Rapidly spreading leg redness, severe pain out of proportion to exam",
    "risk_score": 52,  # Moderate score but Smart Logic catches due to SIRS + lactate
    "risk_level": "MODERATE",
    "sirs_criteria": 3,
    
    "vitals": {
        "current": {
            "heart_rate": 112,
            "blood_pressure": "105/65",
            "respiratory_rate": 24,
            "temperature": 38.6,
            "spo2": 96,
            "map": 78
        },
        "previous": {
            "heart_rate": 95,
            "blood_pressure": "118/72",
            "respiratory_rate": 18,
            "temperature": 37.8,
            "spo2": 98,
            "map": 87
        }
    },
    
    "labs": {
        "current": {
            "lactate": 2.4,
            "wbc": 16.8,
            "creatinine": 1.4,
            "bilirubin": 0.9,
            "platelets": 145,
            "procalcitonin": 2.1,
            "crp": 95,
            "bun": 22,
            "glucose": 185,
            "potassium": 4.5,
            "sodium": 136,
            "hemoglobin": 12.5,
            "ck": 850
        },
        "previous": {
            "lactate": 1.6,
            "wbc": 12.5,
            "creatinine": 1.1,
            "bilirubin": 0.8,
            "platelets": 175,
            "procalcitonin": 0.8,
            "crp": 45
        }
    },
    
    "devices": [
        {"type": "Peripheral IV x2", "days": 1, "inserted": "2025-11-25"}
    ],
    
    "medications": [
        {"name": "Vancomycin", "dose": "1.5g", "route": "IV", "frequency": "Q12H", "start": "2025-11-25 23:00"},
        {"name": "Piperacillin-Tazobactam", "dose": "4.5g", "route": "IV", "frequency": "Q6H", "start": "2025-11-25 23:00"},
        {"name": "Clindamycin", "dose": "900mg", "route": "IV", "frequency": "Q8H", "start": "2025-11-25 23:00"},
        {"name": "Morphine", "dose": "2-4mg", "route": "IV", "frequency": "Q2H PRN", "start": "2025-11-25 22:30"},
        {"name": "Normal Saline", "dose": "150 mL/hr", "route": "IV", "frequency": "Continuous", "start": "2025-11-25 22:00"}
    ],
    
    "notes": [
        {"time": "06:00", "author": "RN Foster", "note": "URGENT: Erythema has spread 3cm in last 4 hours despite antibiotics. Pain 10/10, requiring frequent morphine. Crepitus now palpable. Surgery consulted STAT for possible OR."},
        {"time": "04:00", "author": "RN Foster", "note": "Marked erythema borders with skin marker. Patient extremely anxious, reports 'worst pain of my life'. Lactate trending up to 2.4."},
        {"time": "02:00", "author": "RN Foster", "note": "CT scan completed - radiologist reports 'gas tracking along fascial planes concerning for necrotizing soft tissue infection'. MD notified."},
        {"time": "22:30", "author": "RN Foster", "note": "Admitted from ED with rapidly progressive cellulitis. Started on broad-spectrum antibiotics. Blood cultures x2 sent."}
    ],
    
    "problem_list": [
        {"problem": "Suspected necrotizing fasciitis, left lower extremity", "status": "Active", "onset": "2025-11-25"},
        {"problem": "Sepsis", "status": "Active", "onset": "2025-11-26"},
        {"problem": "Type 2 Diabetes Mellitus (poorly controlled)", "status": "Chronic", "onset": "2008"},
        {"problem": "Peripheral vascular disease", "status": "Chronic", "onset": "2020"},
        {"problem": "Obesity (BMI 34)", "status": "Chronic", "onset": "2010"}
    ],
    
    "allergies": [],
    
    "sepsis_bundle": {
        "lactate_measured": {"status": "complete", "time": "2025-11-25 22:15", "value": 1.6},
        "blood_cultures": {"status": "complete", "time": "2025-11-25 22:30", "result": "Pending"},
        "antibiotics": {"status": "complete", "time": "2025-11-25 23:00", "within_1hr": True},
        "fluid_resuscitation": {"status": "in_progress", "time": "2025-11-25 22:00", "volume_ml": 1800},
        "vasopressors": {"status": "not_indicated", "time": None, "agent": None},
        "repeat_lactate": {"status": "complete", "time": "2025-11-26 04:00", "value": 2.4}
    },
    
    "ground_truth": {
        "sepsis_confirmed": True,
        "sepsis_onset_time": "2025-11-26T02:00:00Z",
        "sepsis_source": "skin_soft_tissue",
        "organism": "Group A Streptococcus (pending)",
        "organ_dysfunction": {
            "tachycardia": True,
            "tachypnea": True
        },
        "qsofa_score": 1,
        "sofa_score": 3
    }
}


# Patient 4: Post-op Abdominal Sepsis (Watchlist - Borderline)
PATIENT_POSTOP_ABDOMINAL = {
    "id": "DEMO-004",
    "mrn": "MRN-2025-004",
    "name": "Margaret O'Brien",
    "age": 65,
    "gender": "F",
    "room": "4W-112",
    "bed": "A",
    "admission_date": "2025-11-22",
    "admission_time": "06:00",
    "attending_physician": "Dr. James Wilson",
    "primary_nurse": "RN Patricia Lee",
    "diagnosis": "Post-operative day 4, sigmoid colectomy for diverticulitis",
    "chief_complaint": "Scheduled surgery for recurrent diverticulitis",
    "risk_score": 45,  # Watchlist candidate
    "risk_level": "MODERATE",
    "sirs_criteria": 2,
    
    "vitals": {
        "current": {
            "heart_rate": 95,
            "blood_pressure": "112/68",
            "respiratory_rate": 20,
            "temperature": 38.2,
            "spo2": 96,
            "map": 83
        },
        "previous": {
            "heart_rate": 88,
            "blood_pressure": "118/72",
            "respiratory_rate": 18,
            "temperature": 37.5,
            "spo2": 97,
            "map": 87
        }
    },
    
    "labs": {
        "current": {
            "lactate": 1.8,
            "wbc": 14.2,
            "creatinine": 1.0,
            "bilirubin": 0.7,
            "platelets": 195,
            "procalcitonin": 0.9,
            "crp": 65,
            "bun": 18,
            "glucose": 128,
            "potassium": 3.8,
            "sodium": 139,
            "hemoglobin": 10.5
        },
        "previous": {
            "lactate": 1.4,
            "wbc": 11.5,
            "creatinine": 0.9,
            "bilirubin": 0.6,
            "platelets": 210,
            "procalcitonin": 0.4,
            "crp": 42
        }
    },
    
    "devices": [
        {"type": "Peripheral IV", "days": 4, "inserted": "2025-11-22"},
        {"type": "Foley catheter", "days": 4, "inserted": "2025-11-22"},
        {"type": "JP drain x1", "days": 4, "inserted": "2025-11-22", "output": "50mL serosanguinous"}
    ],
    
    "medications": [
        {"name": "Cefazolin", "dose": "2g", "route": "IV", "frequency": "Q8H", "start": "2025-11-22 06:00"},
        {"name": "Metronidazole", "dose": "500mg", "route": "IV", "frequency": "Q8H", "start": "2025-11-22 06:00"},
        {"name": "Heparin", "dose": "5000 units", "route": "SQ", "frequency": "Q8H", "start": "2025-11-22 18:00"},
        {"name": "Acetaminophen", "dose": "650mg", "route": "PO", "frequency": "Q6H PRN", "start": "2025-11-22 12:00"},
        {"name": "Ondansetron", "dose": "4mg", "route": "IV", "frequency": "Q8H PRN", "start": "2025-11-22 12:00"}
    ],
    
    "notes": [
        {"time": "07:30", "author": "RN Lee", "note": "New low-grade fever 38.2C this morning. WBC trending up to 14.2. Surgical site clean, no erythema. JP drain output slightly increased. MD aware, monitoring closely."},
        {"time": "04:00", "author": "RN Lee", "note": "Patient reports mild abdominal discomfort, different from incisional pain. Bowel sounds hypoactive. No flatus yet."},
        {"time": "20:00", "author": "RN Martinez", "note": "POD 3, tolerating clear liquids. Ambulated x2 with PT. Pain controlled with oral meds."},
        {"time": "12:00", "author": "RN Martinez", "note": "Foley catheter in place - consider removal per CAUTI bundle. Patient voiding around catheter."}
    ],
    
    "problem_list": [
        {"problem": "Post-operative sigmoid colectomy", "status": "Active", "onset": "2025-11-22"},
        {"problem": "Post-operative ileus", "status": "Active", "onset": "2025-11-24"},
        {"problem": "Diverticulitis (recurrent)", "status": "Resolved", "onset": "2025-11-15"},
        {"problem": "Hypertension", "status": "Chronic", "onset": "2012"},
        {"problem": "Hypothyroidism", "status": "Chronic", "onset": "2018"}
    ],
    
    "allergies": [
        {"allergen": "Latex", "reaction": "Contact dermatitis", "severity": "Moderate"}
    ],
    
    "sepsis_bundle": {
        "lactate_measured": {"status": "complete", "time": "2025-11-26 06:00", "value": 1.8},
        "blood_cultures": {"status": "pending", "time": None, "result": None},
        "antibiotics": {"status": "on_prophylaxis", "time": "2025-11-22 06:00", "within_1hr": None},
        "fluid_resuscitation": {"status": "not_indicated", "time": None, "volume_ml": None},
        "vasopressors": {"status": "not_indicated", "time": None, "agent": None},
        "repeat_lactate": {"status": "ordered", "time": None, "value": None}
    },
    
    "ground_truth": {
        "sepsis_confirmed": False,
        "sepsis_onset_time": None,
        "sepsis_source": None,
        "organism": None,
        "organ_dysfunction": {},
        "qsofa_score": 0,
        "sofa_score": 1
    }
}


# Export all featured patients
FEATURED_PATIENTS = [
    PATIENT_UTI_SEPTIC_SHOCK,
    PATIENT_PNEUMONIA_SEPSIS,
    PATIENT_NEC_FASC,
    PATIENT_POSTOP_ABDOMINAL
]


def get_featured_patients_with_history():
    """Get featured patients with generated 120-hour history data"""
    patients_with_history = []
    
    for patient in FEATURED_PATIENTS:
        patient_copy = {**patient}
        
        # Determine trajectory based on ground truth
        if patient["ground_truth"]["sepsis_confirmed"]:
            trajectory = "worsening"
        elif patient["risk_score"] >= 40:
            trajectory = "stable"
        else:
            trajectory = "improving"
        
        # Generate base values for history generation
        vitals_current = patient["vitals"]["current"]
        base_vitals = {
            "heart_rate": vitals_current.get("heart_rate", 80) - 20,
            "temperature": vitals_current.get("temperature", 37.0) - 1.0,
            "systolic_bp": int(vitals_current.get("blood_pressure", "120/80").split("/")[0]) + 15,
            "diastolic_bp": int(vitals_current.get("blood_pressure", "120/80").split("/")[1]) + 10,
            "respiratory_rate": vitals_current.get("respiratory_rate", 16) - 6,
            "spo2": min(100, vitals_current.get("spo2", 98) + 5)
        }
        
        labs_current = patient["labs"]["current"]
        base_labs = {
            "lactate": max(0.8, labs_current.get("lactate", 1.0) - 2.0),
            "wbc": max(5, labs_current.get("wbc", 8.0) - 8.0),
            "creatinine": max(0.7, labs_current.get("creatinine", 1.0) - 0.8),
            "bilirubin": max(0.3, labs_current.get("bilirubin", 0.8) - 0.5)
        }
        
        # Generate history
        patient_copy["vitals_history"] = generate_120hr_vitals_history(base_vitals, trajectory)
        patient_copy["labs_history"] = generate_120hr_labs_history(base_labs, trajectory)
        
        patients_with_history.append(patient_copy)
    
    return patients_with_history
