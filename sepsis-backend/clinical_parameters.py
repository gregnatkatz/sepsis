"""
Comprehensive Clinical Parameters for Sepsis Detection System
Based on real-life sepsis pathophysiology and post-mortem findings

150+ parameters organized by clinical panels:
- Demographics & Context
- Vital Signs & Monitoring
- Complete Blood Count (CBC)
- Basic/Comprehensive Metabolic Panel
- Coagulation & Hemostasis
- Arterial Blood Gas (ABG)
- Inflammatory Markers
- Cardiac Markers
- Renal Function & Urinalysis
- Sepsis & Severity Scores
- Microbiology
- Imaging Summary
- Interventions & Bundle Compliance
- Outcomes & Trajectory
"""

import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

# Patient Archetypes based on real clinical courses
ARCHETYPES = {
    "uncomplicated_sepsis": {
        "description": "Early sepsis, responds well to treatment, no shock",
        "peak_severity": 0.4,
        "recovery_rate": 0.15,
        "mortality": False,
        "icu_days": 2,
        "vasopressors": False,
        "ventilator": False
    },
    "septic_shock_survivor": {
        "description": "Septic shock requiring vasopressors, recovers with treatment",
        "peak_severity": 0.7,
        "recovery_rate": 0.08,
        "mortality": False,
        "icu_days": 5,
        "vasopressors": True,
        "ventilator": True
    },
    "refractory_shock_nonsurvivor": {
        "description": "Refractory septic shock, dies within 48-72h",
        "peak_severity": 0.95,
        "recovery_rate": -0.02,
        "mortality": True,
        "icu_days": 3,
        "vasopressors": True,
        "ventilator": True
    },
    "late_mods_nonsurvivor": {
        "description": "Initial response then late multi-organ failure",
        "peak_severity": 0.85,
        "recovery_rate": 0.03,
        "mortality": True,
        "icu_days": 7,
        "vasopressors": True,
        "ventilator": True
    }
}

# Organ dysfunction sequence (hours after shock onset)
ORGAN_DYSFUNCTION_DELAYS = {
    "cardiovascular": 0,
    "respiratory": 6,
    "renal": 18,
    "hepatic": 36,
    "coagulation": 24,
    "neurological": 12
}

