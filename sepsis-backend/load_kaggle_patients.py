"""
Load Kaggle patients into the database
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.kaggle_etl import load_kaggle_dataset, transform_to_patient_records
from app.database import init_db, get_db, DimPatient, FactVitals, FactLabs
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

async def load_patients_to_db(max_patients: int = None):
    """Load Kaggle patients into database"""
    print(f"Initializing database...")
    await init_db()
    
    if max_patients:
        print(f"Loading Kaggle dataset (max {max_patients} patients)...")
    else:
        print(f"Loading FULL Kaggle dataset (all patients)...")
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    df = load_kaggle_dataset(csv_path, max_patients=max_patients, sample_strategy="all" if not max_patients else "balanced")
    
    print(f"Transforming to patient records...")
    patients = transform_to_patient_records(df)
    
    print(f"Inserting {len(patients)} patients into database...")
    
    async for db in get_db():
        for i, patient in enumerate(patients):
            from sqlalchemy import select
            result = await db.execute(
                select(DimPatient).where(DimPatient.id == patient['id'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  [{i+1}/{len(patients)}] Patient {patient['id']} already exists, skipping")
                continue
            
            db_patient = DimPatient(
                id=patient['id'],
                mrn=patient['mrn'],
                name=patient['name'],
                age=patient['age'],
                sex=patient['gender'],
                room=patient['room'],
                risk_level=patient['risk_level'],
                risk_score=patient['risk_score'],
                cohort_tags=json.dumps([patient['dataset_source'], f"sepsis_{patient['sepsis_label']}"])
            )
            db.add(db_patient)
            
            vitals = patient['vitals']['current']
            timestamp = datetime.now()
            time_key = int(timestamp.strftime('%Y%m%d'))  # YYYYMMDD format
            
            if vitals.get('heart_rate'):
                db.add(FactVitals(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    vital_name='hr',
                    value=vitals['heart_rate']
                ))
            
            if vitals.get('temperature'):
                db.add(FactVitals(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    vital_name='temp',
                    value=vitals['temperature']
                ))
            
            if vitals.get('respiratory_rate'):
                db.add(FactVitals(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    vital_name='rr',
                    value=vitals['respiratory_rate']
                ))
            
            if vitals.get('oxygen_saturation'):
                db.add(FactVitals(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    vital_name='spo2',
                    value=vitals['oxygen_saturation']
                ))
            
            if vitals.get('blood_pressure') and '/' in str(vitals['blood_pressure']):
                try:
                    sbp, dbp = map(int, str(vitals['blood_pressure']).split('/'))
                    db.add(FactVitals(
                        patient_id=patient['id'],
                        time_key=time_key,
                        timestamp=timestamp,
                        vital_name='bp_systolic',
                        value=sbp
                    ))
                    db.add(FactVitals(
                        patient_id=patient['id'],
                        time_key=time_key,
                        timestamp=timestamp,
                        vital_name='bp_diastolic',
                        value=dbp
                    ))
                except:
                    pass
            
            labs = patient['labs']['current']
            
            if labs.get('wbc'):
                db.add(FactLabs(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    lab_name='wbc',
                    value=labs['wbc']
                ))
            
            if labs.get('lactate'):
                db.add(FactLabs(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    lab_name='lactate',
                    value=labs['lactate']
                ))
            
            if labs.get('creatinine'):
                db.add(FactLabs(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    lab_name='creatinine',
                    value=labs['creatinine']
                ))
            
            if labs.get('platelets'):
                db.add(FactLabs(
                    patient_id=patient['id'],
                    time_key=time_key,
                    timestamp=timestamp,
                    lab_name='platelets',
                    value=labs['platelets']
                ))
            
            print(f"  [{i+1}/{len(patients)}] Inserted patient {patient['id']} ({patient['name']})")
        
        await db.commit()
        print(f"\n✅ Successfully loaded {len(patients)} Kaggle patients into database")
        break

if __name__ == "__main__":
    import sys
    max_patients = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(load_patients_to_db(max_patients=max_patients))
