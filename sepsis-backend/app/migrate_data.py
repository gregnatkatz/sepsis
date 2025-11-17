"""
Data migration script to populate database from MOCK_PATIENTS
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, AsyncSessionLocal, DimPatient, DimTime, FactVitals, FactLabs, FactInterventions, FactOutcomes
from mock_patients import MOCK_PATIENTS

async def migrate_patients():
    """Migrate mock patients to database"""
    print("Initializing database...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        print(f"Migrating {len(MOCK_PATIENTS)} patients...")
        
        seen_mrns = set()
        migrated_count = 0
        
        for patient_data in MOCK_PATIENTS:
            mrn = patient_data["mrn"]
            if mrn in seen_mrns:
                print(f"⚠️  Skipping duplicate MRN: {mrn} (patient: {patient_data['name']})")
                continue
            seen_mrns.add(mrn)
            patient = DimPatient(
                id=patient_data["id"],
                mrn=patient_data["mrn"],
                name=patient_data["name"],
                age=patient_data.get("age", 0),
                sex=patient_data.get("sex", "Unknown"),
                room=patient_data["room"],
                risk_level=patient_data["risk_level"],
                risk_score=patient_data["risk_score"],
                cohort_tags=json.dumps(patient_data.get("cohort_tags", []))
            )
            session.add(patient)
            
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            date_key = int(today.strftime("%Y%m%d"))
            
            existing_time = await session.get(DimTime, date_key)
            if not existing_time:
                time_dim = DimTime(
                    date_key=date_key,
                    date=today,
                    week_start=today - timedelta(days=today.weekday()),
                    month_start=today.replace(day=1),
                    year=today.year,
                    month=today.month,
                    week=today.isocalendar()[1],
                    day=today.day
                )
                session.add(time_dim)
            
            vitals = patient_data.get("vitals", {})
            timestamp = datetime.utcnow()
            
            current_vitals = vitals.get("current", vitals) if isinstance(vitals, dict) else {}
            
            vital_mapping = {
                "blood_pressure": "bp",
                "heart_rate": "hr",
                "respiratory_rate": "rr",
                "spo2": "spo2",
                "temperature": "temp"
            }
            
            for vital_key, vital_name in vital_mapping.items():
                value = current_vitals.get(vital_key)
                if value is None:
                    continue
                    
                if vital_name == "bp" and isinstance(value, str):
                    bp_parts = value.split("/")
                    if len(bp_parts) == 2:
                        session.add(FactVitals(
                            patient_id=patient_data["id"],
                            time_key=date_key,
                            timestamp=timestamp,
                            vital_name="bp_systolic",
                            value=float(bp_parts[0]),
                            unit="mmHg"
                        ))
                        session.add(FactVitals(
                            patient_id=patient_data["id"],
                            time_key=date_key,
                            timestamp=timestamp,
                            vital_name="bp_diastolic",
                            value=float(bp_parts[1]),
                            unit="mmHg"
                        ))
                else:
                    unit_map = {
                        "hr": "bpm",
                        "temp": "°C",
                        "rr": "breaths/min",
                        "spo2": "%"
                    }
                    session.add(FactVitals(
                        patient_id=patient_data["id"],
                        time_key=date_key,
                        timestamp=timestamp,
                        vital_name=vital_name,
                        value=float(value),
                        unit=unit_map.get(vital_name, "")
                    ))
            
            labs = patient_data.get("labs", {})
            
            current_labs = labs.get("current", labs) if isinstance(labs, dict) and "current" in labs else labs
            
            for lab_name, value in current_labs.items():
                if not isinstance(value, (int, float, str)):
                    continue
                    
                try:
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    continue
                    
                unit_map = {
                    "wbc": "K/μL",
                    "lactate": "mmol/L",
                    "creatinine": "mg/dL",
                    "platelets": "K/μL",
                    "bilirubin": "mg/dL"
                }
                session.add(FactLabs(
                    patient_id=patient_data["id"],
                    time_key=date_key,
                    timestamp=timestamp,
                    lab_name=lab_name,
                    value=numeric_value,
                    unit=unit_map.get(lab_name, "")
                ))
            
            session.add(FactOutcomes(
                patient_id=patient_data["id"],
                time_key=date_key,
                timestamp=timestamp,
                survived=1,  # Assume alive at baseline
                time_to_stability_hr=None,
                bundle_compliance_pct=0.0,
                early_warning_leadtime_hr=0.0,
                pathway_chosen="baseline",
                model_version="baseline"
            ))
            
            migrated_count += 1
        
        await session.commit()
        print(f"✅ Successfully migrated {migrated_count} patients to database (skipped {len(MOCK_PATIENTS) - migrated_count} duplicates)")

if __name__ == "__main__":
    asyncio.run(migrate_patients())