# Clinical parameter definitions with normal ranges and sepsis ranges
CLINICAL_PARAMETERS = {
    # ==================== DEMOGRAPHICS & CONTEXT (8 params) ====================
    "demographics": {
        "age": {"unit": "years", "normal": (18, 65), "sepsis": (45, 85)},
        "sex": {"unit": "", "values": ["Male", "Female"]},
        "weight": {"unit": "kg", "normal": (60, 90), "sepsis": (50, 120)},
        "height": {"unit": "cm", "normal": (155, 185), "sepsis": (150, 195)},
        "bmi": {"unit": "kg/m2", "normal": (18.5, 25), "sepsis": (18, 40)},
        "admission_source": {"unit": "", "values": ["ED", "Floor", "OR", "Transfer", "Direct Admit"]},
        "location": {"unit": "", "values": ["ICU", "Stepdown", "Med-Surg", "ED"]},
        "infection_source": {"unit": "", "values": ["Pneumonia", "UTI", "Intra-abdominal", "Skin/Soft Tissue", "Line-associated", "Unknown"]}
    },
    
    # ==================== VITAL SIGNS & MONITORING (15 params) ====================
    "vitals": {
        "heart_rate": {"unit": "bpm", "normal": (60, 100), "early_sepsis": (100, 120), "shock": (120, 150), "cold_shock": (80, 140)},
        "systolic_bp": {"unit": "mmHg", "normal": (100, 140), "early_sepsis": (90, 110), "shock": (70, 90), "cold_shock": (60, 80)},
        "diastolic_bp": {"unit": "mmHg", "normal": (60, 90), "early_sepsis": (50, 70), "shock": (40, 60), "cold_shock": (35, 50)},
        "map": {"unit": "mmHg", "normal": (70, 105), "early_sepsis": (65, 80), "shock": (50, 65), "cold_shock": (40, 55)},
        "respiratory_rate": {"unit": "breaths/min", "normal": (12, 20), "early_sepsis": (20, 28), "shock": (28, 40), "cold_shock": (30, 45)},
        "temperature": {"unit": "°C", "normal": (36.5, 37.5), "early_sepsis": (38.0, 39.5), "shock": (35.5, 40.5), "cold_shock": (35.0, 36.5)},
        "spo2": {"unit": "%", "normal": (95, 100), "early_sepsis": (90, 96), "shock": (85, 92), "cold_shock": (80, 88)},
        "fio2": {"unit": "%", "normal": (21, 21), "early_sepsis": (21, 40), "shock": (40, 80), "cold_shock": (80, 100)},
        "pf_ratio": {"unit": "", "normal": (400, 500), "early_sepsis": (250, 400), "shock": (100, 250), "cold_shock": (50, 100)},
        "urine_output": {"unit": "mL/hr", "normal": (50, 100), "early_sepsis": (30, 50), "shock": (10, 30), "cold_shock": (0, 10)},
        "gcs": {"unit": "", "normal": (15, 15), "early_sepsis": (13, 15), "shock": (10, 13), "cold_shock": (3, 10)},
        "pain_score": {"unit": "0-10", "normal": (0, 2), "early_sepsis": (3, 6), "shock": (2, 8), "cold_shock": (0, 3)},
        "capillary_refill": {"unit": "sec", "normal": (1, 2), "early_sepsis": (2, 3), "shock": (3, 5), "cold_shock": (5, 8)},
        "skin_temp": {"unit": "", "values": ["Warm", "Cool", "Cold", "Mottled"]},
        "bedside_glucose": {"unit": "mg/dL", "normal": (70, 110), "early_sepsis": (110, 180), "shock": (150, 300), "cold_shock": (40, 250)}
    },
    
    # ==================== COMPLETE BLOOD COUNT (18 params) ====================
    "cbc": {
        "wbc": {"unit": "x10^9/L", "normal": (4, 11), "early_sepsis": (12, 20), "shock": (20, 35), "cold_shock": (1, 4)},
        "neutrophils_abs": {"unit": "x10^9/L", "normal": (2, 7), "early_sepsis": (8, 15), "shock": (15, 30), "cold_shock": (0.5, 2)},
        "neutrophils_pct": {"unit": "%", "normal": (40, 70), "early_sepsis": (75, 85), "shock": (85, 95), "cold_shock": (30, 60)},
        "bands_pct": {"unit": "%", "normal": (0, 5), "early_sepsis": (5, 15), "shock": (15, 30), "cold_shock": (20, 40)},
        "lymphocytes_abs": {"unit": "x10^9/L", "normal": (1, 4), "early_sepsis": (0.8, 1.5), "shock": (0.3, 0.8), "cold_shock": (0.1, 0.5)},
        "lymphocytes_pct": {"unit": "%", "normal": (20, 40), "early_sepsis": (10, 20), "shock": (5, 10), "cold_shock": (2, 8)},
        "monocytes_pct": {"unit": "%", "normal": (2, 8), "early_sepsis": (5, 12), "shock": (8, 15), "cold_shock": (3, 10)},
        "eosinophils_pct": {"unit": "%", "normal": (1, 4), "early_sepsis": (0, 1), "shock": (0, 0.5), "cold_shock": (0, 0.2)},
        "basophils_pct": {"unit": "%", "normal": (0, 1), "early_sepsis": (0, 0.5), "shock": (0, 0.3), "cold_shock": (0, 0.2)},
        "rbc": {"unit": "x10^12/L", "normal": (4.2, 5.5), "early_sepsis": (3.5, 4.5), "shock": (3.0, 4.0), "cold_shock": (2.5, 3.5)},
        "hemoglobin": {"unit": "g/dL", "normal": (12, 16), "early_sepsis": (10, 13), "shock": (8, 11), "cold_shock": (6, 9)},
        "hematocrit": {"unit": "%", "normal": (36, 48), "early_sepsis": (30, 40), "shock": (25, 35), "cold_shock": (20, 30)},
        "mcv": {"unit": "fL", "normal": (80, 100), "early_sepsis": (80, 100), "shock": (80, 105), "cold_shock": (75, 110)},
        "mch": {"unit": "pg", "normal": (27, 33), "early_sepsis": (27, 33), "shock": (26, 34), "cold_shock": (25, 35)},
        "mchc": {"unit": "g/dL", "normal": (32, 36), "early_sepsis": (32, 36), "shock": (31, 37), "cold_shock": (30, 38)},
        "rdw": {"unit": "%", "normal": (11.5, 14.5), "early_sepsis": (14, 17), "shock": (16, 20), "cold_shock": (18, 25)},
        "platelets": {"unit": "x10^9/L", "normal": (150, 400), "early_sepsis": (100, 200), "shock": (50, 100), "cold_shock": (10, 50)},
        "mpv": {"unit": "fL", "normal": (7.5, 11.5), "early_sepsis": (10, 13), "shock": (11, 14), "cold_shock": (12, 16)}
    },
    
    # ==================== METABOLIC PANEL (24 params) ====================
    "metabolic": {
        "sodium": {"unit": "mmol/L", "normal": (136, 145), "early_sepsis": (132, 148), "shock": (128, 155), "cold_shock": (125, 160)},
        "potassium": {"unit": "mmol/L", "normal": (3.5, 5.0), "early_sepsis": (3.2, 5.5), "shock": (3.0, 6.5), "cold_shock": (2.5, 7.5)},
        "chloride": {"unit": "mmol/L", "normal": (98, 106), "early_sepsis": (95, 112), "shock": (90, 120), "cold_shock": (85, 125)},
        "bicarbonate": {"unit": "mmol/L", "normal": (22, 29), "early_sepsis": (18, 24), "shock": (12, 18), "cold_shock": (6, 14)},
        "bun": {"unit": "mg/dL", "normal": (7, 20), "early_sepsis": (20, 40), "shock": (40, 80), "cold_shock": (60, 120)},
        "creatinine": {"unit": "mg/dL", "normal": (0.6, 1.2), "early_sepsis": (1.2, 2.0), "shock": (2.0, 4.0), "cold_shock": (4.0, 8.0)},
        "glucose": {"unit": "mg/dL", "normal": (70, 100), "early_sepsis": (120, 200), "shock": (180, 350), "cold_shock": (40, 400)},
        "calcium_total": {"unit": "mg/dL", "normal": (8.5, 10.5), "early_sepsis": (7.5, 9.5), "shock": (6.5, 8.5), "cold_shock": (5.5, 7.5)},
        "calcium_ionized": {"unit": "mmol/L", "normal": (1.12, 1.32), "early_sepsis": (1.0, 1.2), "shock": (0.85, 1.1), "cold_shock": (0.7, 0.95)},
        "magnesium": {"unit": "mg/dL", "normal": (1.7, 2.2), "early_sepsis": (1.4, 2.5), "shock": (1.2, 3.0), "cold_shock": (1.0, 3.5)},
        "phosphate": {"unit": "mg/dL", "normal": (2.5, 4.5), "early_sepsis": (2.0, 5.5), "shock": (1.5, 7.0), "cold_shock": (1.0, 9.0)},
        "anion_gap": {"unit": "mEq/L", "normal": (8, 12), "early_sepsis": (12, 18), "shock": (18, 28), "cold_shock": (25, 40)},
        "egfr": {"unit": "mL/min/1.73m2", "normal": (90, 120), "early_sepsis": (60, 90), "shock": (30, 60), "cold_shock": (5, 30)},
        "albumin": {"unit": "g/dL", "normal": (3.5, 5.0), "early_sepsis": (2.5, 3.5), "shock": (1.8, 2.8), "cold_shock": (1.2, 2.2)},
        "total_protein": {"unit": "g/dL", "normal": (6.0, 8.3), "early_sepsis": (5.0, 7.0), "shock": (4.0, 6.0), "cold_shock": (3.0, 5.0)},
        "ast": {"unit": "U/L", "normal": (10, 40), "early_sepsis": (40, 100), "shock": (100, 500), "cold_shock": (500, 5000)},
        "alt": {"unit": "U/L", "normal": (7, 56), "early_sepsis": (50, 150), "shock": (150, 800), "cold_shock": (800, 5000)},
        "alp": {"unit": "U/L", "normal": (44, 147), "early_sepsis": (100, 250), "shock": (200, 500), "cold_shock": (300, 800)},
        "ggt": {"unit": "U/L", "normal": (9, 48), "early_sepsis": (50, 150), "shock": (150, 400), "cold_shock": (300, 800)},
        "bilirubin_total": {"unit": "mg/dL", "normal": (0.1, 1.2), "early_sepsis": (1.2, 3.0), "shock": (3.0, 8.0), "cold_shock": (8.0, 20.0)},
        "bilirubin_direct": {"unit": "mg/dL", "normal": (0, 0.3), "early_sepsis": (0.3, 1.5), "shock": (1.5, 5.0), "cold_shock": (5.0, 15.0)},
        "ldh": {"unit": "U/L", "normal": (140, 280), "early_sepsis": (280, 500), "shock": (500, 1500), "cold_shock": (1500, 5000)},
        "uric_acid": {"unit": "mg/dL", "normal": (3.5, 7.2), "early_sepsis": (6, 10), "shock": (8, 15), "cold_shock": (10, 20)},
        "ammonia": {"unit": "µmol/L", "normal": (15, 45), "early_sepsis": (40, 80), "shock": (80, 150), "cold_shock": (150, 300)}
    },
    
    # ==================== COAGULATION & HEMOSTASIS (10 params) ====================
    "coagulation": {
        "pt": {"unit": "sec", "normal": (11, 13.5), "early_sepsis": (13, 16), "shock": (16, 25), "cold_shock": (25, 50)},
        "inr": {"unit": "", "normal": (0.9, 1.1), "early_sepsis": (1.1, 1.5), "shock": (1.5, 2.5), "cold_shock": (2.5, 6.0)},
        "aptt": {"unit": "sec", "normal": (25, 35), "early_sepsis": (35, 50), "shock": (50, 80), "cold_shock": (80, 150)},
        "fibrinogen": {"unit": "mg/dL", "normal": (200, 400), "early_sepsis": (400, 600), "shock": (150, 400), "cold_shock": (50, 150)},
        "d_dimer": {"unit": "µg/mL FEU", "normal": (0, 0.5), "early_sepsis": (0.5, 2.0), "shock": (2.0, 10.0), "cold_shock": (10.0, 50.0)},
        "antithrombin_iii": {"unit": "%", "normal": (80, 120), "early_sepsis": (60, 90), "shock": (40, 70), "cold_shock": (20, 50)},
        "protein_c": {"unit": "%", "normal": (70, 140), "early_sepsis": (50, 80), "shock": (30, 60), "cold_shock": (10, 40)},
        "protein_s": {"unit": "%", "normal": (60, 140), "early_sepsis": (40, 70), "shock": (25, 50), "cold_shock": (10, 35)},
        "thrombin_time": {"unit": "sec", "normal": (14, 19), "early_sepsis": (18, 25), "shock": (25, 40), "cold_shock": (40, 80)},
        "dic_score": {"unit": "", "normal": (0, 0), "early_sepsis": (0, 2), "shock": (3, 5), "cold_shock": (5, 8)}
    },
    
    # ==================== ARTERIAL BLOOD GAS (12 params) ====================
    "abg": {
        "ph": {"unit": "", "normal": (7.35, 7.45), "early_sepsis": (7.30, 7.40), "shock": (7.20, 7.32), "cold_shock": (6.90, 7.20)},
        "paco2": {"unit": "mmHg", "normal": (35, 45), "early_sepsis": (28, 38), "shock": (25, 35), "cold_shock": (20, 50)},
        "pao2": {"unit": "mmHg", "normal": (80, 100), "early_sepsis": (60, 85), "shock": (50, 70), "cold_shock": (40, 60)},
        "hco3_abg": {"unit": "mmol/L", "normal": (22, 26), "early_sepsis": (18, 23), "shock": (12, 18), "cold_shock": (6, 14)},
        "base_excess": {"unit": "mEq/L", "normal": (-2, 2), "early_sepsis": (-6, -2), "shock": (-15, -6), "cold_shock": (-25, -12)},
        "sao2": {"unit": "%", "normal": (95, 100), "early_sepsis": (90, 96), "shock": (85, 92), "cold_shock": (70, 88)},
        "lactate_abg": {"unit": "mmol/L", "normal": (0.5, 1.5), "early_sepsis": (2.0, 4.0), "shock": (4.0, 8.0), "cold_shock": (8.0, 20.0)},
        "carboxyhemoglobin": {"unit": "%", "normal": (0, 3), "early_sepsis": (0, 5), "shock": (0, 8), "cold_shock": (0, 10)},
        "methemoglobin": {"unit": "%", "normal": (0, 1.5), "early_sepsis": (0, 2), "shock": (0, 3), "cold_shock": (0, 5)},
        "a_a_gradient": {"unit": "mmHg", "normal": (5, 15), "early_sepsis": (15, 30), "shock": (30, 60), "cold_shock": (50, 100)},
        "oxygen_content": {"unit": "mL/dL", "normal": (18, 21), "early_sepsis": (14, 18), "shock": (10, 15), "cold_shock": (6, 12)},
        "co2_content": {"unit": "mmol/L", "normal": (23, 29), "early_sepsis": (19, 25), "shock": (14, 20), "cold_shock": (8, 16)}
    },
    
    # ==================== INFLAMMATORY MARKERS (12 params) ====================
    "inflammatory": {
        "crp": {"unit": "mg/L", "normal": (0, 10), "early_sepsis": (50, 150), "shock": (150, 350), "cold_shock": (300, 500)},
        "procalcitonin": {"unit": "ng/mL", "normal": (0, 0.1), "early_sepsis": (0.5, 5.0), "shock": (5.0, 50.0), "cold_shock": (50.0, 200.0)},
        "esr": {"unit": "mm/hr", "normal": (0, 20), "early_sepsis": (30, 60), "shock": (60, 100), "cold_shock": (80, 120)},
        "ferritin": {"unit": "ng/mL", "normal": (20, 200), "early_sepsis": (300, 800), "shock": (800, 3000), "cold_shock": (3000, 10000)},
        "il_6": {"unit": "pg/mL", "normal": (0, 7), "early_sepsis": (50, 500), "shock": (500, 5000), "cold_shock": (5000, 50000)},
        "tnf_alpha": {"unit": "pg/mL", "normal": (0, 8), "early_sepsis": (20, 100), "shock": (100, 500), "cold_shock": (500, 2000)},
        "il_1_beta": {"unit": "pg/mL", "normal": (0, 5), "early_sepsis": (10, 50), "shock": (50, 200), "cold_shock": (200, 1000)},
        "il_10": {"unit": "pg/mL", "normal": (0, 5), "early_sepsis": (20, 100), "shock": (100, 500), "cold_shock": (500, 2000)},
        "presepsin": {"unit": "pg/mL", "normal": (0, 300), "early_sepsis": (500, 1000), "shock": (1000, 3000), "cold_shock": (3000, 10000)},
        "supar": {"unit": "ng/mL", "normal": (1.5, 4.0), "early_sepsis": (5, 10), "shock": (10, 20), "cold_shock": (20, 40)},
        "haptoglobin": {"unit": "mg/dL", "normal": (30, 200), "early_sepsis": (100, 300), "shock": (50, 200), "cold_shock": (10, 100)},
        "complement_c3": {"unit": "mg/dL", "normal": (90, 180), "early_sepsis": (60, 100), "shock": (40, 70), "cold_shock": (20, 50)}
    },
    
    # ==================== CARDIAC MARKERS (12 params) ====================
    "cardiac": {
        "troponin_i": {"unit": "ng/L", "normal": (0, 14), "early_sepsis": (20, 100), "shock": (100, 1000), "cold_shock": (1000, 10000)},
        "troponin_t": {"unit": "ng/L", "normal": (0, 14), "early_sepsis": (15, 80), "shock": (80, 500), "cold_shock": (500, 5000)},
        "ck_mb": {"unit": "ng/mL", "normal": (0, 5), "early_sepsis": (5, 20), "shock": (20, 100), "cold_shock": (100, 500)},
        "bnp": {"unit": "pg/mL", "normal": (0, 100), "early_sepsis": (200, 500), "shock": (500, 2000), "cold_shock": (2000, 10000)},
        "nt_probnp": {"unit": "pg/mL", "normal": (0, 300), "early_sepsis": (500, 2000), "shock": (2000, 10000), "cold_shock": (10000, 50000)},
        "ejection_fraction": {"unit": "%", "normal": (55, 70), "early_sepsis": (45, 60), "shock": (30, 50), "cold_shock": (15, 35)},
        "cardiac_output": {"unit": "L/min", "normal": (4, 8), "early_sepsis": (6, 12), "shock": (3, 8), "cold_shock": (2, 4)},
        "svr": {"unit": "dynes·s/cm5", "normal": (800, 1200), "early_sepsis": (400, 800), "shock": (300, 600), "cold_shock": (600, 1500)},
        "cvp": {"unit": "mmHg", "normal": (2, 8), "early_sepsis": (4, 12), "shock": (8, 18), "cold_shock": (12, 25)},
        "scvo2": {"unit": "%", "normal": (65, 75), "early_sepsis": (70, 85), "shock": (50, 70), "cold_shock": (30, 55)},
        "heart_rhythm": {"unit": "", "values": ["NSR", "Sinus Tachycardia", "AFib", "AFib RVR", "VT", "Bradycardia"]},
        "arrhythmia_burden": {"unit": "%", "normal": (0, 1), "early_sepsis": (1, 10), "shock": (10, 40), "cold_shock": (30, 80)}
    },
    
    # ==================== RENAL & URINALYSIS (12 params) ====================
    "renal": {
        "urine_sodium": {"unit": "mEq/L", "normal": (40, 220), "early_sepsis": (20, 40), "shock": (10, 30), "cold_shock": (5, 20)},
        "urine_creatinine": {"unit": "mg/dL", "normal": (20, 275), "early_sepsis": (30, 150), "shock": (20, 80), "cold_shock": (10, 50)},
        "fena": {"unit": "%", "normal": (0.5, 1.0), "early_sepsis": (0.5, 2.0), "shock": (2.0, 5.0), "cold_shock": (3.0, 10.0)},
        "urine_leukocyte_esterase": {"unit": "", "values": ["Negative", "Trace", "1+", "2+", "3+"]},
        "urine_nitrites": {"unit": "", "values": ["Negative", "Positive"]},
        "urine_wbc": {"unit": "/hpf", "normal": (0, 5), "early_sepsis": (5, 20), "shock": (20, 100), "cold_shock": (50, 200)},
        "urine_rbc": {"unit": "/hpf", "normal": (0, 3), "early_sepsis": (3, 15), "shock": (15, 50), "cold_shock": (30, 100)},
        "urine_protein": {"unit": "", "values": ["Negative", "Trace", "1+", "2+", "3+", "4+"]},
        "urine_specific_gravity": {"unit": "", "normal": (1.005, 1.030), "early_sepsis": (1.015, 1.035), "shock": (1.020, 1.040), "cold_shock": (1.010, 1.025)},
        "urine_ph": {"unit": "", "normal": (5.0, 8.0), "early_sepsis": (5.0, 7.0), "shock": (5.0, 6.5), "cold_shock": (5.0, 6.0)},
        "urine_casts": {"unit": "", "values": ["None", "Hyaline", "Granular", "Muddy Brown", "WBC Casts", "RBC Casts"]},
        "aki_stage": {"unit": "", "values": ["None", "Stage 1", "Stage 2", "Stage 3"]}
    },
    
    # ==================== SEPSIS & SEVERITY SCORES (10 params) ====================
    "scores": {
        "sirs_count": {"unit": "/4", "normal": (0, 1), "early_sepsis": (2, 3), "shock": (3, 4), "cold_shock": (4, 4)},
        "qsofa": {"unit": "/3", "normal": (0, 0), "early_sepsis": (1, 2), "shock": (2, 3), "cold_shock": (3, 3)},
        "sofa_total": {"unit": "/24", "normal": (0, 1), "early_sepsis": (2, 6), "shock": (7, 14), "cold_shock": (15, 24)},
        "sofa_respiratory": {"unit": "/4", "normal": (0, 0), "early_sepsis": (1, 2), "shock": (2, 3), "cold_shock": (3, 4)},
        "sofa_coagulation": {"unit": "/4", "normal": (0, 0), "early_sepsis": (0, 1), "shock": (1, 3), "cold_shock": (3, 4)},
        "sofa_liver": {"unit": "/4", "normal": (0, 0), "early_sepsis": (0, 1), "shock": (1, 3), "cold_shock": (3, 4)},
        "sofa_cardiovascular": {"unit": "/4", "normal": (0, 0), "early_sepsis": (1, 2), "shock": (3, 4), "cold_shock": (4, 4)},
        "sofa_cns": {"unit": "/4", "normal": (0, 0), "early_sepsis": (0, 1), "shock": (1, 3), "cold_shock": (3, 4)},
        "sofa_renal": {"unit": "/4", "normal": (0, 0), "early_sepsis": (0, 1), "shock": (1, 3), "cold_shock": (3, 4)},
        "news2": {"unit": "/20", "normal": (0, 4), "early_sepsis": (5, 8), "shock": (9, 14), "cold_shock": (15, 20)}
    },
    
    # ==================== MICROBIOLOGY (15 params) ====================
    "microbiology": {
        "blood_culture_sent": {"unit": "", "values": ["Yes", "No"]},
        "blood_culture_positive": {"unit": "", "values": ["Yes", "No", "Pending"]},
        "time_to_blood_culture": {"unit": "min", "normal": (0, 60), "early_sepsis": (0, 120), "shock": (0, 180), "cold_shock": (0, 240)},
        "organism_1": {"unit": "", "values": ["E. coli", "Klebsiella", "Pseudomonas", "Staph aureus", "MRSA", "Strep pneumo", "Enterococcus", "Candida", "None identified"]},
        "organism_susceptibility": {"unit": "", "values": ["Susceptible", "MDR", "ESBL", "CRE", "MRSA", "VRE", "Unknown"]},
        "positive_bottles": {"unit": "", "normal": (0, 0), "early_sepsis": (1, 2), "shock": (2, 4), "cold_shock": (3, 6)},
        "urine_culture_sent": {"unit": "", "values": ["Yes", "No"]},
        "urine_culture_positive": {"unit": "", "values": ["Yes", "No", "Pending"]},
        "urine_organism": {"unit": "", "values": ["E. coli", "Klebsiella", "Proteus", "Enterococcus", "Pseudomonas", "Candida", "None"]},
        "respiratory_culture_sent": {"unit": "", "values": ["Yes", "No"]},
        "respiratory_culture_positive": {"unit": "", "values": ["Yes", "No", "Pending"]},
        "wound_culture_sent": {"unit": "", "values": ["Yes", "No", "N/A"]},
        "source_control_performed": {"unit": "", "values": ["Yes", "No", "N/A", "Pending"]},
        "days_since_positive_culture": {"unit": "days", "normal": (0, 0), "early_sepsis": (0, 2), "shock": (0, 3), "cold_shock": (0, 5)},
        "pcr_panel_positive": {"unit": "", "values": ["Yes", "No", "Not done"]}
    },
    
    # ==================== IMAGING SUMMARY (10 params) ====================
    "imaging": {
        "cxr_performed": {"unit": "", "values": ["Yes", "No"]},
        "cxr_infiltrate": {"unit": "", "values": ["None", "Unilateral", "Bilateral", "Diffuse"]},
        "cxr_effusion": {"unit": "", "values": ["None", "Small", "Moderate", "Large"]},
        "ct_abdomen_free_air": {"unit": "", "values": ["Yes", "No", "Not done"]},
        "ct_abdomen_abscess": {"unit": "", "values": ["Yes", "No", "Not done"]},
        "us_gallbladder": {"unit": "", "values": ["Normal", "Wall thickening", "Stones", "Cholecystitis", "Not done"]},
        "us_biliary_dilation": {"unit": "", "values": ["Yes", "No", "Not done"]},
        "imaging_studies_24h": {"unit": "", "normal": (0, 1), "early_sepsis": (1, 3), "shock": (2, 5), "cold_shock": (3, 8)},
        "hours_since_imaging": {"unit": "hrs", "normal": (0, 24), "early_sepsis": (0, 12), "shock": (0, 6), "cold_shock": (0, 4)},
        "imaging_severity": {"unit": "0-3", "normal": (0, 0), "early_sepsis": (1, 1), "shock": (2, 2), "cold_shock": (3, 3)}
    },
    
    # ==================== INTERVENTIONS & BUNDLE (20 params) ====================
    "interventions": {
        "time_to_antibiotics": {"unit": "min", "normal": (0, 60), "early_sepsis": (0, 120), "shock": (0, 180), "cold_shock": (0, 360)},
        "antibiotic_count": {"unit": "", "normal": (0, 1), "early_sepsis": (1, 2), "shock": (2, 4), "cold_shock": (3, 5)},
        "antibiotic_1_class": {"unit": "", "values": ["Beta-lactam", "Carbapenem", "Fluoroquinolone", "Vancomycin", "Aminoglycoside", "Antifungal"]},
        "antibiotic_2_class": {"unit": "", "values": ["None", "Beta-lactam", "Carbapenem", "Fluoroquinolone", "Vancomycin", "Aminoglycoside", "Antifungal"]},
        "fluid_bolus_3h": {"unit": "mL", "normal": (0, 500), "early_sepsis": (1000, 2000), "shock": (2000, 4000), "cold_shock": (3000, 6000)},
        "fluid_volume_6h": {"unit": "mL", "normal": (0, 1000), "early_sepsis": (2000, 4000), "shock": (4000, 8000), "cold_shock": (6000, 12000)},
        "vasopressor_started": {"unit": "", "values": ["Yes", "No"]},
        "vasopressor_type": {"unit": "", "values": ["None", "Norepinephrine", "Vasopressin", "Epinephrine", "Dopamine", "Phenylephrine"]},
        "vasopressor_max_dose": {"unit": "µg/kg/min", "normal": (0, 0), "early_sepsis": (0, 0.1), "shock": (0.1, 0.5), "cold_shock": (0.5, 2.0)},
        "mechanical_ventilation": {"unit": "", "values": ["Yes", "No"]},
        "vent_mode": {"unit": "", "values": ["None", "SIMV", "AC/VC", "AC/PC", "PSV", "APRV", "HFOV"]},
        "peep": {"unit": "cmH2O", "normal": (0, 5), "early_sepsis": (5, 10), "shock": (10, 16), "cold_shock": (14, 24)},
        "tidal_volume_per_kg": {"unit": "mL/kg", "normal": (6, 8), "early_sepsis": (6, 8), "shock": (6, 8), "cold_shock": (4, 6)},
        "dialysis_crrt": {"unit": "", "values": ["None", "IHD", "CRRT", "SLED"]},
        "central_line": {"unit": "", "values": ["Yes", "No"]},
        "arterial_line": {"unit": "", "values": ["Yes", "No"]},
        "steroids_started": {"unit": "", "values": ["Yes", "No"]},
        "stress_ulcer_prophylaxis": {"unit": "", "values": ["Yes", "No"]},
        "dvt_prophylaxis": {"unit": "", "values": ["Yes", "No"]},
        "code_status": {"unit": "", "values": ["Full Code", "DNR", "DNR/DNI", "Comfort Care"]}
    },
    
    # ==================== OUTCOMES & TRAJECTORY (10 params) ====================
    "outcomes": {
        "survived_discharge": {"unit": "", "values": ["Yes", "No", "Pending"]},
        "icu_los": {"unit": "days", "normal": (0, 1), "early_sepsis": (2, 5), "shock": (5, 14), "cold_shock": (3, 7)},
        "hospital_los": {"unit": "days", "normal": (1, 3), "early_sepsis": (5, 10), "shock": (10, 30), "cold_shock": (3, 10)},
        "time_to_hemodynamic_stability": {"unit": "hrs", "normal": (0, 6), "early_sepsis": (6, 24), "shock": (24, 72), "cold_shock": (72, 168)},
        "time_to_lactate_normalization": {"unit": "hrs", "normal": (0, 6), "early_sepsis": (6, 24), "shock": (24, 72), "cold_shock": (72, 168)},
        "max_sofa_score": {"unit": "", "normal": (0, 2), "early_sepsis": (3, 8), "shock": (9, 16), "cold_shock": (17, 24)},
        "sepsis_recurrence": {"unit": "", "values": ["Yes", "No"]},
        "readmission_30d": {"unit": "", "values": ["Yes", "No", "N/A"]},
        "bundle_compliance_pct": {"unit": "%", "normal": (80, 100), "early_sepsis": (60, 90), "shock": (40, 80), "cold_shock": (20, 60)},
        "early_warning_leadtime": {"unit": "hrs", "normal": (0, 0), "early_sepsis": (2, 8), "shock": (4, 12), "cold_shock": (1, 6)}
    }
}


