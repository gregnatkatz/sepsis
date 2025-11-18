"""
Train calibration model on Kaggle dataset
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.database import DimPatient
from app.model_calibration import train_calibrator_on_kaggle
import json

DATABASE_URL = "sqlite+aiosqlite:///./sepsis_data.db"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(
            select(DimPatient).where(DimPatient.id.like('KGL-%'))
        )
        patients = result.scalars().all()
        
        print(f"Loaded {len(patients)} Kaggle patients")
        
        patient_dicts = []
        for p in patients:
            patient_dicts.append({
                'id': p.id,
                'risk_score': p.risk_score,
                'cohort_tags': p.cohort_tags
            })
        
        print("Training calibrator...")
        calibrator, metrics = train_calibrator_on_kaggle(patient_dicts)
        
        calibrator.save('calibrator.pkl')
        print("Calibrator saved to calibrator.pkl")
        
        print("\nCalibration Metrics:")
        print(json.dumps(metrics, indent=2))
        
        import numpy as np
        test_scores = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        calibrated_probs = calibrator.predict_proba(test_scores)
        
        print("\nCalibrated Probabilities:")
        print("Risk Score -> Calibrated Probability")
        for score, prob in zip(test_scores, calibrated_probs):
            print(f"{score:3.0f} -> {prob:.4f} ({prob*100:.2f}%)")

if __name__ == "__main__":
    asyncio.run(main())
