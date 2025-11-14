
MOCK_PATIENTS = [
    {
        "admission_date": "2025-11-09",
        "age": 81,
        "devices": [
            {
                "days": 4,
                "type": "Foley catheter"
            },
            {
                "days": 4,
                "type": "IV line"
            }
        ],
        "diagnosis": "UTI with septic shock",
        "gender": "M",
        "id": "1",
        "labs": {
            "current": {
                "bilirubin": 1.8,
                "creatinine": 2.1,
                "lactate": 3.5,
                "wbc": 19.8
            },
            "previous": {
                "bilirubin": 1.2,
                "creatinine": 1.6,
                "lactate": 2.2,
                "wbc": 15.2
            }
        },
        "mrn": "MRN-789456",
        "name": "James Brown",
        "notes": [
            {
                "note": "Patient increasingly lethargic, difficult to arouse",
                "time": "07:00"
            },
            {
                "note": "Urine output decreased to 20ml/hr",
                "time": "05:30"
            }
        ],
        "risk_level": "CRITICAL",
        "risk_score": 92,
        "room": "3E-301",
        "sirs_criteria": 4,
        "vitals": {
            "current": {
                "blood_pressure": "88/55",
                "heart_rate": 118,
                "respiratory_rate": 26,
                "spo2": 91,
                "temperature": 39.1
            },
            "previous": {
                "blood_pressure": "102/68",
                "heart_rate": 92,
                "respiratory_rate": 18,
                "spo2": 94,
                "temperature": 38.2
            }
        },
        "ground_truth": {
            "sepsis_confirmed": true,
            "sepsis_onset_time": "2025-11-14T11:16:49.396830Z",
            "sepsis_source": "urinary_tract",
            "organ_dysfunction": {
                "hypotension": true,
                "altered_mental_status": true,
                "oliguria": true,
                "acute_kidney_injury": true
            },
            "qsofa_score": 3,
            "sofa_score": 8
        }
    },
    {
        "admission_date": "2025-11-10",
        "age": 69,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "Cholecystitis, post-ERCP",
        "gender": "M",
        "id": "2",
        "labs": {
            "current": {
                "bilirubin": 2.1,
                "creatinine": 1.2,
                "lactate": 1.8,
                "wbc": 12.5
            },
            "previous": {
                "bilirubin": 1.8,
                "creatinine": 1.1,
                "lactate": 1.5,
                "wbc": 11.2
            }
        },
        "mrn": "MRN-901234",
        "name": "Richard Moore",
        "notes": [
            {
                "note": "Tolerating clear liquids, pain controlled",
                "time": "06:30"
            },
            {
                "note": "ERCP completed yesterday, improving",
                "time": "04:45"
            }
        ],
        "risk_level": "MODERATE",
        "risk_score": 55,
        "room": "3E-320",
        "sirs_criteria": 2,
        "vitals": {
            "current": {
                "blood_pressure": "118/72",
                "heart_rate": 98,
                "respiratory_rate": 20,
                "spo2": 95,
                "temperature": 38.3
            },
            "previous": {
                "blood_pressure": "122/76",
                "heart_rate": 92,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.9
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {
                "hyperbilirubinemia": true
            },
            "qsofa_score": 0,
            "sofa_score": 4
        }
    },
    {
        "admission_date": "2025-11-10",
        "age": 68,
        "devices": [
            {
                "days": 3,
                "type": "IV line"
            }
        ],
        "diagnosis": "Post-op colectomy (Day 3), recovering",
        "gender": "M",
        "id": "3",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 1.1,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.8,
                "creatinine": 1.0,
                "lactate": 1.3,
                "wbc": 9.5
            }
        },
        "mrn": "MRN-456123",
        "name": "John Smith",
        "notes": [
            {
                "note": "Patient alert and oriented x3, pain well controlled",
                "time": "06:45"
            },
            {
                "note": "Tolerating regular diet, bowel sounds present",
                "time": "04:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 27,
        "room": "3E-312",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "118/75",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 97,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "120/78",
                "heart_rate": 88,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.5
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-11",
        "age": 77,
        "devices": [
            {
                "days": 3,
                "type": "IV line"
            }
        ],
        "diagnosis": "Severe CAP with pleural effusion",
        "gender": "M",
        "id": "4",
        "labs": {
            "current": {
                "bilirubin": 1.3,
                "creatinine": 1.8,
                "lactate": 3.2,
                "wbc": 20.5
            },
            "previous": {
                "bilirubin": 1.1,
                "creatinine": 1.5,
                "lactate": 2.6,
                "wbc": 17.8
            }
        },
        "mrn": "MRN-567890",
        "name": "Charles Harris",
        "notes": [
            {
                "note": "Increasing oxygen requirement, now on BiPAP",
                "time": "07:15"
            },
            {
                "note": "Chest X-ray shows worsening infiltrates",
                "time": "05:00"
            }
        ],
        "risk_level": "HIGH",
        "risk_score": 85,
        "room": "3E-316",
        "sirs_criteria": 4,
        "vitals": {
            "current": {
                "blood_pressure": "92/58",
                "heart_rate": 115,
                "respiratory_rate": 28,
                "spo2": 88,
                "temperature": 39.2
            },
            "previous": {
                "blood_pressure": "98/62",
                "heart_rate": 102,
                "respiratory_rate": 24,
                "spo2": 90,
                "temperature": 38.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": true,
            "sepsis_onset_time": "2025-11-14T15:16:49.396889Z",
            "sepsis_source": "pneumonia",
            "organ_dysfunction": {
                "hypoxemia": true
            },
            "qsofa_score": 2,
            "sofa_score": 6
        }
    },
    {
        "admission_date": "2025-11-11",
        "age": 73,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "UTI, on antibiotics",
        "gender": "F",
        "id": "5",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 1.4,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.8,
                "creatinine": 1.3,
                "lactate": 1.3,
                "wbc": 10.5
            }
        },
        "mrn": "MRN-345679",
        "name": "Margaret Foster",
        "notes": [
            {
                "note": "Alert and oriented x3, afebrile this morning",
                "time": "08:00"
            },
            {
                "note": "Urine culture shows E. coli, sensitive to ceftriaxone",
                "time": "06:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 19,
        "room": "3E-324",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "122/68",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "120/70",
                "heart_rate": 90,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.9
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 1
        }
    },
    {
        "admission_date": "2025-11-11",
        "age": 62,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "Diverticulitis, on antibiotics",
        "gender": "F",
        "id": "6",
        "labs": {
            "current": {
                "bilirubin": 0.8,
                "creatinine": 1.1,
                "lactate": 1.4,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 1.2,
                "wbc": 10.5
            }
        },
        "mrn": "MRN-012345",
        "name": "Elizabeth Garcia",
        "notes": [
            {
                "note": "Abdominal pain improving, tolerating liquids",
                "time": "07:45"
            },
            {
                "note": "CT shows uncomplicated diverticulitis, conservative management",
                "time": "05:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 23,
        "room": "3E-311",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "125/75",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 97,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "122/72",
                "heart_rate": 86,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 79,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Abdominal pain, under evaluation",
        "gender": "F",
        "id": "7",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 1.2,
                "lactate": 1.3,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.8,
                "creatinine": 1.1,
                "lactate": 1.1,
                "wbc": 9.8
            }
        },
        "mrn": "MRN-789013",
        "name": "Patricia Wilson",
        "notes": [
            {
                "note": "CT shows mild colitis, no abscess",
                "time": "08:15"
            },
            {
                "note": "Abdominal pain improving with conservative management",
                "time": "06:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 29,
        "room": "3E-328",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "128/72",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "125/70",
                "heart_rate": 88,
                "respiratory_rate": 18,
                "spo2": 97,
                "temperature": 37.6
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 1
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 55,
        "devices": [],
        "diagnosis": "Diabetic foot ulcer, improving",
        "gender": "M",
        "id": "8",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.3,
                "lactate": 1.1,
                "wbc": 9.2
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.2,
                "lactate": 1.0,
                "wbc": 8.8
            }
        },
        "mrn": "MRN-234567",
        "name": "Robert Williams",
        "notes": [
            {
                "note": "Wound healing well, granulation tissue present",
                "time": "07:30"
            },
            {
                "note": "Patient ambulating, pain controlled",
                "time": "05:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 22,
        "room": "3E-315",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "128/78",
                "heart_rate": 82,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.2
            },
            "previous": {
                "blood_pressure": "125/75",
                "heart_rate": 80,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.1
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 1
        }
    },
    {
        "admission_date": "2025-11-11",
        "age": 72,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            },
            {
                "days": 7,
                "type": "Foley catheter"
            }
        ],
        "diagnosis": "Community-acquired pneumonia",
        "gender": "F",
        "id": "9",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 1.1,
                "lactate": 2.1,
                "wbc": 16.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.5,
                "wbc": 12.3
            }
        },
        "mrn": "MRN-345678",
        "name": "Mary Johnson",
        "notes": [
            {
                "note": "Increased work of breathing noted",
                "time": "08:15"
            },
            {
                "note": "Patient reports feeling weak",
                "time": "06:00"
            }
        ],
        "risk_level": "MODERATE",
        "risk_score": 62,
        "room": "3E-308",
        "sirs_criteria": 3,
        "vitals": {
            "current": {
                "blood_pressure": "110/70",
                "heart_rate": 98,
                "respiratory_rate": 22,
                "spo2": 92,
                "temperature": 38.8
            },
            "previous": {
                "blood_pressure": "118/75",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 95,
                "temperature": 37.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": true,
            "sepsis_onset_time": "2025-11-14T17:16:49.396938Z",
            "sepsis_source": "pneumonia",
            "organ_dysfunction": {},
            "qsofa_score": 1,
            "sofa_score": 2
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 84,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "Aspiration pneumonia",
        "gender": "M",
        "id": "10",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 1.3,
                "lactate": 2.3,
                "wbc": 15.8
            },
            "previous": {
                "bilirubin": 0.8,
                "creatinine": 1.2,
                "lactate": 1.9,
                "wbc": 13.2
            }
        },
        "mrn": "MRN-901234",
        "name": "George Anderson",
        "notes": [
            {
                "note": "Increased oxygen requirement, now on 4L NC",
                "time": "08:45"
            },
            {
                "note": "Productive cough with thick secretions",
                "time": "06:15"
            }
        ],
        "risk_level": "MODERATE",
        "risk_score": 58,
        "room": "3E-310",
        "sirs_criteria": 3,
        "vitals": {
            "current": {
                "blood_pressure": "108/68",
                "heart_rate": 102,
                "respiratory_rate": 24,
                "spo2": 90,
                "temperature": 38.6
            },
            "previous": {
                "blood_pressure": "115/72",
                "heart_rate": 88,
                "respiratory_rate": 20,
                "spo2": 92,
                "temperature": 38.2
            }
        },
        "ground_truth": {
            "sepsis_confirmed": true,
            "sepsis_onset_time": "2025-11-14T17:16:49.396951Z",
            "sepsis_source": "pneumonia",
            "organ_dysfunction": {},
            "qsofa_score": 1,
            "sofa_score": 3
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 48,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            },
            {
                "days": 1,
                "type": "Wound VAC"
            }
        ],
        "diagnosis": "Necrotizing fasciitis, post-debridement",
        "gender": "M",
        "id": "11",
        "labs": {
            "current": {
                "bilirubin": 1.0,
                "creatinine": 1.4,
                "lactate": 2.4,
                "wbc": 16.2
            },
            "previous": {
                "bilirubin": 1.2,
                "creatinine": 1.6,
                "lactate": 2.9,
                "wbc": 18.5
            }
        },
        "mrn": "MRN-345678",
        "name": "David Rodriguez",
        "notes": [
            {
                "note": "Wound improving post-debridement, less erythema",
                "time": "08:30"
            },
            {
                "note": "Patient more alert, pain better controlled",
                "time": "06:00"
            }
        ],
        "risk_level": "MODERATE",
        "risk_score": 55,
        "room": "3E-314",
        "sirs_criteria": 3,
        "vitals": {
            "current": {
                "blood_pressure": "102/65",
                "heart_rate": 110,
                "respiratory_rate": 20,
                "spo2": 94,
                "temperature": 38.4
            },
            "previous": {
                "blood_pressure": "108/68",
                "heart_rate": 98,
                "respiratory_rate": 18,
                "spo2": 95,
                "temperature": 38.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": true,
            "sepsis_onset_time": "2025-11-14T17:16:49.396963Z",
            "sepsis_source": "unknown",
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 2
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 71,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "Post-op hip replacement, wound infection",
        "gender": "M",
        "id": "12",
        "labs": {
            "current": {
                "bilirubin": 0.8,
                "creatinine": 1.2,
                "lactate": 1.9,
                "wbc": 14.8
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.1,
                "lactate": 1.5,
                "wbc": 12.2
            }
        },
        "mrn": "MRN-789012",
        "name": "Thomas King",
        "notes": [
            {
                "note": "Surgical site with purulent drainage",
                "time": "09:00"
            },
            {
                "note": "Orthopedics consulted for possible washout",
                "time": "07:00"
            }
        ],
        "risk_level": "MODERATE",
        "risk_score": 52,
        "room": "3E-318",
        "sirs_criteria": 2,
        "vitals": {
            "current": {
                "blood_pressure": "112/70",
                "heart_rate": 96,
                "respiratory_rate": 20,
                "spo2": 95,
                "temperature": 38.5
            },
            "previous": {
                "blood_pressure": "118/74",
                "heart_rate": 88,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.9
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 2
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 66,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Soft tissue infection, left arm",
        "gender": "M",
        "id": "13",
        "labs": {
            "current": {
                "bilirubin": 0.8,
                "creatinine": 1.1,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 1.4,
                "wbc": 12.5
            }
        },
        "mrn": "MRN-901235",
        "name": "Andrew Miller",
        "notes": [
            {
                "note": "Erythema extending, marked for tracking",
                "time": "09:45"
            },
            {
                "note": "Patient reports pain 7/10",
                "time": "07:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 21,
        "room": "3E-330",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "122/78",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "126/80",
                "heart_rate": 86,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 64,
        "devices": [
            {
                "days": 2,
                "type": "IV line"
            }
        ],
        "diagnosis": "Acute pancreatitis",
        "gender": "F",
        "id": "14",
        "labs": {
            "current": {
                "bilirubin": 1.5,
                "creatinine": 1.3,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 1.2,
                "creatinine": 1.1,
                "lactate": 1.7,
                "wbc": 12.8
            }
        },
        "mrn": "MRN-123457",
        "name": "Angela Thompson",
        "notes": [
            {
                "note": "Abdominal pain 8/10, NPO",
                "time": "09:15"
            },
            {
                "note": "Lipase 1250, CT shows pancreatic edema",
                "time": "07:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 25,
        "room": "3E-322",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "108/66",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 95,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "115/72",
                "heart_rate": 92,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.6
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 3
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 58,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Cellulitis, right leg",
        "gender": "F",
        "id": "15",
        "labs": {
            "current": {
                "bilirubin": 0.8,
                "creatinine": 1.0,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.3,
                "wbc": 10.5
            }
        },
        "mrn": "MRN-456789",
        "name": "Linda Martinez",
        "notes": [
            {
                "note": "Erythema spreading, warm to touch",
                "time": "09:00"
            },
            {
                "note": "Patient reports pain 6/10",
                "time": "07:15"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 31,
        "room": "3E-305",
        "sirs_criteria": 1,
        "vitals": {
            "current": {
                "blood_pressure": "128/82",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "125/80",
                "heart_rate": 82,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.6
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 70,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Acute kidney injury",
        "gender": "F",
        "id": "16",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 2.8,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.9,
                "creatinine": 3.2,
                "lactate": 1.3,
                "wbc": 10.8
            }
        },
        "mrn": "MRN-234569",
        "name": "Helen Martinez",
        "notes": [
            {
                "note": "Creatinine trending down with hydration",
                "time": "09:30"
            },
            {
                "note": "Urine output 40ml/hr",
                "time": "07:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 33,
        "room": "3E-333",
        "sirs_criteria": 1,
        "vitals": {
            "current": {
                "blood_pressure": "112/68",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "118/72",
                "heart_rate": 86,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.4
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {
                "acute_kidney_injury": true
            },
            "qsofa_score": 0,
            "sofa_score": 2
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 58,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "COPD exacerbation",
        "gender": "F",
        "id": "17",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 1.5,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.3,
                "wbc": 11.2
            }
        },
        "mrn": "MRN-567891",
        "name": "Rachel Green",
        "notes": [
            {
                "note": "Wheezing improved with nebulizers",
                "time": "09:30"
            },
            {
                "note": "Patient on 3L NC, satting 91%",
                "time": "07:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 35,
        "room": "3E-326",
        "sirs_criteria": 1,
        "vitals": {
            "current": {
                "blood_pressure": "118/72",
                "heart_rate": 85,
                "respiratory_rate": 18,
                "spo2": 91,
                "temperature": 37.5
            },
            "previous": {
                "blood_pressure": "122/76",
                "heart_rate": 88,
                "respiratory_rate": 20,
                "spo2": 93,
                "temperature": 37.5
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 2
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 52,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Pyelonephritis, responding to treatment",
        "gender": "F",
        "id": "18",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.1,
                "lactate": 1.3,
                "wbc": 11.8
            },
            "previous": {
                "bilirubin": 0.8,
                "creatinine": 1.3,
                "lactate": 1.6,
                "wbc": 14.2
            }
        },
        "mrn": "MRN-234567",
        "name": "Jennifer Taylor",
        "notes": [
            {
                "note": "Flank pain improving, tolerating PO",
                "time": "09:45"
            },
            {
                "note": "Afebrile x12 hours",
                "time": "07:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 28,
        "room": "3E-313",
        "sirs_criteria": 1,
        "vitals": {
            "current": {
                "blood_pressure": "118/74",
                "heart_rate": 84,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.6
            },
            "previous": {
                "blood_pressure": "112/70",
                "heart_rate": 96,
                "respiratory_rate": 18,
                "spo2": 97,
                "temperature": 38.4
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 76,
        "devices": [],
        "diagnosis": "Uncomplicated UTI",
        "gender": "F",
        "id": "19",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.1,
                "lactate": 1.2,
                "wbc": 11.2
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 1.3,
                "wbc": 12.5
            }
        },
        "mrn": "MRN-890123",
        "name": "Dorothy Wilson",
        "notes": [
            {
                "note": "Responding well to antibiotics, temp trending down",
                "time": "09:30"
            },
            {
                "note": "Patient reports decreased dysuria",
                "time": "07:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 22,
        "room": "3E-309",
        "sirs_criteria": 1,
        "vitals": {
            "current": {
                "blood_pressure": "132/84",
                "heart_rate": 78,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.8
            },
            "previous": {
                "blood_pressure": "130/82",
                "heart_rate": 76,
                "respiratory_rate": 14,
                "spo2": 97,
                "temperature": 38.1
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 47,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Alcohol withdrawal, stable",
        "gender": "M",
        "id": "20",
        "labs": {
            "current": {
                "bilirubin": 1.8,
                "creatinine": 1.0,
                "lactate": 1.1,
                "wbc": 8.5
            },
            "previous": {
                "bilirubin": 1.9,
                "creatinine": 1.1,
                "lactate": 1.3,
                "wbc": 9.2
            }
        },
        "mrn": "MRN-456790",
        "name": "Christopher Lee",
        "notes": [
            {
                "note": "CIWA score 4, no tremors",
                "time": "10:30"
            },
            {
                "note": "Patient calm, cooperative",
                "time": "08:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 18,
        "room": "3E-325",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "132/84",
                "heart_rate": 82,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.0
            },
            "previous": {
                "blood_pressure": "142/92",
                "heart_rate": 96,
                "respiratory_rate": 18,
                "spo2": 96,
                "temperature": 37.2
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 1
        }
    },
    {
        "admission_date": "2025-11-12",
        "age": 45,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Appendectomy (Day 1)",
        "gender": "F",
        "id": "21",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.1,
                "wbc": 10.5
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.8,
                "lactate": 1.0,
                "wbc": 11.2
            }
        },
        "mrn": "MRN-567890",
        "name": "Patricia Davis",
        "notes": [
            {
                "note": "Post-op recovery progressing well",
                "time": "08:00"
            },
            {
                "note": "Pain controlled with oral medications",
                "time": "06:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 15,
        "room": "3E-306",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "118/76",
                "heart_rate": 82,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.4
            },
            "previous": {
                "blood_pressure": "120/78",
                "heart_rate": 78,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 37.1
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 42,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Dehydration, improving",
        "gender": "F",
        "id": "22",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.1,
                "lactate": 1.0,
                "wbc": 7.8
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.4,
                "lactate": 1.3,
                "wbc": 8.2
            }
        },
        "mrn": "MRN-890124",
        "name": "Jessica Davis",
        "notes": [
            {
                "note": "Tolerating PO fluids well",
                "time": "10:00"
            },
            {
                "note": "Urine output improving",
                "time": "08:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 14,
        "room": "3E-329",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "118/74",
                "heart_rate": 76,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 36.9
            },
            "previous": {
                "blood_pressure": "108/68",
                "heart_rate": 92,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.1
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 44,
        "devices": [],
        "diagnosis": "Simple cellulitis, improving",
        "gender": "F",
        "id": "23",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.8,
                "lactate": 1.1,
                "wbc": 9.8
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.8,
                "lactate": 1.2,
                "wbc": 11.5
            }
        },
        "mrn": "MRN-678901",
        "name": "Nancy Clark",
        "notes": [
            {
                "note": "Erythema markedly improved",
                "time": "10:30"
            },
            {
                "note": "Patient ready for discharge on oral antibiotics",
                "time": "08:15"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 12,
        "room": "3E-317",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "120/78",
                "heart_rate": 76,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 37.2
            },
            "previous": {
                "blood_pressure": "118/76",
                "heart_rate": 82,
                "respiratory_rate": 16,
                "spo2": 98,
                "temperature": 37.9
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 51,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "Gastroenteritis, improving",
        "gender": "M",
        "id": "24",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.0,
                "wbc": 9.2
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 1.2,
                "wbc": 10.8
            }
        },
        "mrn": "MRN-012346",
        "name": "Kevin Martinez",
        "notes": [
            {
                "note": "Tolerating clear liquids well",
                "time": "10:00"
            },
            {
                "note": "No vomiting x24 hours",
                "time": "08:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 10,
        "room": "3E-321",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "126/80",
                "heart_rate": 74,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 37.1
            },
            "previous": {
                "blood_pressure": "118/76",
                "heart_rate": 88,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 37.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 29,
        "devices": [],
        "diagnosis": "Asthma exacerbation, stable",
        "gender": "F",
        "id": "25",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.8,
                "lactate": 0.9,
                "wbc": 8.8
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.8,
                "lactate": 1.0,
                "wbc": 9.2
            }
        },
        "mrn": "MRN-012347",
        "name": "Emily Rodriguez",
        "notes": [
            {
                "note": "Peak flow improved to 85% predicted",
                "time": "11:00"
            },
            {
                "note": "No wheezing on exam",
                "time": "09:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 9,
        "room": "3E-331",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "116/72",
                "heart_rate": 78,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 36.8
            },
            "previous": {
                "blood_pressure": "118/74",
                "heart_rate": 88,
                "respiratory_rate": 20,
                "spo2": 94,
                "temperature": 36.9
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 65,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "CHF exacerbation, stable",
        "gender": "M",
        "id": "26",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.2,
                "lactate": 1.0,
                "wbc": 8.2
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.1,
                "lactate": 1.0,
                "wbc": 8.5
            }
        },
        "mrn": "MRN-123456",
        "name": "William Lee",
        "notes": [
            {
                "note": "Diuresing well, weight down 2kg",
                "time": "10:15"
            },
            {
                "note": "No dyspnea at rest",
                "time": "08:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 8,
        "room": "3E-312A",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "128/78",
                "heart_rate": 76,
                "respiratory_rate": 16,
                "spo2": 96,
                "temperature": 36.7
            },
            "previous": {
                "blood_pressure": "125/76",
                "heart_rate": 74,
                "respiratory_rate": 16,
                "spo2": 96,
                "temperature": 36.6
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 1
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 54,
        "devices": [],
        "diagnosis": "Atrial fibrillation, rate controlled",
        "gender": "M",
        "id": "27",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 0.9,
                "wbc": 7.5
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 0.9,
                "wbc": 7.8
            }
        },
        "mrn": "MRN-123458",
        "name": "Robert Anderson",
        "notes": [
            {
                "note": "Heart rate well controlled on diltiazem",
                "time": "10:30"
            },
            {
                "note": "Patient asymptomatic",
                "time": "08:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 7,
        "room": "3E-332",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "128/80",
                "heart_rate": 82,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 36.7
            },
            "previous": {
                "blood_pressure": "132/84",
                "heart_rate": 118,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 36.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 56,
        "devices": [],
        "diagnosis": "Hypertensive urgency, controlled",
        "gender": "F",
        "id": "28",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 0.9,
                "wbc": 7.8
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 1.0,
                "lactate": 0.9,
                "wbc": 8.0
            }
        },
        "mrn": "MRN-890123",
        "name": "Susan Lewis",
        "notes": [
            {
                "note": "BP well controlled on oral meds",
                "time": "11:00"
            },
            {
                "note": "Patient asymptomatic, ready for discharge",
                "time": "09:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 6,
        "room": "3E-319",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "138/82",
                "heart_rate": 72,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 36.9
            },
            "previous": {
                "blood_pressure": "178/102",
                "heart_rate": 88,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 36.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-13",
        "age": 42,
        "devices": [],
        "diagnosis": "Observation for chest pain, ruled out MI",
        "gender": "M",
        "id": "29",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.9,
                "wbc": 7.2
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.8,
                "wbc": 7.5
            }
        },
        "mrn": "MRN-678901",
        "name": "Michael Chen",
        "notes": [
            {
                "note": "Patient resting comfortably, no complaints",
                "time": "10:00"
            },
            {
                "note": "Cardiac enzymes negative x2",
                "time": "08:30"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 5,
        "room": "3E-307",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "122/78",
                "heart_rate": 72,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 36.8
            },
            "previous": {
                "blood_pressure": "120/76",
                "heart_rate": 70,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 36.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 59,
        "devices": [],
        "diagnosis": "Post-cardiac catheterization",
        "gender": "F",
        "id": "30",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.9,
                "wbc": 7.5
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.9,
                "wbc": 7.8
            }
        },
        "mrn": "MRN-456789",
        "name": "Barbara White",
        "notes": [
            {
                "note": "Groin site intact, no hematoma",
                "time": "11:30"
            },
            {
                "note": "Ambulating without difficulty",
                "time": "10:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 4,
        "room": "3E-302",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "124/76",
                "heart_rate": 70,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 36.8
            },
            "previous": {
                "blood_pressure": "122/74",
                "heart_rate": 68,
                "respiratory_rate": 12,
                "spo2": 99,
                "temperature": 36.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 38,
        "devices": [],
        "diagnosis": "Pre-op for elective cholecystectomy",
        "gender": "F",
        "id": "31",
        "labs": {
            "current": {
                "bilirubin": 0.9,
                "creatinine": 0.8,
                "lactate": 0.8,
                "wbc": 6.8
            },
            "previous": {
                "bilirubin": 0.9,
                "creatinine": 0.8,
                "lactate": 0.8,
                "wbc": 7.0
            }
        },
        "mrn": "MRN-789012",
        "name": "Sarah Thompson",
        "notes": [
            {
                "note": "NPO since midnight, ready for surgery",
                "time": "11:00"
            },
            {
                "note": "Pre-op teaching completed",
                "time": "09:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 3,
        "room": "3E-304",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "115/72",
                "heart_rate": 68,
                "respiratory_rate": 12,
                "spo2": 99,
                "temperature": 36.9
            },
            "previous": {
                "blood_pressure": "118/74",
                "heart_rate": 66,
                "respiratory_rate": 12,
                "spo2": 99,
                "temperature": 36.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 39,
        "devices": [],
        "diagnosis": "Syncope workup, stable",
        "gender": "M",
        "id": "32",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.8,
                "wbc": 6.9
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.8,
                "wbc": 7.1
            }
        },
        "mrn": "MRN-234568",
        "name": "Daniel Kim",
        "notes": [
            {
                "note": "Telemetry normal, no arrhythmias",
                "time": "11:00"
            },
            {
                "note": "Patient ambulating without issues",
                "time": "09:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 2,
        "room": "3E-323",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "118/74",
                "heart_rate": 68,
                "respiratory_rate": 12,
                "spo2": 99,
                "temperature": 36.7
            },
            "previous": {
                "blood_pressure": "120/76",
                "heart_rate": 66,
                "respiratory_rate": 12,
                "spo2": 99,
                "temperature": 36.6
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 35,
        "devices": [],
        "diagnosis": "Migraine, resolving",
        "gender": "M",
        "id": "33",
        "labs": {
            "current": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.9,
                "wbc": 7.0
            },
            "previous": {
                "bilirubin": 0.6,
                "creatinine": 0.9,
                "lactate": 0.9,
                "wbc": 7.2
            }
        },
        "mrn": "MRN-678902",
        "name": "Steven Brown",
        "notes": [
            {
                "note": "Headache resolved with IV meds",
                "time": "11:30"
            },
            {
                "note": "Patient resting in dark room",
                "time": "10:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 1,
        "room": "3E-327",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "124/78",
                "heart_rate": 70,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 36.8
            },
            "previous": {
                "blood_pressure": "126/80",
                "heart_rate": 72,
                "respiratory_rate": 14,
                "spo2": 99,
                "temperature": 36.7
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    },
    {
        "admission_date": "2025-11-14",
        "age": 48,
        "devices": [
            {
                "days": 1,
                "type": "IV line"
            }
        ],
        "diagnosis": "GI bleed, stable",
        "gender": "M",
        "id": "34",
        "labs": {
            "current": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.0,
                "wbc": 8.2
            },
            "previous": {
                "bilirubin": 0.7,
                "creatinine": 0.9,
                "lactate": 1.1,
                "wbc": 8.5
            }
        },
        "mrn": "MRN-345680",
        "name": "Mark Thompson",
        "notes": [
            {
                "note": "No further melena, Hgb stable at 10.2",
                "time": "11:00"
            },
            {
                "note": "EGD scheduled for tomorrow",
                "time": "09:00"
            }
        ],
        "risk_level": "LOW",
        "risk_score": 16,
        "room": "3E-334",
        "sirs_criteria": 0,
        "vitals": {
            "current": {
                "blood_pressure": "122/76",
                "heart_rate": 78,
                "respiratory_rate": 14,
                "spo2": 98,
                "temperature": 36.9
            },
            "previous": {
                "blood_pressure": "118/72",
                "heart_rate": 88,
                "respiratory_rate": 16,
                "spo2": 97,
                "temperature": 36.8
            }
        },
        "ground_truth": {
            "sepsis_confirmed": false,
            "sepsis_onset_time": null,
            "sepsis_source": null,
            "organ_dysfunction": {},
            "qsofa_score": 0,
            "sofa_score": 0
        }
    }
]