def get_severity_phase(severity: float) -> str:
    """Determine clinical phase based on severity score (0-1)"""
    if severity < 0.3:
        return "normal"
    elif severity < 0.5:
        return "early_sepsis"
    elif severity < 0.75:
        return "shock"
    else:
        return "cold_shock"


def generate_severity_curve(archetype: str, hours: int = 120) -> List[float]:
    """
    Generate a severity curve over time based on patient archetype.
    Returns list of severity values (0-1) for each hour.
    
    Based on real clinical sepsis progression:
    - Pre-sepsis baseline: hours -120 to -24
    - Deterioration: hours -24 to 0
    - Treatment response: hours 0 to +96
    """
    arch = ARCHETYPES[archetype]
    peak_severity = arch["peak_severity"]
    recovery_rate = arch["recovery_rate"]
    mortality = arch["mortality"]
    
    curve = []
    
    for h in range(hours):
        # Normalize hour to -60 to +60 range (0 = presentation/peak)
        t = h - 60  # Center at hour 60
        
        if t < -24:
            # Pre-sepsis: gradual rise
            base = 0.1
            rise = (t + 60) / 36 * 0.2  # Gradual rise over 36 hours
            severity = base + rise
        elif t < 0:
            # Deterioration phase: rapid rise to peak
            progress = (t + 24) / 24  # 0 to 1 over 24 hours
            severity = 0.3 + progress * (peak_severity - 0.3)
        else:
            # Post-treatment phase
            if mortality and archetype == "refractory_shock_nonsurvivor":
                # Refractory: stays high then rises to death
                severity = peak_severity + (t / 48) * 0.1
                severity = min(1.0, severity)
            elif mortality and archetype == "late_mods_nonsurvivor":
                # Late MODS: initial improvement then second hit
                if t < 24:
                    severity = peak_severity - (t / 24) * 0.15  # Slight improvement
                elif t < 48:
                    severity = peak_severity - 0.15 + ((t - 24) / 24) * 0.25  # Second hit
                else:
                    severity = peak_severity + 0.1  # Terminal
                severity = min(1.0, severity)
            else:
                # Survivor: gradual recovery
                decay = math.exp(-recovery_rate * t)
                severity = peak_severity * decay
                severity = max(0.1, severity)  # Don't go below baseline
        
        curve.append(max(0, min(1, severity)))
    
    return curve


