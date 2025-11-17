"""
Database models and session management for Sepsis Prevention Copilot
Star schema design for efficient querying and trending analytics
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sepsis_data.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class DimPatient(Base):
    """Dimension table for patient demographics and cohort information"""
    __tablename__ = "dim_patient"
    
    id = Column(String, primary_key=True)
    mrn = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer)
    sex = Column(String)
    room = Column(String)
    risk_level = Column(String)
    risk_score = Column(Float)
    cohort_tags = Column(Text)  # JSON string of tags
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    vitals = relationship("FactVitals", back_populates="patient")
    labs = relationship("FactLabs", back_populates="patient")
    interventions = relationship("FactInterventions", back_populates="patient")
    outcomes = relationship("FactOutcomes", back_populates="patient")
    eval_results = relationship("FactEvalResults", back_populates="patient")

class DimTime(Base):
    """Dimension table for time-based queries and trending"""
    __tablename__ = "dim_time"
    
    date_key = Column(Integer, primary_key=True)  # YYYYMMDD format
    date = Column(DateTime, nullable=False)
    week_start = Column(DateTime)
    month_start = Column(DateTime)
    year = Column(Integer)
    month = Column(Integer)
    week = Column(Integer)
    day = Column(Integer)

class FactVitals(Base):
    """Fact table for patient vitals over time"""
    __tablename__ = "fact_vitals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("dim_patient.id"), nullable=False)
    time_key = Column(Integer, ForeignKey("dim_time.date_key"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    vital_name = Column(String, nullable=False)  # hr, bp_systolic, bp_diastolic, temp, rr, spo2
    value = Column(Float, nullable=False)
    unit = Column(String)
    
    patient = relationship("DimPatient", back_populates="vitals")

class FactLabs(Base):
    """Fact table for lab results over time"""
    __tablename__ = "fact_labs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("dim_patient.id"), nullable=False)
    time_key = Column(Integer, ForeignKey("dim_time.date_key"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    lab_name = Column(String, nullable=False)  # wbc, lactate, creatinine, etc.
    value = Column(Float, nullable=False)
    unit = Column(String)
    
    patient = relationship("DimPatient", back_populates="labs")

class FactInterventions(Base):
    """Fact table for interventions and treatments"""
    __tablename__ = "fact_interventions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("dim_patient.id"), nullable=False)
    time_key = Column(Integer, ForeignKey("dim_time.date_key"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    fluids_ml = Column(Integer)
    antibiotics_type = Column(String)
    antibiotics_timing_min = Column(Integer)
    vasopressor_type = Column(String)
    vasopressor_dose = Column(Float)
    vasopressor_timing_min = Column(Integer)
    
    patient = relationship("DimPatient", back_populates="interventions")

class FactOutcomes(Base):
    """Fact table for patient outcomes and metrics"""
    __tablename__ = "fact_outcomes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("dim_patient.id"), nullable=False)
    time_key = Column(Integer, ForeignKey("dim_time.date_key"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    survived = Column(Integer)  # 0 or 1
    time_to_stability_hr = Column(Float)
    bundle_compliance_pct = Column(Float)
    early_warning_leadtime_hr = Column(Float)
    pathway_chosen = Column(String)
    model_version = Column(String)  # "baseline", "rl-v1", "model-router", etc.
    
    patient = relationship("DimPatient", back_populates="outcomes")

class FactEvalResults(Base):
    """Fact table for Monte Carlo evaluation results (cached)"""
    __tablename__ = "fact_eval_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("dim_patient.id"), nullable=False)
    time_key = Column(Integer, ForeignKey("dim_time.date_key"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    model = Column(String, nullable=False)  # "model-router", "gpt-5", "o3", etc.
    samples = Column(Integer, nullable=False)
    seed = Column(Integer)
    content_hash = Column(String, unique=True, nullable=False)  # patient_id|samples|seed
    json_result = Column(Text, nullable=False)  # Full JSON result
    composite_score = Column(Float)
    best_pathway = Column(String)
    survival_prob = Column(Float)
    time_to_stability = Column(Float)
    organ_preservation = Column(Float)
    
    patient = relationship("DimPatient", back_populates="eval_results")

class EvaluationRun(Base):
    """Table for tracking batch evaluation runs"""
    __tablename__ = "evaluation_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String)  # NULL for batch runs across all patients
    samples = Column(Integer, nullable=False)
    seed = Column(Integer)
    status = Column(String, nullable=False)  # "pending", "running", "completed", "failed"
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    error = Column(Text)
    results_count = Column(Integer, default=0)
