"""
Check database schema and patient data
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///./sepsis_data.db"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        if any('patients' in str(t) for t in tables):
            result = await conn.execute(text("PRAGMA table_info(patients);"))
            schema = result.fetchall()
            print("\nPatients table schema:")
            for col in schema:
                print(f"  {col[1]} ({col[2]})")
            
            result = await conn.execute(text("SELECT COUNT(*) FROM patients WHERE id LIKE 'KGL-%';"))
            count = result.fetchone()[0]
            print(f"\nKaggle patients: {count}")
            
            result = await conn.execute(text("SELECT id, risk_score, cohort_tags FROM patients WHERE id LIKE 'KGL-%' LIMIT 5;"))
            samples = result.fetchall()
            print("\nSample Kaggle patients:")
            for sample in samples:
                print(f"  ID: {sample[0]}, Risk Score: {sample[1]}, Tags: {sample[2][:100] if sample[2] else 'None'}...")

if __name__ == "__main__":
    asyncio.run(main())