def generate_organ_dysfunction_curves(severity_curve: List[float]) -> Dict[str, List[float]]:
    """
    Generate organ-specific dysfunction curves based on overall severity.
    Applies realistic delays for each organ system.
    """
    hours = len(severity_curve)
    organ_curves = {}
    
    for organ, delay in ORGAN_DYSFUNCTION_DELAYS.items():
        curve = []
        for h in range(hours):
            # Apply delay
            source_h = max(0, h - delay)
            base_severity = severity_curve[source_h]
            
            # Add organ-specific variation
            variation = random.gauss(0, 0.05)
            organ_severity = base_severity + variation
            
            # Clamp to valid range
            curve.append(max(0, min(1, organ_severity)))
        
        organ_curves[organ] = curve
    
    return organ_curves


def get_parameter_value(param_def: Dict, severity: float, phase: str = None) -> any:
    """Generate a realistic parameter value based on severity and phase"""
    if phase is None:
        phase = get_severity_phase(severity)
    
    # Handle categorical values
    if "values" in param_def:
        values = param_def["values"]
        if phase == "normal":
            return values[0]  # Usually the normal/negative value
        elif phase == "early_sepsis":
            idx = min(1, len(values) - 1)
            return values[idx]
        elif phase == "shock":
            idx = min(2, len(values) - 1)
            return values[idx]
        else:  # cold_shock
            idx = min(len(values) - 1, 3)
            return values[idx]
    
    # Handle numeric values
    if phase in param_def:
        range_tuple = param_def[phase]
    elif "normal" in param_def:
        range_tuple = param_def["normal"]
    else:
        return None
    
    low, high = range_tuple
    
    # Interpolate within range based on severity within phase
    phase_severity = severity
    if phase == "normal":
        phase_severity = severity / 0.3
    elif phase == "early_sepsis":
        phase_severity = (severity - 0.3) / 0.2
    elif phase == "shock":
        phase_severity = (severity - 0.5) / 0.25
    else:
        phase_severity = (severity - 0.75) / 0.25
    
    phase_severity = max(0, min(1, phase_severity))
    
    # Generate value with some noise
    base_value = low + (high - low) * phase_severity
    noise = random.gauss(0, (high - low) * 0.1)
    value = base_value + noise
    
    # Clamp to reasonable bounds
    value = max(low * 0.8, min(high * 1.2, value))
    
    # Round appropriately
    if abs(value) >= 100:
        return round(value, 0)
    elif abs(value) >= 10:
        return round(value, 1)
    else:
        return round(value, 2)


def generate_patient_clinical_data(
    patient_id: str,
    archetype: str = "septic_shock_survivor",
    hours: int = 120,
    interval_hours: int = 4
) -> Dict:
    """
    Generate comprehensive clinical data for a patient over 120 hours.
    
    Args:
        patient_id: Patient identifier
        archetype: One of the ARCHETYPES keys
        hours: Total hours of data to generate
        interval_hours: Hours between data points
    
    Returns:
        Dict with all clinical parameters organized by category and timepoint
    """
    # Generate severity and organ dysfunction curves
    severity_curve = generate_severity_curve(archetype, hours)
    organ_curves = generate_organ_dysfunction_curves(severity_curve)
    
    # Generate timepoints
    timepoints = list(range(0, hours, interval_hours))
    
    # Initialize result structure
    result = {
        "patient_id": patient_id,
        "archetype": archetype,
        "archetype_description": ARCHETYPES[archetype]["description"],
        "mortality": ARCHETYPES[archetype]["mortality"],
        "timepoints": [],
        "parameters_by_category": {},
        "parameter_count": 0
    }
    
    # Count total parameters
    param_count = 0
    for category, params in CLINICAL_PARAMETERS.items():
        param_count += len(params)
    result["parameter_count"] = param_count
    
    # Generate data for each timepoint
    for t in timepoints:
        severity = severity_curve[t]
        phase = get_severity_phase(severity)
        
        timepoint_data = {
            "hour": t - 60,  # Relative to presentation (hour 0)
            "timestamp": (datetime.now() - timedelta(hours=60-t)).isoformat(),
            "severity": round(severity, 3),
            "phase": phase,
            "parameters": {}
        }
        
        # Generate parameters for each category
        for category, params in CLINICAL_PARAMETERS.items():
            category_data = {}
            
            for param_name, param_def in params.items():
                # Use organ-specific severity for relevant parameters
                param_severity = severity
                if category in ["metabolic", "renal"] and "renal" in organ_curves:
                    param_severity = organ_curves["renal"][t]
                elif category in ["coagulation"] and "coagulation" in organ_curves:
                    param_severity = organ_curves["coagulation"][t]
                elif category in ["abg", "vitals"] and "respiratory" in organ_curves:
                    if param_name in ["pao2", "spo2", "pf_ratio", "fio2"]:
                        param_severity = organ_curves["respiratory"][t]
                elif category in ["cardiac"] and "cardiovascular" in organ_curves:
                    param_severity = organ_curves["cardiovascular"][t]
                
                value = get_parameter_value(param_def, param_severity, phase)
                unit = param_def.get("unit", "")
                
                category_data[param_name] = {
                    "value": value,
                    "unit": unit
                }
            
            timepoint_data["parameters"][category] = category_data
        
        result["timepoints"].append(timepoint_data)
    
    # Also organize by parameter for easy time-series access
    for category, params in CLINICAL_PARAMETERS.items():
        result["parameters_by_category"][category] = {}
        for param_name in params.keys():
            result["parameters_by_category"][category][param_name] = {
                "values": [],
                "unit": params[param_name].get("unit", "")
            }
            for tp in result["timepoints"]:
                result["parameters_by_category"][category][param_name]["values"].append(
                    tp["parameters"][category][param_name]["value"]
                )
    
    return result


def get_current_parameters(clinical_data: Dict) -> Dict:
    """Extract current (most recent) parameter values from clinical data"""
    if not clinical_data.get("timepoints"):
        return {}
    
    # Get the timepoint closest to hour 0 (presentation)
    current_tp = None
    min_diff = float('inf')
    for tp in clinical_data["timepoints"]:
        diff = abs(tp["hour"])
        if diff < min_diff:
            min_diff = diff
            current_tp = tp
    
    if not current_tp:
        current_tp = clinical_data["timepoints"][-1]
    
    return current_tp["parameters"]


def generate_lactate_clearance_curve(archetype: str, hours: int = 72) -> List[Dict]:
    """
    Generate lactate clearance curve based on archetype.
    Survivors show >10-20% clearance in first 6 hours.
    Non-survivors show flat or rising lactate.
    """
    arch = ARCHETYPES[archetype]
    mortality = arch["mortality"]
    
    curve = []
    
    if mortality:
        # Non-survivor: lactate stays high or rises
        initial = random.uniform(6, 10)
        for h in range(0, hours, 2):
            if h < 6:
                # Minimal clearance
                clearance = random.uniform(-5, 5)
            else:
                # Rising or flat
                clearance = random.uniform(-10, 2)
            
            value = initial * (1 - clearance/100)
            initial = value
            curve.append({
                "hour": h,
                "lactate": round(max(2, value), 1),
                "clearance_pct": round(clearance, 1)
            })
    else:
        # Survivor: good clearance
        initial = random.uniform(4, 8)
        for h in range(0, hours, 2):
            if h < 6:
                clearance = random.uniform(15, 30)
            elif h < 24:
                clearance = random.uniform(10, 20)
            else:
                clearance = random.uniform(5, 15)
            
            value = initial * (1 - clearance/100)
            initial = max(0.8, value)
            curve.append({
                "hour": h,
                "lactate": round(initial, 1),
                "clearance_pct": round(clearance, 1)
            })
    
    return curve


# Export parameter categories for frontend
def get_parameter_categories() -> List[Dict]:
    """Get list of parameter categories with counts for frontend display"""
    categories = []
    for category, params in CLINICAL_PARAMETERS.items():
        categories.append({
            "name": category,
            "display_name": category.replace("_", " ").title(),
            "parameter_count": len(params),
            "parameters": list(params.keys())
        })
    return categories


if __name__ == "__main__":
    # Test generation
    print("Testing clinical parameter generation...")
    
    # Generate data for each archetype
    for archetype in ARCHETYPES.keys():
        print(f"\n=== {archetype} ===")
        data = generate_patient_clinical_data(f"test-{archetype}", archetype)
        print(f"Total parameters: {data['parameter_count']}")
        print(f"Timepoints: {len(data['timepoints'])}")
        print(f"Mortality: {data['mortality']}")
        
        # Show current values for key parameters
        current = get_current_parameters(data)
        print(f"Current lactate: {current['abg']['lactate_abg']['value']} {current['abg']['lactate_abg']['unit']}")
        print(f"Current MAP: {current['vitals']['map']['value']} {current['vitals']['map']['unit']}")
        print(f"Current SOFA: {current['scores']['sofa_total']['value']}")
    
    # Show total parameter count
    total = sum(len(params) for params in CLINICAL_PARAMETERS.values())
    print(f"\n\nTotal unique parameters: {total}")
    
    # List categories
    print("\nParameter categories:")
    for cat in get_parameter_categories():
        print(f"  {cat['display_name']}: {cat['parameter_count']} parameters")
