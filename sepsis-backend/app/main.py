from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import json
from datetime import datetime, timedelta
import asyncio
from pathlib import Path
import websockets
import base64
import sys
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_patients import MOCK_PATIENTS
from featured_patients import FEATURED_PATIENTS, get_featured_patients_with_history
from app.agui import create_agui_session, handle_agui_websocket
from app.llm_client import get_llm_client, ModelType
from app.database import (
    get_db, init_db, DimPatient, FactVitals, FactLabs, 
    FactInterventions, FactOutcomes, FactEvalResults, EvaluationRun
)
from app.evaluation_agent import (
    run_evaluation_for_patient, run_batch_evaluation, 
    get_evaluation_run_status, get_cached_evaluation
)
from app.reports import get_trending_outcomes, get_pathway_adoption
from app.synthetic_outcomes import generate_synthetic_outcomes, generate_pathway_adoption as generate_synthetic_pathway_adoption
from app.validation_metrics import calculate_validation_metrics
from app.risk_logic import (
    is_patient_high_risk, get_risk_reason, classify_risk_level,
    calculate_sepsis_stage, get_priority_score, get_patient_lactate, get_patient_sirs
)
from clinical_parameters import (
    generate_patient_clinical_data, get_current_parameters, 
    get_parameter_categories, ARCHETYPES, CLINICAL_PARAMETERS,
    generate_lactate_clearance_curve
)
from app.multi_agent_analysis import (
    run_multi_agent_analysis, clear_agent_cache,
    AgentFinding, AggregatedAnalysis
)

load_dotenv()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://gpt-env-app-1ch3k8ec.devinapps.com",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

client = AzureOpenAI(
    api_key=os.getenv("GPT41_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def get_llm(model_override: Optional[str] = None) -> Any:
    """Get LLM client with optional model override from query param"""
    if model_override:
        try:
            model_type = ModelType(model_override)
            return get_llm_client(model_type)
        except ValueError:
            pass  # Fall back to default
    return get_llm_client()

class ChatRequest(BaseModel):
    message: str
    patient_id: Optional[str] = None

class PatientQuery(BaseModel):
    room: Optional[str] = None
    patient_id: Optional[str] = None

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

async def get_patient_from_db(patient_id: str, db: AsyncSession) -> Optional[Dict]:
    """Helper to get patient data from database"""
    result = await db.execute(
        select(DimPatient).where(DimPatient.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return None
    
    vitals_result = await db.execute(
        select(FactVitals)
        .where(FactVitals.patient_id == patient_id)
        .order_by(FactVitals.timestamp.desc())
        .limit(10)
    )
    vitals_rows = vitals_result.scalars().all()
    
    labs_result = await db.execute(
        select(FactLabs)
        .where(FactLabs.patient_id == patient_id)
        .order_by(FactLabs.timestamp.desc())
        .limit(10)
    )
    labs_rows = labs_result.scalars().all()
    
    vitals_dict = {}
    for v in vitals_rows:
        vitals_dict[v.vital_name] = v.value
    
    labs_dict = {}
    for l in labs_rows:
        labs_dict[l.lab_name] = l.value
    
    if "bp_systolic" in vitals_dict and "bp_diastolic" in vitals_dict:
        vitals_dict["blood_pressure"] = f"{int(vitals_dict['bp_systolic'])}/{int(vitals_dict['bp_diastolic'])}"
    else:
        vitals_dict["blood_pressure"] = "120/80"  # Default for Kaggle patients
    
    sirs_count = 0
    temp = vitals_dict.get("temp", 37.0)
    hr = vitals_dict.get("hr", 70)
    rr = vitals_dict.get("rr", 16)
    wbc = labs_dict.get("wbc", 8.0)
    
    if temp < 36 or temp > 38:
        sirs_count += 1
    if hr > 90:
        sirs_count += 1
    if rr > 20:
        sirs_count += 1
    if wbc < 4 or wbc > 12:
        sirs_count += 1
    
    cohort_tags = json.loads(patient.cohort_tags) if patient.cohort_tags else []
    is_kaggle = "kaggle" in cohort_tags
    
    if is_kaggle:
        diagnoses = [
            "Pneumonia with sepsis",
            "Urinary tract infection",
            "Abdominal sepsis",
            "Skin and soft tissue infection",
            "Bacteremia",
            "Post-operative infection",
            "Aspiration pneumonia",
            "Cholecystitis",
            "Pyelonephritis",
            "Cellulitis"
        ]
        try:
            parts = patient_id.split('-')
            if len(parts) >= 2:
                diagnosis_idx = int(parts[1]) % len(diagnoses)
            else:
                diagnosis_idx = hash(patient_id) % len(diagnoses)
        except (ValueError, IndexError):
            diagnosis_idx = hash(patient_id) % len(diagnoses)
        diagnosis = diagnoses[diagnosis_idx]
    else:
        diagnosis = "Sepsis monitoring"
    
    return {
        "id": patient.id,
        "mrn": patient.mrn,
        "name": patient.name,
        "age": patient.age,
        "sex": patient.sex,
        "gender": patient.sex,  # Map sex to gender for frontend
        "room": patient.room,
        "diagnosis": diagnosis,
        "risk_level": patient.risk_level,
        "risk_score": patient.risk_score,
        "sirs_criteria": sirs_count,
        "cohort_tags": cohort_tags,
        "devices": [],  # Kaggle patients don't have device data
        "ground_truth": {},  # No ground truth for Kaggle patients
        "vitals": {
            "current": {
                "heart_rate": vitals_dict.get("hr", 70),
                "blood_pressure": vitals_dict.get("blood_pressure", "120/80"),
                "respiratory_rate": vitals_dict.get("rr", 16),
                "temperature": vitals_dict.get("temp", 37.0),
                "spo2": vitals_dict.get("spo2", 98)
            }
        },
        "labs": {
            "current": {
                "wbc": labs_dict.get("wbc", 8.0),
                "lactate": labs_dict.get("lactate", 1.5),
                "creatinine": labs_dict.get("creatinine", 1.0),
                "bilirubin": labs_dict.get("bilirubin", 0.8),
                "platelets": labs_dict.get("platelets", 200)
            }
        }
    }

@app.get("/api/patients")
async def get_patients(
    limit: int = 500,
    offset: int = 0,
    dataset: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get patients from database with pagination and filtering
    
    Args:
        limit: Maximum number of patients to return (default 500)
        offset: Number of patients to skip (default 0)
        dataset: Filter by dataset (kaggle, synthetic, or None for all)
    """
    query = select(DimPatient).order_by(DimPatient.risk_score.desc(), DimPatient.created_at.desc())
    
    count_result = await db.execute(select(func.count()).select_from(DimPatient))
    total = count_result.scalar()
    
    if total == 0:
        return {
            "patients": MOCK_PATIENTS,
            "total": len(MOCK_PATIENTS),
            "limit": limit,
            "offset": offset
        }
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    patients = result.scalars().all()
    
    patient_list = []
    for p in patients:
        # Parse cohort_tags
        cohort_tags = []
        if p.cohort_tags:
            try:
                cohort_tags = json.loads(p.cohort_tags)
            except:
                cohort_tags = []
        
        if dataset:
            if dataset == "kaggle" and "kaggle" not in cohort_tags:
                continue
            elif dataset == "synthetic" and "synthetic" not in cohort_tags:
                continue
        
        # Fetch latest vitals for this patient
        vitals_result = await db.execute(
            select(FactVitals)
            .where(FactVitals.patient_id == p.id)
            .order_by(FactVitals.timestamp.desc())
            .limit(10)
        )
        vitals_rows = vitals_result.scalars().all()
        vitals_dict = {v.vital_name: v.value for v in vitals_rows}
        
        # Fetch latest labs for this patient
        labs_result = await db.execute(
            select(FactLabs)
            .where(FactLabs.patient_id == p.id)
            .order_by(FactLabs.timestamp.desc())
            .limit(10)
        )
        labs_rows = labs_result.scalars().all()
        labs_dict = {l.lab_name: l.value for l in labs_rows}
        
        # Calculate blood pressure string
        if "bp_systolic" in vitals_dict and "bp_diastolic" in vitals_dict:
            blood_pressure = f"{int(vitals_dict['bp_systolic'])}/{int(vitals_dict['bp_diastolic'])}"
        else:
            blood_pressure = "120/80"
        
        # Calculate SIRS criteria
        temp = vitals_dict.get("temp", 37.0)
        hr = vitals_dict.get("hr", 70)
        rr = vitals_dict.get("rr", 16)
        wbc = labs_dict.get("wbc", 8.0)
        
        sirs_count = 0
        if temp < 36 or temp > 38:
            sirs_count += 1
        if hr > 90:
            sirs_count += 1
        if rr > 20:
            sirs_count += 1
        if wbc < 4 or wbc > 12:
            sirs_count += 1
        
        # Generate diagnosis based on patient ID for Kaggle patients
        is_kaggle = "kaggle" in cohort_tags
        if is_kaggle:
            diagnoses = [
                "Pneumonia with sepsis",
                "Urinary tract infection",
                "Abdominal sepsis",
                "Skin and soft tissue infection",
                "Bacteremia",
                "Post-operative infection",
                "Aspiration pneumonia",
                "Cholecystitis",
                "Pyelonephritis",
                "Cellulitis"
            ]
            try:
                diagnosis_idx = int(p.id.split('-')[1]) % len(diagnoses)
            except:
                diagnosis_idx = hash(p.id) % len(diagnoses)
            diagnosis = diagnoses[diagnosis_idx]
        else:
            diagnosis = "Sepsis monitoring"
        
        patient_summary = {
            "id": p.id,
            "mrn": p.mrn,
            "name": p.name,
            "age": p.age,
            "gender": "Male" if p.sex == 1 else "Female",
            "room": p.room,
            "risk_level": p.risk_level,
            "risk_score": p.risk_score,
            "cohort_tags": cohort_tags,
            "sirs_criteria": sirs_count,
            "diagnosis": diagnosis,
            "vitals": {
                "current": {
                    "heart_rate": vitals_dict.get("hr", 70),
                    "blood_pressure": blood_pressure,
                    "respiratory_rate": vitals_dict.get("rr", 16),
                    "temperature": vitals_dict.get("temp", 37.0),
                    "spo2": vitals_dict.get("spo2", 98)
                }
            },
            "labs": {
                "current": {
                    "wbc": labs_dict.get("wbc", 8.0),
                    "lactate": labs_dict.get("lactate", 1.5),
                    "creatinine": labs_dict.get("creatinine", 1.0),
                    "bilirubin": labs_dict.get("bilirubin", 0.8),
                    "platelets": labs_dict.get("platelets", 200)
                }
            }
        }
        patient_list.append(patient_summary)
    
    return {
        "patients": patient_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Get single patient from database, fallback to MOCK_PATIENTS if not found"""
    patient = await get_patient_from_db(patient_id, db)
    
    if not patient:
        # Fallback to MOCK_PATIENTS
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return patient

def calculate_sirs_criteria(patient: Dict) -> Dict:
    vitals = patient["vitals"]["current"]
    labs = patient["labs"]["current"]
    
    criteria = []
    count = 0
    
    if vitals["temperature"] > 38 or vitals["temperature"] < 36:
        criteria.append(f"Temperature: {vitals['temperature']}°C (abnormal)")
        count += 1
    
    if vitals["heart_rate"] > 90:
        criteria.append(f"Heart Rate: {vitals['heart_rate']} bpm (tachycardia)")
        count += 1
    
    if vitals["respiratory_rate"] > 20:
        criteria.append(f"Respiratory Rate: {vitals['respiratory_rate']} (tachypnea)")
        count += 1
    
    if labs["wbc"] > 12 or labs["wbc"] < 4:
        criteria.append(f"WBC: {labs['wbc']} K/µL (abnormal)")
        count += 1
    
    return {"count": count, "criteria": criteria}

def generate_clinical_assessment(patient: Dict) -> str:
    vitals_current = patient["vitals"]["current"]
    vitals_prev = patient["vitals"]["previous"]
    labs_current = patient["labs"]["current"]
    labs_prev = patient["labs"]["previous"]
    
    sirs = calculate_sirs_criteria(patient)
    
    assessment = f"""
**Patient: {patient['name']} ({patient['room']})**
Age: {patient['age']} | Gender: {patient['gender']} | Admission: {patient['admission_date']}
Diagnosis: {patient['diagnosis']}

🔴 **Critical Changes (Last 4 Hours):**
"""
    
    lactate_change = ((labs_current["lactate"] - labs_prev["lactate"]) / labs_prev["lactate"]) * 100
    if abs(lactate_change) > 10:
        assessment += f"• Lactate: {labs_prev['lactate']} → {labs_current['lactate']} mmol/L (↑{lactate_change:.0f}%)\n"
    
    hr_change = vitals_current["heart_rate"] - vitals_prev["heart_rate"]
    if abs(hr_change) > 10:
        assessment += f"• Heart Rate: {vitals_prev['heart_rate']} → {vitals_current['heart_rate']} bpm "
        assessment += "(tachycardia)\n" if vitals_current["heart_rate"] > 90 else "\n"
    
    if patient["notes"]:
        assessment += f"• {patient['notes'][0]['note']} (at {patient['notes'][0]['time']})\n"
    
    assessment += f"\n⚠️ **Risk Factors:**\n"
    assessment += f"• {patient['diagnosis']}\n"
    
    for device in patient["devices"]:
        assessment += f"• {device['type']} since admission (Day {device['days']})\n"
    
    wbc_trend = f"{labs_prev['wbc']} → {labs_current['wbc']}"
    assessment += f"• WBC trending up: {wbc_trend}\n"
    
    assessment += f"\n📊 **SIRS Criteria: {sirs['count']} of 4 met**\n"
    for criterion in sirs["criteria"]:
        assessment += f"• {criterion}\n"
    
    assessment += f"\n🎯 **Sepsis Risk Score: {patient['risk_score']}/100 - {patient['risk_level']} RISK**\n"
    
    assessment += "\n**Recommended Actions:**\n"
    
    if patient["risk_score"] >= 70:
        assessment += "1. Blood cultures ×2 from separate sites (STAT)\n"
        assessment += "2. Repeat lactate in 2-4 hours\n"
        assessment += "3. Notify attending physician immediately\n"
        assessment += "4. Consider empiric antibiotics after cultures\n"
        assessment += "5. Increase monitoring frequency\n"
    elif patient["risk_score"] >= 50:
        assessment += "1. Monitor vitals every 2 hours\n"
        assessment += "2. Repeat labs in 4-6 hours\n"
        assessment += "3. Notify physician of trending changes\n"
        assessment += "4. Consider blood cultures if condition worsens\n"
    else:
        assessment += "1. Continue routine monitoring\n"
        assessment += "2. Reassess if clinical status changes\n"
    
    if any(d["type"] == "Foley catheter" and d["days"] >= 3 for d in patient["devices"]):
        assessment += f"\n💡 **Prevention Opportunity:**\n"
        assessment += "• Consider Foley catheter removal (Day 3+) to prevent CAUTI\n"
    
    return assessment

@app.post("/api/chat")
async def chat(request: ChatRequest):
    message = request.message.lower()
    
    patient = None
    if request.patient_id:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == request.patient_id), None)
    else:
        for p in MOCK_PATIENTS:
            if p["room"].lower() in message or p["name"].lower() in message:
                patient = p
                break
    
    if patient:
        assessment = generate_clinical_assessment(patient)
        
        async def generate():
            for chunk in assessment.split("\n"):
                yield f"data: {json.dumps({'content': chunk + '\\n'})}\n\n"
                await asyncio.sleep(0.05)
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        system_prompt = """You are a clinical AI assistant helping nurses with sepsis prevention and detection. 
        Provide evidence-based, actionable recommendations. Be concise and clear."""
        
        try:
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ],
                stream=True,
                temperature=0.7,
                max_tokens=1000
            )
            
            async def generate():
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            
            return StreamingResponse(generate(), media_type="text/event-stream")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-patient")
async def analyze_patient(query: PatientQuery):
    patient = None
    
    if query.patient_id:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == query.patient_id), None)
    elif query.room:
        patient = next((p for p in MOCK_PATIENTS if p["room"].lower() == query.room.lower()), None)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    assessment = generate_clinical_assessment(patient)
    
    async def generate():
        for chunk in assessment.split("\n"):
            yield f"data: {json.dumps({'content': chunk + '\\n'})}\n\n"
            await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'done': True, 'patient': patient})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/high-risk-patients")
async def get_high_risk_patients():
    """Get high-risk patients using Smart Logic for improved PPV"""
    high_risk = []
    for p in MOCK_PATIENTS:
        if is_patient_high_risk(p):
            patient_data = {**p}
            patient_data["risk_reason"] = get_risk_reason(p)
            patient_data["smart_risk_level"] = classify_risk_level(p)
            stage_name, stage_num = calculate_sepsis_stage(p)
            patient_data["sepsis_stage"] = stage_name
            patient_data["sepsis_stage_num"] = stage_num
            patient_data["priority_score"] = get_priority_score(p)
            high_risk.append(patient_data)
    
    # Sort by priority score (highest first)
    high_risk.sort(key=lambda x: x["priority_score"], reverse=True)
    return {"patients": high_risk, "count": len(high_risk)}


@app.get("/api/sepsis-worklist")
async def get_sepsis_worklist():
    """
    Clinical Worklist: Prioritized list of patients requiring immediate attention.
    Sorted by sepsis stage, risk score, and time since admission.
    This is the primary view for nurses/clinicians to triage patients.
    """
    worklist = []
    for p in MOCK_PATIENTS:
        if is_patient_high_risk(p):
            stage_name, stage_num = calculate_sepsis_stage(p)
            sirs_count = get_patient_sirs(p)
            lactate = get_patient_lactate(p)
            
            # Calculate hours since admission
            admission_date = p.get("admission_date", "2025-11-14")
            try:
                admission_dt = datetime.strptime(admission_date, "%Y-%m-%d")
                hours_since_admission = (datetime.now() - admission_dt).total_seconds() / 3600
            except:
                hours_since_admission = 48
            
            worklist_item = {
                "id": p["id"],
                "name": p["name"],
                "mrn": p.get("mrn", ""),
                "room": p.get("room", ""),
                "age": p.get("age", 0),
                "gender": p.get("gender", ""),
                "diagnosis": p.get("diagnosis", ""),
                "risk_score": p.get("risk_score", 0),
                "risk_level": classify_risk_level(p),
                "risk_reason": get_risk_reason(p),
                "sepsis_stage": stage_name,
                "sepsis_stage_num": stage_num,
                "sirs_count": sirs_count,
                "lactate": lactate,
                "priority_score": get_priority_score(p),
                "hours_since_admission": round(hours_since_admission, 1),
                "devices": p.get("devices", []),
                "vitals": p.get("vitals", {}).get("current", {}),
                "labs": p.get("labs", {}).get("current", {}),
                "notes": p.get("notes", [])[:2]  # Last 2 notes
            }
            worklist.append(worklist_item)
    
    # Sort by priority (sepsis stage desc, then risk score desc)
    worklist.sort(key=lambda x: (x["sepsis_stage_num"], x["priority_score"]), reverse=True)
    
    return {
        "worklist": worklist,
        "count": len(worklist),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/watchlist-patients")
async def get_watchlist_patients():
    """
    Watchlist: Sub-threshold patients who need monitoring.
    These are patients with moderate risk (40-49) who have concerning signs.
    Nurses should check these patients regularly for deterioration.
    """
    watchlist = []
    for p in MOCK_PATIENTS:
        risk_score = p.get("risk_score", 0)
        sirs_count = get_patient_sirs(p)
        lactate = get_patient_lactate(p)
        
        # Watchlist criteria: moderate risk with some warning signs
        if 40 <= risk_score < 50 and (sirs_count >= 2 or lactate > 1.5):
            stage_name, stage_num = calculate_sepsis_stage(p)
            
            watchlist_item = {
                "id": p["id"],
                "name": p["name"],
                "mrn": p.get("mrn", ""),
                "room": p.get("room", ""),
                "age": p.get("age", 0),
                "gender": p.get("gender", ""),
                "diagnosis": p.get("diagnosis", ""),
                "risk_score": risk_score,
                "risk_level": "WATCH",
                "watch_reason": f"Risk {risk_score} with SIRS={sirs_count}, Lactate={lactate:.1f}",
                "sepsis_stage": stage_name,
                "sirs_count": sirs_count,
                "lactate": lactate,
                "vitals": p.get("vitals", {}).get("current", {}),
                "labs": p.get("labs", {}).get("current", {}),
                "recommended_actions": [
                    "Monitor vitals every 2 hours",
                    "Repeat lactate in 4 hours",
                    "Notify physician if condition worsens"
                ]
            }
            watchlist.append(watchlist_item)
    
    # Sort by risk score descending
    watchlist.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "watchlist": watchlist,
        "count": len(watchlist),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/patients/{patient_id}/sepsis-huddle-summary")
async def get_sepsis_huddle_summary(patient_id: str):
    """
    Sepsis Huddle Summary: Quick clinical summary for rapid huddles.
    Consolidates: why worried, trajectory, top 3 actions, bundle status.
    """
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    stage_name, stage_num = calculate_sepsis_stage(patient)
    sirs_count = get_patient_sirs(patient)
    lactate = get_patient_lactate(patient)
    risk_reason = get_risk_reason(patient)
    
    # Determine trajectory based on vitals/labs trends
    vitals_current = patient.get("vitals", {}).get("current", {})
    vitals_prev = patient.get("vitals", {}).get("previous", {})
    labs_current = patient.get("labs", {}).get("current", {})
    labs_prev = patient.get("labs", {}).get("previous", {})
    
    trajectory = "stable"
    trajectory_details = []
    
    if vitals_prev and labs_prev:
        hr_change = vitals_current.get("heart_rate", 0) - vitals_prev.get("heart_rate", 0)
        lactate_change = labs_current.get("lactate", 0) - labs_prev.get("lactate", 0)
        
        if hr_change > 10 or lactate_change > 0.5:
            trajectory = "worsening"
            if hr_change > 10:
                trajectory_details.append(f"HR increased by {hr_change}")
            if lactate_change > 0.5:
                trajectory_details.append(f"Lactate increased by {lactate_change:.1f}")
        elif hr_change < -10 or lactate_change < -0.3:
            trajectory = "improving"
            if hr_change < -10:
                trajectory_details.append(f"HR decreased by {abs(hr_change)}")
            if lactate_change < -0.3:
                trajectory_details.append(f"Lactate decreased by {abs(lactate_change):.1f}")
    
    # Top 3 recommended actions based on stage
    if stage_num >= 3:
        top_actions = [
            "Blood cultures x2 from separate sites (STAT)",
            "Broad-spectrum antibiotics within 1 hour",
            "30 mL/kg crystalloid for hypotension or lactate >= 4"
        ]
    elif stage_num >= 2:
        top_actions = [
            "Blood cultures before antibiotics",
            "Repeat lactate in 2-4 hours",
            "Notify attending physician"
        ]
    else:
        top_actions = [
            "Continue monitoring vitals q2h",
            "Repeat labs in 4-6 hours",
            "Reassess if clinical status changes"
        ]
    
    return {
        "patient_id": patient_id,
        "name": patient.get("name", ""),
        "room": patient.get("room", ""),
        "diagnosis": patient.get("diagnosis", ""),
        "why_worried": {
            "risk_score": patient.get("risk_score", 0),
            "risk_reason": risk_reason,
            "sepsis_stage": stage_name,
            "sirs_count": sirs_count,
            "lactate": lactate
        },
        "trajectory": {
            "status": trajectory,
            "details": trajectory_details
        },
        "top_actions": top_actions,
        "bundle_status": {
            "blood_cultures": "pending",
            "lactate_measured": True,
            "antibiotics": "pending",
            "fluids": "pending" if stage_num >= 3 else "not_indicated"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/featured-patients")
async def get_featured_patients():
    """
    Get featured demo patients with comprehensive EHR-like data.
    These 4 patients demonstrate different sepsis presentations:
    1. UTI Septic Shock (Critical)
    2. Pneumonia Sepsis (High Risk)
    3. Necrotizing Fasciitis (Moderate - Smart Logic catch)
    4. Post-op Abdominal (Watchlist candidate)
    """
    patients_with_history = get_featured_patients_with_history()
    
    # Add Smart Logic analysis to each patient
    for p in patients_with_history:
        p["is_high_risk"] = is_patient_high_risk(p)
        p["risk_reason"] = get_risk_reason(p)
        p["smart_risk_level"] = classify_risk_level(p)
        stage_name, stage_num = calculate_sepsis_stage(p)
        p["sepsis_stage"] = stage_name
        p["sepsis_stage_num"] = stage_num
        p["priority_score"] = get_priority_score(p)
    
    return {
        "patients": patients_with_history,
        "count": len(patients_with_history),
        "description": "Featured demo patients with 120-hour history data"
    }


@app.get("/api/patients/{patient_id}/journey-120hr")
async def get_patient_journey_120hr(patient_id: str):
    """
    Get 120-hour patient journey data for EPIC-style reporting.
    Includes vitals history, labs history, medications, notes, and bundle status.
    """
    # Check featured patients first
    featured = get_featured_patients_with_history()
    patient = next((p for p in featured if p["id"] == patient_id), None)
    
    if not patient:
        # Fall back to mock patients
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
        if patient:
            # Generate 120-hour history for mock patient
            from featured_patients import generate_120hr_vitals_history, generate_120hr_labs_history
            
            vitals_current = patient.get("vitals", {}).get("current", {})
            base_vitals = {
                "heart_rate": vitals_current.get("heart_rate", 80) - 15,
                "temperature": vitals_current.get("temperature", 37.0) - 0.8,
                "systolic_bp": 120,
                "diastolic_bp": 75,
                "respiratory_rate": vitals_current.get("respiratory_rate", 16) - 4,
                "spo2": min(100, vitals_current.get("spo2", 98) + 3)
            }
            
            labs_current = patient.get("labs", {}).get("current", {})
            base_labs = {
                "lactate": max(0.8, labs_current.get("lactate", 1.0) - 1.5),
                "wbc": max(5, labs_current.get("wbc", 8.0) - 6.0),
                "creatinine": max(0.7, labs_current.get("creatinine", 1.0) - 0.5),
                "bilirubin": max(0.3, labs_current.get("bilirubin", 0.8) - 0.3)
            }
            
            trajectory = "worsening" if patient.get("risk_level") in ["CRITICAL", "HIGH"] else "stable"
            patient["vitals_history"] = generate_120hr_vitals_history(base_vitals, trajectory)
            patient["labs_history"] = generate_120hr_labs_history(base_labs, trajectory)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Add Smart Logic analysis
    patient["is_high_risk"] = is_patient_high_risk(patient)
    patient["risk_reason"] = get_risk_reason(patient)
    stage_name, stage_num = calculate_sepsis_stage(patient)
    patient["sepsis_stage"] = stage_name
    patient["sepsis_stage_num"] = stage_num
    
    return {
        "patient": patient,
        "vitals_history": patient.get("vitals_history", []),
        "labs_history": patient.get("labs_history", []),
        "medications": patient.get("medications", []),
        "notes": patient.get("notes", []),
        "problem_list": patient.get("problem_list", []),
        "allergies": patient.get("allergies", []),
        "devices": patient.get("devices", []),
        "sepsis_bundle": patient.get("sepsis_bundle", {}),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/patients/{patient_id}/comprehensive-data")
async def get_patient_comprehensive_data(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get comprehensive clinical data for a patient with 150+ parameters.
    Based on real sepsis pathophysiology and post-mortem findings.
    
    Returns:
    - 120-hour time series data for all clinical parameters
    - Organized by clinical panels (vitals, CBC, metabolic, coag, ABG, inflammatory, cardiac, renal, scores, microbiology, imaging, interventions, outcomes)
    - Realistic progression based on patient archetype (survivor vs non-survivor)
    - Lactate clearance curves
    - Organ dysfunction sequences
    """
    # Get patient from database or featured patients
    patient = await get_patient_from_db(patient_id, db)
    
    if not patient:
        featured = get_featured_patients_with_history()
        patient = next((p for p in featured if p["id"] == patient_id), None)
    
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Determine archetype based on patient risk level and outcome
    risk_level = patient.get("risk_level", "MODERATE")
    if risk_level == "CRITICAL":
        # 30% chance of non-survivor for critical patients
        import random
        if random.random() < 0.3:
            archetype = "refractory_shock_nonsurvivor"
        else:
            archetype = "septic_shock_survivor"
    elif risk_level == "HIGH":
        archetype = "septic_shock_survivor"
    elif risk_level == "MODERATE":
        # 10% chance of late MODS for moderate patients
        import random
        if random.random() < 0.1:
            archetype = "late_mods_nonsurvivor"
        else:
            archetype = "uncomplicated_sepsis"
    else:
        archetype = "uncomplicated_sepsis"
    
    # Generate comprehensive clinical data
    clinical_data = generate_patient_clinical_data(
        patient_id=patient_id,
        archetype=archetype,
        hours=120,
        interval_hours=4
    )
    
    # Generate lactate clearance curve
    lactate_clearance = generate_lactate_clearance_curve(archetype, hours=72)
    
    # Get current parameters (at presentation)
    current_params = get_current_parameters(clinical_data)
    
    # Get parameter categories for frontend
    categories = get_parameter_categories()
    
    # Add Smart Logic analysis
    is_high_risk = is_patient_high_risk(patient)
    risk_reason = get_risk_reason(patient)
    stage_name, stage_num = calculate_sepsis_stage(patient)
    
    return {
        "patient": {
            "id": patient.get("id"),
            "name": patient.get("name"),
            "mrn": patient.get("mrn"),
            "age": patient.get("age"),
            "room": patient.get("room"),
            "risk_level": risk_level,
            "risk_score": patient.get("risk_score"),
            "diagnosis": patient.get("diagnosis"),
            "admission_date": patient.get("admission_date")
        },
        "archetype": archetype,
        "archetype_description": ARCHETYPES[archetype]["description"],
        "mortality_risk": ARCHETYPES[archetype]["mortality"],
        "smart_logic": {
            "is_high_risk": is_high_risk,
            "risk_reason": risk_reason,
            "sepsis_stage": stage_name,
            "sepsis_stage_num": stage_num
        },
        "parameter_count": clinical_data["parameter_count"],
        "categories": categories,
        "current_parameters": current_params,
        "timepoints": clinical_data["timepoints"],
        "parameters_by_category": clinical_data["parameters_by_category"],
        "lactate_clearance": lactate_clearance,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/clinical-parameters/categories")
async def get_clinical_parameter_categories():
    """Get list of all clinical parameter categories with counts"""
    categories = get_parameter_categories()
    total_params = sum(cat["parameter_count"] for cat in categories)
    return {
        "categories": categories,
        "total_parameters": total_params
    }


@app.get("/api/patients/{patient_id}/multi-agent-analysis")
async def get_multi_agent_analysis(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Run comprehensive multi-agent analysis for a patient.
    
    Architecture:
    1. 8 Specialized Agents analyze different clinical domains in parallel:
       - Vitals Agent: HR, BP, RR, Temp, SpO2 trends
       - Hematology Agent: CBC, differential, platelets
       - Metabolic Agent: BMP/CMP, electrolytes, liver/renal function
       - Coagulation Agent: PT/INR, D-dimer, DIC assessment
       - ABG Agent: Acid-base, oxygenation, lactate kinetics
       - Inflammatory Agent: CRP, procalcitonin, cytokines
       - Cardiac Agent: Troponin, BNP, hemodynamics
       - Microbiology Agent: Cultures, organisms, susceptibilities
    
    2. Aggregation Layer synthesizes findings and identifies cross-system correlations
    
    3. RAG Deep Search retrieves relevant context from raw 120-hr data + agent results
    
    Returns comprehensive analysis with:
    - Individual agent findings with confidence scores
    - Cross-system correlations (e.g., DIC, ARDS, MODS patterns)
    - Overall assessment and sepsis trajectory
    - Mortality risk estimation
    - Prioritized recommended actions
    """
    # Get patient from database or featured patients
    patient = await get_patient_from_db(patient_id, db)
    
    if not patient:
        featured = get_featured_patients_with_history()
        patient = next((p for p in featured if p["id"] == patient_id), None)
    
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get comprehensive data first
    risk_level = patient.get("risk_level", "MODERATE")
    if risk_level == "CRITICAL":
        import random
        archetype = "refractory_shock_nonsurvivor" if random.random() < 0.3 else "septic_shock_survivor"
    elif risk_level == "HIGH":
        archetype = "septic_shock_survivor"
    elif risk_level == "MODERATE":
        import random
        archetype = "late_mods_nonsurvivor" if random.random() < 0.1 else "uncomplicated_sepsis"
    else:
        archetype = "uncomplicated_sepsis"
    
    comprehensive_data = generate_patient_clinical_data(
        patient_id=patient_id,
        archetype=archetype,
        hours=120,
        interval_hours=4
    )
    comprehensive_data["archetype"] = archetype
    comprehensive_data["archetype_description"] = ARCHETYPES[archetype]["description"]
    comprehensive_data["current_parameters"] = get_current_parameters(comprehensive_data)
    comprehensive_data["lactate_clearance"] = generate_lactate_clearance_curve(archetype, hours=72)
    
    # Prepare patient data for agents
    patient_data = {
        "id": patient.get("id"),
        "name": patient.get("name"),
        "age": patient.get("age"),
        "diagnosis": patient.get("diagnosis"),
        "risk_level": risk_level,
        "risk_score": patient.get("risk_score")
    }
    
    # Run multi-agent analysis
    analysis = await run_multi_agent_analysis(
        patient_id=patient_id,
        patient_data=patient_data,
        comprehensive_data=comprehensive_data
    )
    
    # Convert to dict for JSON response
    return {
        "patient_id": analysis.patient_id,
        "timestamp": analysis.timestamp,
        "agent_findings": [
            {
                "agent_name": f.agent_name,
                "domain": f.domain,
                "summary": f.summary,
                "issues": [
                    {
                        "id": i.id,
                        "label": i.label,
                        "severity": i.severity,
                        "evidence": i.evidence,
                        "related_parameters": i.related_parameters,
                        "clinical_significance": i.clinical_significance
                    }
                    for i in f.issues
                ],
                "trends": f.trends,
                "overall_risk": f.overall_risk,
                "confidence": f.confidence,
                "recommendations": f.recommendations
            }
            for f in analysis.agent_findings
        ],
        "cross_system_correlations": [
            {
                "id": c.id,
                "pattern_name": c.pattern_name,
                "involved_systems": c.involved_systems,
                "evidence": c.evidence,
                "clinical_interpretation": c.clinical_interpretation,
                "severity": c.severity
            }
            for c in analysis.cross_system_correlations
        ],
        "overall_assessment": analysis.overall_assessment,
        "primary_concerns": analysis.primary_concerns,
        "sepsis_trajectory": analysis.sepsis_trajectory,
        "mortality_risk": analysis.mortality_risk,
        "recommended_actions": analysis.recommended_actions,
        "confidence_score": analysis.confidence_score
    }


@app.post("/api/multi-agent/clear-cache")
async def clear_multi_agent_cache():
    """Clear the multi-agent analysis cache"""
    clear_agent_cache()
    return {"status": "success", "message": "Agent cache cleared"}


def generate_12hour_history(patient: Dict) -> Dict:
    """Generate 12-hour historical data based on current/previous values and risk level"""
    vitals_current = patient["vitals"]["current"]
    labs_current = patient["labs"]["current"]
    
    vitals_prev = patient.get("vitals", {}).get("previous")
    labs_prev = patient.get("labs", {}).get("previous")
    
    if not vitals_prev:
        vitals_prev = {
            "heart_rate": vitals_current.get("heart_rate", 70) * 0.95,
            "temperature": vitals_current.get("temperature", 37.0) * 0.99,
            "respiratory_rate": vitals_current.get("respiratory_rate", 16) * 0.95,
            "spo2": vitals_current.get("spo2", 98) * 1.01
        }
    
    if not labs_prev:
        labs_prev = {
            "wbc": labs_current.get("wbc", 8.0) * 0.9,
            "lactate": labs_current.get("lactate", 1.5) * 0.8,
            "creatinine": labs_current.get("creatinine", 1.0) * 0.95,
            "bilirubin": labs_current.get("bilirubin", 0.8) * 0.95,
            "platelets": labs_current.get("platelets", 200) * 1.05
        }
    
    history = []
    now = datetime.now()
    
    for i in range(13):
        hour_offset = 12 - i
        timestamp = (now - timedelta(hours=hour_offset)).isoformat()
        
        if patient["risk_level"] in ["CRITICAL", "HIGH"]:
            progress = i / 12.0
            hr = vitals_prev["heart_rate"] + (vitals_current.get("heart_rate", 70) - vitals_prev["heart_rate"]) * progress
            temp = vitals_prev["temperature"] + (vitals_current.get("temperature", 37.0) - vitals_prev["temperature"]) * progress
            wbc = labs_prev["wbc"] + (labs_current.get("wbc", 8.0) - labs_prev["wbc"]) * progress
            lactate = labs_prev["lactate"] + (labs_current.get("lactate", 1.5) - labs_prev["lactate"]) * progress
        else:
            progress = i / 12.0
            hr = vitals_prev["heart_rate"] + (vitals_current.get("heart_rate", 70) - vitals_prev["heart_rate"]) * progress * 0.5
            temp = vitals_prev["temperature"] + (vitals_current.get("temperature", 37.0) - vitals_prev["temperature"]) * progress * 0.3
            wbc = labs_prev["wbc"] + (labs_current.get("wbc", 8.0) - labs_prev["wbc"]) * progress * 0.4
            lactate = labs_prev["lactate"] + (labs_current.get("lactate", 1.5) - labs_prev["lactate"]) * progress * 0.2
        
        history.append({
            "timestamp": timestamp,
            "heart_rate": round(hr, 1),
            "temperature": round(temp, 1),
            "wbc": round(wbc, 1),
            "lactate": round(lactate, 1)
        })
    
    return {"history": history}

@app.get("/api/patients/{patient_id}/history")
async def get_patient_history(patient_id: str, db: AsyncSession = Depends(get_db)):
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return generate_12hour_history(patient)

def calculate_trend_features(patient: Dict, history: List[Dict]) -> Dict:
    """Calculate trend features for AI analysis"""
    if len(history) < 2:
        vitals = patient.get("vitals", {}).get("current", {})
        labs = patient.get("labs", {}).get("current", {})
        return {
            "hr_change": 0.0,
            "hr_pct_change": 0.0,
            "temp_change": 0.0,
            "temp_pct_change": 0.0,
            "wbc_change": 0.0,
            "wbc_pct_change": 0.0,
            "lactate_change": 0.0,
            "lactate_pct_change": 0.0,
            "max_hr": vitals.get("heart_rate", 70),
            "max_temp": vitals.get("temperature", 37.0),
            "max_wbc": labs.get("wbc", 8.0),
            "max_lactate": labs.get("lactate", 1.5)
        }
    
    first = history[0]
    last = history[-1]
    
    hr_change = last["heart_rate"] - first["heart_rate"]
    hr_pct = (hr_change / first["heart_rate"]) * 100 if first["heart_rate"] > 0 else 0
    
    temp_change = last["temperature"] - first["temperature"]
    temp_pct = (temp_change / first["temperature"]) * 100 if first["temperature"] > 0 else 0
    
    wbc_change = last["wbc"] - first["wbc"]
    wbc_pct = (wbc_change / first["wbc"]) * 100 if first["wbc"] > 0 else 0
    
    lactate_change = last["lactate"] - first["lactate"]
    lactate_pct = (lactate_change / first["lactate"]) * 100 if first["lactate"] > 0 else 0
    
    max_hr = max(h["heart_rate"] for h in history)
    max_temp = max(h["temperature"] for h in history)
    max_wbc = max(h["wbc"] for h in history)
    max_lactate = max(h["lactate"] for h in history)
    
    return {
        "hr_change": round(hr_change, 1),
        "hr_pct_change": round(hr_pct, 1),
        "temp_change": round(temp_change, 1),
        "temp_pct_change": round(temp_pct, 1),
        "wbc_change": round(wbc_change, 1),
        "wbc_pct_change": round(wbc_pct, 1),
        "lactate_change": round(lactate_change, 1),
        "lactate_pct_change": round(lactate_pct, 1),
        "max_hr": round(max_hr, 1),
        "max_temp": round(max_temp, 1),
        "max_wbc": round(max_wbc, 1),
        "max_lactate": round(max_lactate, 1)
    }

@app.get("/api/patients/{patient_id}/ai-analysis")
async def get_ai_analysis(patient_id: str):
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    
    system_prompt = """You are a clinical AI assistant specializing in sepsis detection and prevention. 
    Analyze the patient's 12-hour trends and current status to provide actionable clinical insights.
    
    IMPORTANT: Format your response in clean GitHub-flavored Markdown:
    - Use ### for section headers (e.g., ### Trend Interpretation)
    - Use **bold** for emphasis on key clinical terms
    - Use bullet lists (- ) for actions and findings
    - Do NOT use code fences or backticks
    - Keep paragraphs concise and scannable"""
    
    user_prompt = f"""Analyze this patient's 12-hour trends:

Patient: {patient['name']}, {patient['age']}y {patient['gender']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {patient['risk_score']}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4

12-Hour Trends:
- Heart Rate: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%), Peak: {trends['max_hr']} bpm
- Temperature: {trends['temp_change']:+.1f}°C ({trends['temp_pct_change']:+.1f}%), Peak: {trends['max_temp']}°C
- WBC: {trends['wbc_change']:+.1f} K/µL ({trends['wbc_pct_change']:+.1f}%), Peak: {trends['max_wbc']} K/µL
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%), Peak: {trends['max_lactate']} mmol/L

Current Values:
- HR: {patient['vitals']['current']['heart_rate']} bpm, Temp: {patient['vitals']['current']['temperature']}°C
- WBC: {patient['labs']['current']['wbc']} K/µL, Lactate: {patient['labs']['current']['lactate']} mmol/L

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Provide a concise clinical analysis with these sections:
### Trend Interpretation
### Key Warning Signs
### Recommended Actions"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=True,
            temperature=0.7,
            max_tokens=800
        )
        
        async def generate():
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients/{patient_id}/ai-insights")
async def get_ai_insights(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Generate structured AI insights as alert cards for better readability"""
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    
    system_prompt = """You are a clinical AI assistant specializing in sepsis detection and prevention.
    Generate structured clinical insights as discrete alert cards.
    
    Return ONLY valid JSON matching this exact schema (no markdown, no prose):
    {
      "cards": [
        {
          "severity": "critical|warning|info|success",
          "category": "deterioration|labs|hemodynamics|sepsis|monitoring|other",
          "title": "Brief alert title (5-8 words)",
          "description": "One sentence clinical detail with specific values",
          "agent": "Agent name",
          "icon": "alert-triangle|activity|beaker|trending-up|stethoscope|thermometer"
        }
      ]
    }
    
    Guidelines:
    - Generate 3-5 cards max, prioritizing most critical findings
    - severity: "critical" for deteriorating vitals/SIRS 4/4, "warning" for concerning trends, "info" for stable monitoring, "success" for improvements
    - Keep titles concise and actionable
    - Include specific values in descriptions (e.g., "BP dropping 140→110, HR increasing 95→125")
    - Use appropriate agent names (Clinical Deterioration Agent, Sepsis Monitoring Agent, Lab Analysis Agent, etc.)"""
    
    user_prompt = f"""Analyze this patient and generate alert cards:

Patient: {patient['name']}, {patient['age']}y {patient['gender']} in {patient['room']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {patient['risk_score']}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4

12-Hour Trends:
- Heart Rate: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%), Peak: {trends['max_hr']} bpm
- Temperature: {trends['temp_change']:+.1f}°C ({trends['temp_pct_change']:+.1f}%), Peak: {trends['max_temp']}°C
- WBC: {trends['wbc_change']:+.1f} K/µL ({trends['wbc_pct_change']:+.1f}%), Peak: {trends['max_wbc']} K/µL
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%), Peak: {trends['max_lactate']} mmol/L

Current Values:
- HR: {patient['vitals']['current']['heart_rate']} bpm, Temp: {patient['vitals']['current']['temperature']}°C, RR: {patient['vitals']['current']['respiratory_rate']}, BP: {patient['vitals']['current']['blood_pressure']}
- WBC: {patient['labs']['current']['wbc']} K/µL, Lactate: {patient['labs']['current']['lactate']} mmol/L

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Generate alert cards as JSON."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        insights = json.loads(content)
        
        now = datetime.utcnow()
        for i, card in enumerate(insights.get("cards", [])):
            card["ts"] = (now - timedelta(minutes=i*2)).isoformat() + "Z"
            card["id"] = f"{patient_id}-{i}"
        
        return {
            "patient_id": patient_id,
            "generated_at": now.isoformat() + "Z",
            **insights
        }
    except json.JSONDecodeError as e:
        return {
            "patient_id": patient_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cards": [{
                "id": f"{patient_id}-error",
                "severity": "warning",
                "category": "other",
                "title": "Analysis Unavailable",
                "description": "Unable to generate structured insights. Please try again.",
                "agent": "System",
                "icon": "alert-triangle",
                "ts": datetime.utcnow().isoformat() + "Z"
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients/{patient_id}/horizon-forecast")
async def get_horizon_forecast(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Predictive Horizon Forecasting: 1h/3h/6h sepsis risk predictions with personalized baselines using Azure OpenAI"""
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    ground_truth = patient.get('ground_truth', {})
    
    system_prompt = """You are a predictive analytics AI specializing in sepsis risk forecasting.
    Analyze patient trends and predict sepsis risk at 1-hour, 3-hour, and 6-hour horizons.
    
    Return ONLY valid JSON matching this exact schema:
    {
      "current_risk": 0-100,
      "forecasts": [
        {"horizon": "1h", "risk": 0-100, "confidence": 0.0-1.0},
        {"horizon": "3h", "risk": 0-100, "confidence": 0.0-1.0},
        {"horizon": "6h", "risk": 0-100, "confidence": 0.0-1.0}
      ],
      "time_to_breach": "X.Xh" or null,
      "trend_direction": "rising|stable|falling",
      "clinical_reasoning": "Brief explanation of forecast rationale"
    }
    
    Guidelines:
    - Consider velocity of vital signs and lab trends
    - Factor in SIRS criteria progression
    - Account for current interventions and devices
    - Confidence decreases with longer horizons
    - time_to_breach: hours until risk exceeds 70 (if applicable)
    - Be conservative but realistic based on clinical trajectory"""
    
    user_prompt = f"""Forecast sepsis risk for this patient:

Patient: {patient['name']}, {patient['age']}y {patient['gender']} in {patient['room']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {patient['risk_score']}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4

12-Hour Trends:
- Heart Rate: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%), Current: {patient['vitals']['current']['heart_rate']} bpm, Peak: {trends['max_hr']} bpm
- Temperature: {trends['temp_change']:+.1f}°C ({trends['temp_pct_change']:+.1f}%), Current: {patient['vitals']['current']['temperature']}°C, Peak: {trends['max_temp']}°C
- WBC: {trends['wbc_change']:+.1f} K/µL ({trends['wbc_pct_change']:+.1f}%), Current: {patient['labs']['current']['wbc']} K/µL, Peak: {trends['max_wbc']} K/µL
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%), Current: {patient['labs']['current']['lactate']} mmol/L, Peak: {trends['max_lactate']} mmol/L

Current Vitals:
- HR: {patient['vitals']['current']['heart_rate']} bpm, RR: {patient['vitals']['current']['respiratory_rate']}, BP: {patient['vitals']['current']['blood_pressure']}, SpO2: {patient['vitals']['current']['spo2']}%
- Temp: {patient['vitals']['current']['temperature']}°C

Current Labs:
- WBC: {patient['labs']['current']['wbc']} K/µL, Lactate: {patient['labs']['current']['lactate']} mmol/L

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Predict 1h/3h/6h sepsis risk with confidence levels and time-to-breach if applicable."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        forecast_data = json.loads(content)
        
        return {
            "patient_id": patient_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            **forecast_data
        }
    except json.JSONDecodeError as e:
        baseline_risk = patient['risk_score']
        return {
            "patient_id": patient_id,
            "current_risk": baseline_risk,
            "forecasts": [
                {"horizon": "1h", "risk": baseline_risk, "confidence": 0.5},
                {"horizon": "3h", "risk": baseline_risk, "confidence": 0.4},
                {"horizon": "6h", "risk": baseline_risk, "confidence": 0.3}
            ],
            "time_to_breach": None,
            "trend_direction": "stable",
            "clinical_reasoning": "Unable to generate forecast. Using baseline risk.",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients/{patient_id}/next-best-action")
async def get_next_best_action(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Next Best Action: Concrete recommendations with expected value and confidence using Azure OpenAI"""
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    ground_truth = patient.get('ground_truth', {})
    
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    bp_parts = vitals['blood_pressure'].split('/')
    map_pressure = (int(bp_parts[0]) + 2 * int(bp_parts[1])) / 3
    
    system_prompt = """You are a clinical decision support AI specializing in sepsis management.
    Generate prioritized clinical recommendations with expected benefit and confidence levels.
    
    Return ONLY valid JSON matching this exact schema:
    {
      "actions": [
        {
          "action_type": "lab|intervention|monitoring|escalation",
          "title": "Brief action title (5-8 words)",
          "rationale": "Clinical reasoning with specific values",
          "expected_benefit": "high|medium|low",
          "confidence": 0.0-1.0,
          "urgency": "immediate|soon|routine"
        }
      ]
    }
    
    Guidelines:
    - Generate 3-5 prioritized actions based on clinical urgency
    - action_type: lab (diagnostics), intervention (treatment), monitoring (observation), escalation (consult/transfer)
    - expected_benefit: high (likely to prevent deterioration), medium (supportive), low (precautionary)
    - confidence: based on evidence strength and clinical certainty
    - urgency: immediate (<15 min), soon (<1 hour), routine (next rounds)
    - Include specific values in rationale (e.g., "Lactate 4.2 mmol/L, trending up +1.1")
    - Prioritize sepsis bundle components for high-risk patients"""
    
    user_prompt = f"""Generate next best actions for this patient:

Patient: {patient['name']}, {patient['age']}y {patient['gender']} in {patient['room']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {patient['risk_score']}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4

12-Hour Trends:
- Heart Rate: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%), Current: {vitals['heart_rate']} bpm
- Temperature: {trends['temp_change']:+.1f}°C ({trends['temp_pct_change']:+.1f}%), Current: {vitals['temperature']}°C
- WBC: {trends['wbc_change']:+.1f} K/µL ({trends['wbc_pct_change']:+.1f}%), Current: {labs['wbc']} K/µL
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%), Current: {labs['lactate']} mmol/L

Current Vitals:
- HR: {vitals['heart_rate']} bpm, RR: {vitals['respiratory_rate']}, BP: {vitals['blood_pressure']} (MAP {map_pressure:.0f} mmHg), SpO2: {vitals['spo2']}%
- Temp: {vitals['temperature']}°C

Current Labs:
- WBC: {labs['wbc']} K/µL, Lactate: {labs['lactate']} mmol/L

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Generate 3-5 prioritized clinical actions with rationale, expected benefit, confidence, and urgency."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        action_data = json.loads(content)
        
        return {
            "patient_id": patient_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            **action_data
        }
    except json.JSONDecodeError as e:
        return {
            "patient_id": patient_id,
            "actions": [{
                "action_type": "monitoring",
                "title": "Continue Current Management",
                "rationale": "Unable to generate specific recommendations. Continue monitoring.",
                "expected_benefit": "medium",
                "confidence": 0.5,
                "urgency": "routine"
            }],
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients/{patient_id}/sepsis-bundle")
async def get_sepsis_bundle(patient_id: str, db: AsyncSession = Depends(get_db)):
    """1-Hour Sepsis Bundle Autopilot: Live timers, checkboxes, escalation using Azure OpenAI"""
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    ground_truth = patient.get('ground_truth', {})
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    
    bundle_active = patient['risk_level'] in ['CRITICAL', 'HIGH'] or ground_truth.get('sepsis_confirmed')
    
    if not bundle_active:
        return {
            "patient_id": patient_id,
            "bundle_active": False,
            "message": "Sepsis bundle not activated for this patient",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    onset_time = ground_truth.get('sepsis_onset_time')
    if onset_time:
        bundle_start = datetime.fromisoformat(onset_time.replace('Z', ''))
    else:
        bundle_start = datetime.utcnow() - timedelta(minutes=30)
    
    elapsed_minutes = (datetime.utcnow() - bundle_start).total_seconds() / 60
    remaining_minutes = max(0, 60 - elapsed_minutes)
    
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    
    system_prompt = """You are a sepsis bundle orchestration AI.
    Analyze the patient's current status and generate intelligent task tracking for the 1-hour sepsis bundle.
    
    Return ONLY valid JSON matching this exact schema:
    {
      "tasks": [
        {
          "id": "lactate|cultures|antibiotics|fluids|reassess",
          "title": "Task title",
          "completed": true|false,
          "blocked": true|false,
          "blocker_reason": "Reason if blocked" or null,
          "priority": "critical|high|medium"
        }
      ],
      "escalation_needed": true|false,
      "escalation_message": "Message if escalation needed" or null,
      "ai_recommendations": "Brief guidance on bundle completion"
    }
    
    Guidelines:
    - Assess completion status based on elapsed time and clinical context
    - Identify blockers (e.g., waiting for cultures before antibiotics)
    - Set priority based on clinical urgency and time remaining
    - Recommend escalation if bundle at risk of not completing in 60 minutes
    - Consider patient-specific factors (allergies, contraindications)"""
    
    user_prompt = f"""Orchestrate sepsis bundle for this patient:

Patient: {patient['name']}, {patient['age']}y {patient['gender']} in {patient['room']}
Diagnosis: {patient['diagnosis']}
Risk Level: {patient['risk_level']}
SIRS Criteria: {patient['sirs_criteria']}/4

Bundle Status:
- Started: {elapsed_minutes:.1f} minutes ago
- Remaining: {remaining_minutes:.1f} minutes

Current Vitals:
- HR: {vitals['heart_rate']} bpm, RR: {vitals['respiratory_rate']}, BP: {vitals['blood_pressure']}, SpO2: {vitals['spo2']}%
- Temp: {vitals['temperature']}°C

Current Labs:
- WBC: {labs['wbc']} K/µL, Lactate: {labs['lactate']} mmol/L

12-Hour Trends:
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%)
- HR: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%)

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Generate intelligent task tracking for the 5 sepsis bundle components:
1. Measure Lactate
2. Obtain Blood Cultures (2 sets)
3. Administer Broad-Spectrum Antibiotics
4. 30 mL/kg Crystalloid Bolus
5. Reassess Hemodynamics

Consider elapsed time, clinical status, and potential blockers."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        bundle_data = json.loads(content)
        
        tasks = bundle_data.get('tasks', [])
        completed_count = sum(1 for t in tasks if t.get('completed'))
        blocked_count = sum(1 for t in tasks if t.get('blocked') and not t.get('completed'))
        
        return {
            "patient_id": patient_id,
            "bundle_active": True,
            "bundle_start": bundle_start.isoformat() + "Z",
            "elapsed_minutes": round(elapsed_minutes, 1),
            "remaining_minutes": round(remaining_minutes, 1),
            "tasks": tasks,
            "completed_count": completed_count,
            "total_count": len(tasks),
            "blocked_count": blocked_count,
            "escalation_needed": bundle_data.get('escalation_needed', False),
            "escalation_message": bundle_data.get('escalation_message'),
            "ai_recommendations": bundle_data.get('ai_recommendations'),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except json.JSONDecodeError as e:
        default_tasks = [
            {"id": "lactate", "title": "Measure Lactate", "completed": elapsed_minutes > 10, "blocked": False, "blocker_reason": None, "priority": "critical"},
            {"id": "cultures", "title": "Obtain Blood Cultures (2 sets)", "completed": elapsed_minutes > 15, "blocked": False, "blocker_reason": None, "priority": "critical"},
            {"id": "antibiotics", "title": "Administer Broad-Spectrum Antibiotics", "completed": elapsed_minutes > 45, "blocked": elapsed_minutes < 15, "blocker_reason": "Waiting for blood cultures" if elapsed_minutes < 15 else None, "priority": "critical"},
            {"id": "fluids", "title": "30 mL/kg Crystalloid Bolus", "completed": elapsed_minutes > 35, "blocked": False, "blocker_reason": None, "priority": "high"},
            {"id": "reassess", "title": "Reassess Hemodynamics", "completed": elapsed_minutes > 55, "blocked": elapsed_minutes < 35, "blocker_reason": "Waiting for fluid bolus" if elapsed_minutes < 35 else None, "priority": "medium"}
        ]
        completed_count = sum(1 for t in default_tasks if t['completed'])
        escalation_needed = remaining_minutes < 15 and completed_count < len(default_tasks)
        
        return {
            "patient_id": patient_id,
            "bundle_active": True,
            "bundle_start": bundle_start.isoformat() + "Z",
            "elapsed_minutes": round(elapsed_minutes, 1),
            "remaining_minutes": round(remaining_minutes, 1),
            "tasks": default_tasks,
            "completed_count": completed_count,
            "total_count": len(default_tasks),
            "blocked_count": sum(1 for t in default_tasks if t['blocked'] and not t['completed']),
            "escalation_needed": escalation_needed,
            "escalation_message": "Bundle completion at risk" if escalation_needed else None,
            "ai_recommendations": "Unable to generate AI recommendations. Using default task tracking.",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patients/{patient_id}/what-if")
async def what_if_simulator(patient_id: str, intervention: Dict[str, Any]):
    """What-If Simulator: Predict impact of interventions on risk trajectory using Azure OpenAI"""
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    ground_truth = patient.get('ground_truth', {})
    
    current_risk = patient['risk_score']
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    current_sofa = ground_truth.get('sofa_score', 0)
    
    bp_parts = vitals['blood_pressure'].split('/')
    map_pressure = (int(bp_parts[0]) + 2 * int(bp_parts[1])) / 3
    
    system_prompt = """You are a predictive simulation AI for clinical interventions.
    Predict the physiological and clinical impact of proposed interventions on a septic patient.
    
    Return ONLY valid JSON matching this exact schema:
    {
      "predicted_state": {
        "risk_score": 0-100,
        "heart_rate": number,
        "blood_pressure": "systolic/diastolic",
        "spo2": 0-100,
        "lactate": number,
        "sofa_score": 0-24
      },
      "effects": [
        "Description of effect 1",
        "Description of effect 2"
      ],
      "risk_reduction": number,
      "confidence": 0.0-1.0,
      "clinical_reasoning": "Brief explanation of predictions",
      "timeframe": "Expected timeframe for effects (e.g., '1-2 hours', '4-6 hours')"
    }
    
    Guidelines:
    - Predict realistic physiological responses based on intervention type and dose
    - Consider patient's current state, trends, and baseline physiology
    - Account for synergistic effects of multiple interventions
    - Provide confidence based on evidence strength and patient variability
    - Include timeframe for when effects are expected to manifest
    - Be conservative but evidence-based in predictions"""
    
    intervention_desc = []
    if intervention.get('fluids_ml'):
        intervention_desc.append(f"IV crystalloid bolus: {intervention['fluids_ml']} mL")
    if intervention.get('oxygen_increase'):
        intervention_desc.append(f"Increase O2 by {intervention['oxygen_increase']} L/min")
    if intervention.get('antibiotics_given'):
        intervention_desc.append("Administer broad-spectrum antibiotics")
    if intervention.get('vasopressors_started'):
        intervention_desc.append("Initiate vasopressor support")
    
    user_prompt = f"""Predict intervention effects for this patient:

Patient: {patient['name']}, {patient['age']}y {patient['gender']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {current_risk}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4
Current SOFA Score: {current_sofa}

Current State:
- HR: {vitals['heart_rate']} bpm, RR: {vitals['respiratory_rate']}, BP: {vitals['blood_pressure']} (MAP {map_pressure:.0f} mmHg)
- SpO2: {vitals['spo2']}%, Temp: {vitals['temperature']}°C
- WBC: {labs['wbc']} K/µL, Lactate: {labs['lactate']} mmol/L

12-Hour Trends:
- HR: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%)
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%)

Proposed Interventions:
{chr(10).join('- ' + desc for desc in intervention_desc) if intervention_desc else '- No interventions specified'}

Predict the physiological effects, risk reduction, SOFA score change, and confidence level."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        prediction_data = json.loads(content)
        
        predicted_state = prediction_data.get('predicted_state', {})
        
        return {
            "patient_id": patient_id,
            "intervention": intervention,
            "current_state": {
                "risk_score": current_risk,
                "heart_rate": vitals['heart_rate'],
                "blood_pressure": vitals['blood_pressure'],
                "spo2": vitals['spo2'],
                "lactate": labs['lactate'],
                "sofa_score": current_sofa
            },
            "predicted_state": predicted_state,
            "effects": prediction_data.get('effects', []),
            "risk_reduction": prediction_data.get('risk_reduction', 0),
            "confidence": prediction_data.get('confidence', 0.5),
            "clinical_reasoning": prediction_data.get('clinical_reasoning', ''),
            "timeframe": prediction_data.get('timeframe', ''),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except json.JSONDecodeError as e:
        predicted_risk = current_risk
        predicted_vitals = vitals.copy()
        predicted_labs = labs.copy()
        effects = []
        
        if intervention.get('fluids_ml'):
            fluid_amount = intervention['fluids_ml']
            sbp = int(bp_parts[0])
            sbp_increase = min(20, fluid_amount / 150)
            predicted_vitals['blood_pressure'] = f"{sbp + int(sbp_increase)}/{bp_parts[1]}"
            predicted_risk -= sbp_increase * 0.5
            effects.append(f"BP increase: {sbp}→{sbp + int(sbp_increase)} mmHg")
        
        if intervention.get('oxygen_increase'):
            spo2_increase = min(5, intervention['oxygen_increase'] * 2)
            predicted_vitals['spo2'] = min(100, vitals['spo2'] + spo2_increase)
            predicted_risk -= spo2_increase * 0.3
            effects.append(f"SpO2 increase: {vitals['spo2']}→{predicted_vitals['spo2']}%")
        
        if intervention.get('antibiotics_given'):
            predicted_risk -= 10
            predicted_labs['lactate'] = max(0.5, labs['lactate'] - 0.5)
            effects.append("Antibiotics: Expected risk reduction over 6h")
        
        predicted_risk = max(0, min(100, predicted_risk))
        
        return {
            "patient_id": patient_id,
            "intervention": intervention,
            "current_state": {
                "risk_score": current_risk,
                "heart_rate": vitals['heart_rate'],
                "blood_pressure": vitals['blood_pressure'],
                "spo2": vitals['spo2'],
                "lactate": labs['lactate'],
                "sofa_score": current_sofa
            },
            "predicted_state": {
                "risk_score": round(predicted_risk, 1),
                "heart_rate": vitals['heart_rate'],
                "blood_pressure": predicted_vitals.get('blood_pressure', vitals['blood_pressure']),
                "spo2": predicted_vitals.get('spo2', vitals['spo2']),
                "lactate": predicted_labs.get('lactate', labs['lactate']),
                "sofa_score": max(0, current_sofa - 1) if intervention.get('fluids_ml') or intervention.get('oxygen_increase') else current_sofa
            },
            "effects": effects,
            "risk_reduction": round(current_risk - predicted_risk, 1),
            "confidence": 0.5,
            "clinical_reasoning": "Unable to generate AI prediction. Using simplified model.",
            "timeframe": "1-6 hours",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/patients/{patient_id}/what-if/monte-carlo")
async def monte_carlo_what_if(patient_id: str, params: Dict[str, Any] = None, db: AsyncSession = Depends(get_db)):
    """
    Monte Carlo What-If Simulator: Generate top 3 treatment pathways with 100x simulation
    Auto-recommends fluids, vasopressors, antibiotics based on patient state
    """
    from app.monte_carlo import (
        generate_candidate_treatments,
        run_monte_carlo,
        rank_pathways
    )
    
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if params is None:
        params = {}
    samples = params.get("samples", 500)  # Default to 500 for high-fidelity results
    seed = params.get("seed", None)
    
    try:
        candidates = generate_candidate_treatments(patient)
        
        monte_carlo_results = []
        for candidate in candidates:
            result = run_monte_carlo(patient, candidate, samples=samples, seed=seed)
            
            result["treatment_details"] = {
                "fluids": {
                    "volume_ml": candidate.fluids_ml,
                    "type": candidate.fluids_type.value,
                    "rate_ml_hr": candidate.fluids_rate_ml_hr
                },
                "vasopressor": {
                    "type": candidate.vasopressor.value,
                    "dose_mcg_kg_min": candidate.vasopressor_dose_mcg_kg_min,
                    "timing_min": candidate.vasopressor_timing_min
                },
                "antibiotics": {
                    "coverage": candidate.antibiotics.value,
                    "timing_min": candidate.antibiotics_timing_min
                },
                "reassessment_intervals_min": candidate.reassessment_intervals_min
            }
            
            monte_carlo_results.append(result)
        
        ranked_pathways = rank_pathways(monte_carlo_results)
        
        top_3 = ranked_pathways[:3]
        
        for pathway in top_3:
            rationale = await _generate_pathway_rationale(patient, pathway)
            pathway["clinical_rationale"] = rationale
        
        return {
            "patient_id": patient_id,
            "patient_name": patient.get("name"),
            "risk_level": patient.get("risk_level"),
            "risk_score": patient.get("risk_score"),
            "simulation_params": {
                "samples_per_pathway": samples,
                "total_simulations": len(candidates) * samples,
                "candidates_evaluated": len(candidates)
            },
            "top_3_pathways": top_3,
            "all_pathways": ranked_pathways,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monte Carlo simulation failed: {str(e)}")

async def _generate_pathway_rationale(patient: Dict[str, Any], pathway: Dict[str, Any]) -> str:
    """Generate clinical rationale for a treatment pathway using LLM"""
    try:
        vitals = patient.get('vitals', {}).get('current', {})
        labs = patient.get('labs', {}).get('current', {})
        
        prompt = f"""Provide a brief clinical rationale (2-3 sentences) for this sepsis treatment pathway:

Patient: {patient.get('name')}, {patient.get('age')}y, Risk: {patient.get('risk_level')} ({patient.get('risk_score')}/100)
Current: BP {vitals.get('blood_pressure')}, HR {vitals.get('heart_rate')}, Lactate {labs.get('lactate')}

Pathway: {pathway['candidate_name']}
Treatment:
- Fluids: {pathway['treatment_details']['fluids']['volume_ml']}mL {pathway['treatment_details']['fluids']['type']} at {pathway['treatment_details']['fluids']['rate_ml_hr']}mL/hr
- Vasopressor: {pathway['treatment_details']['vasopressor']['type']} at {pathway['treatment_details']['vasopressor']['dose_mcg_kg_min']} mcg/kg/min (start at {pathway['treatment_details']['vasopressor']['timing_min']}min)
- Antibiotics: {pathway['treatment_details']['antibiotics']['coverage']} (start at {pathway['treatment_details']['antibiotics']['timing_min']}min)

Expected Outcomes (from {pathway['samples']} simulations):
- Survival: {pathway['expected_outcomes']['survival_prob']['mean']:.1%} (±{pathway['expected_outcomes']['survival_prob']['std']:.1%})
- Time to Stability: {pathway['expected_outcomes']['time_to_stability_hr']['mean']:.1f}h (±{pathway['expected_outcomes']['time_to_stability_hr']['std']:.1f}h)
- Organ Preservation: {pathway['expected_outcomes']['organ_preservation_score']['mean']:.0f}/100

Explain why this pathway is appropriate for this patient's condition."""

        llm_client = get_llm_client()
        response = await llm_client.get_completion_text(
            messages=[
                {"role": "system", "content": "You are a critical care physician explaining treatment decisions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=200,
            timeout=30.0
        )
        
        return response.strip()
    
    except Exception as e:
        return f"This pathway balances {pathway['candidate_name'].lower()} approach with expected outcomes."

@app.post("/api/patients/{patient_id}/what-if/evaluate")
async def evaluate_custom_pathway(patient_id: str, params: Dict[str, Any]):
    """
    Evaluate custom treatment parameters with quick Monte Carlo preview (30-50 simulations)
    Used for "Preview with my changes" button in What-If Simulator
    """
    from app.monte_carlo import (
        Candidate,
        FluidsType,
        VasopressorType,
        AntibioticCoverage,
        run_monte_carlo
    )
    
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    fluids_ml = params.get("fluids_ml", 0)
    antibiotics = params.get("antibiotics", False)
    vasopressors = params.get("vasopressors", False)
    samples = params.get("samples", 30)  # Quick preview with fewer samples
    
    try:
        candidate = Candidate(
            name="Custom Parameters",
            fluids_ml=fluids_ml,
            fluids_type=FluidsType.CRYSTALLOID,
            fluids_rate_ml_hr=min(fluids_ml, 1000),  # Cap at 1000 mL/hr
            vasopressor=VasopressorType.NOREPINEPHRINE if vasopressors else VasopressorType.NONE,
            vasopressor_dose_mcg_kg_min=0.05 if vasopressors else 0.0,
            vasopressor_timing_min=30 if vasopressors else 0,
            antibiotics=AntibioticCoverage.BROAD if antibiotics else AntibioticCoverage.NONE,
            antibiotics_timing_min=45 if antibiotics else 0,
            reassessment_intervals_min=[30, 60, 120, 240]
        )
        
        result = run_monte_carlo(patient, candidate, samples=samples, seed=None)
        
        outcomes = result.get("expected_outcomes", {})
        
        return {
            "patient_id": patient_id,
            "custom_parameters": {
                "fluids_ml": fluids_ml,
                "antibiotics": antibiotics,
                "vasopressors": vasopressors
            },
            "survival_probability": outcomes.get("survival_prob", {}).get("mean", 0.0),
            "time_to_stability_hours": outcomes.get("time_to_stability_hr", {}).get("mean", 0.0),
            "organ_preservation_score": outcomes.get("organ_preservation_score", {}).get("mean", 0.0),
            "confidence_intervals": {
                "survival_ci": [
                    outcomes.get("survival_prob", {}).get("ci_lower", 0.0),
                    outcomes.get("survival_prob", {}).get("ci_upper", 0.0)
                ],
                "stability_ci": [
                    outcomes.get("time_to_stability_hr", {}).get("ci_lower", 0.0),
                    outcomes.get("time_to_stability_hr", {}).get("ci_upper", 0.0)
                ],
                "organ_ci": [
                    outcomes.get("organ_preservation_score", {}).get("ci_lower", 0.0),
                    outcomes.get("organ_preservation_score", {}).get("ci_upper", 0.0)
                ]
            },
            "samples": samples,
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom pathway evaluation failed: {str(e)}")

@app.get("/api/rl/results")
async def get_rl_results():
    """Get RL batch evaluation results with learning curves and insights"""
    results_path = Path(__file__).parent / "data" / "rl_batch_results.json"
    
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="RL results not found. Run batch evaluation first.")
    
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        # Transform learning_curves from dict of arrays to array of objects for frontend
        lc = results.get("learning_curves", {})
        if isinstance(lc, dict) and "batches" in lc:
            transformed_curves = []
            batches = lc.get("batches", [])
            rl_win_rates = lc.get("rl_win_rate", [])
            baseline_win_rates = lc.get("baseline_win_rate", [])
            rl_utilities = lc.get("rl_utility", [])
            baseline_utilities = lc.get("baseline_utility", [])
            rl_regrets = lc.get("rl_regret", [])
            
            for i, batch_id in enumerate(batches):
                transformed_curves.append({
                    "batch_id": batch_id,
                    "rl_win_rate": rl_win_rates[i] * 100 if i < len(rl_win_rates) else 0,
                    "baseline_win_rate": baseline_win_rates[i] * 100 if i < len(baseline_win_rates) else 0,
                    "rl_utility": rl_utilities[i] if i < len(rl_utilities) else 0,
                    "baseline_utility": baseline_utilities[i] if i < len(baseline_utilities) else 0,
                    "rl_regret": rl_regrets[i] if i < len(rl_regrets) else 0
                })
            results["learning_curves"] = transformed_curves
        
        # Transform insights_report to insights for frontend
        if "insights_report" in results and "insights" not in results:
            results["insights"] = results["insights_report"]
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load RL results: {str(e)}")

@app.get("/api/rl/scenarios")
async def get_rl_scenarios(limit: int = 100, offset: int = 0, risk_level: Optional[str] = None):
    """Get paginated RL scenario results from comprehensive table"""
    csv_path = Path(__file__).parent / "data" / "comprehensive_table.csv"
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Scenario data not found. Run batch evaluation first.")
    
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        if risk_level:
            df = df[df['risk_level'] == risk_level.upper()]
        
        total = len(df)
        df_page = df.iloc[offset:offset+limit]
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "scenarios": df_page.to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios: {str(e)}")

@app.post("/api/evaluation/run")
async def run_evaluation(
    patient_ids: Optional[List[str]] = None,
    samples: int = 500,
    seed: Optional[int] = None,
    use_cache: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Run batch Monte Carlo evaluation across patients with caching"""
    try:
        result = await run_batch_evaluation(patient_ids, samples, seed, db, use_cache)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@app.get("/api/evaluation/status/{run_id}")
async def evaluation_status(run_id: int, db: AsyncSession = Depends(get_db)):
    """Get status of an evaluation run"""
    result = await get_evaluation_run_status(run_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.get("/api/evaluation/cached/{patient_id}")
async def get_cached_eval(
    patient_id: str,
    samples: int = 500,
    seed: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get cached evaluation result for a patient"""
    result = await get_cached_evaluation(patient_id, samples, seed, db)
    if not result:
        raise HTTPException(status_code=404, detail="No cached evaluation found")
    return result

@app.get("/api/reports/outcomes")
async def get_outcomes_report(
    window: str = "weekly",
    risk_level: Optional[str] = None,
    use_synthetic: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get trending outcomes data for Report tab (uses synthetic data by default for demo)"""
    if use_synthetic:
        weeks = 12 if window == "weekly" else 6
        result = generate_synthetic_outcomes(weeks=weeks)
        return result
    else:
        cohort_filter = {"risk_level": risk_level} if risk_level else None
        result = await get_trending_outcomes(window, cohort_filter, db)
        return result

@app.get("/api/reports/pathway-adoption")
async def get_pathway_report(
    window: str = "weekly",
    use_synthetic: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get pathway adoption trends over time (uses synthetic data by default for demo)"""
    if use_synthetic:
        weeks = 12 if window == "weekly" else 6
        result = generate_synthetic_pathway_adoption(weeks=weeks)
        return result
    else:
        result = await get_pathway_adoption(window, db)
        return result

@app.get("/api/validation-reports", response_model=None)
async def get_validation_reports(db: AsyncSession = Depends(get_db)):
    """Get comprehensive validation reports for Kaggle and Synthetic datasets"""
    try:
        import numpy as np
        from sklearn.metrics import roc_auc_score, average_precision_score
        
        result = await db.execute(
            select(DimPatient.risk_score, DimPatient.cohort_tags, DimPatient.id)
        )
        data = result.all()
        
        kaggle_data = []
        
        for row in data:
            cohort_tags = json.loads(row.cohort_tags) if row.cohort_tags else []
            
            sepsis_label = 0
            for tag in cohort_tags:
                if tag.startswith('sepsis_'):
                    sepsis_label = int(tag.split('_')[1])
                    break
            
            is_kaggle = 'kaggle' in cohort_tags
            
            if is_kaggle:
                kaggle_data.append({
                    'risk_score': row.risk_score,
                    'sepsis_label': sepsis_label
                })
        
        reports = {}
        
        if len(kaggle_data) >= 10:
            y_true = np.array([d['sepsis_label'] for d in kaggle_data])
            y_scores = np.array([d['risk_score'] for d in kaggle_data])
            
            thresholds = [16, 20, 25, 30, 35, 40, 45, 50]
            threshold_metrics = []
            
            for threshold in thresholds:
                y_pred = (y_scores >= threshold).astype(int)
                
                tp = ((y_pred == 1) & (y_true == 1)).sum()
                fp = ((y_pred == 1) & (y_true == 0)).sum()
                fn = ((y_pred == 0) & (y_true == 1)).sum()
                tn = ((y_pred == 0) & (y_true == 0)).sum()
                
                sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
                specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
                ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
                npv = tn / (tn + fn) if (tn + fn) > 0 else 0
                f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
                accuracy = (tp + tn) / len(y_true)
                
                threshold_metrics.append({
                    'threshold': threshold,
                    'tp': int(tp),
                    'fp': int(fp),
                    'fn': int(fn),
                    'tn': int(tn),
                    'sensitivity': float(sensitivity),
                    'specificity': float(specificity),
                    'ppv': float(ppv),
                    'npv': float(npv),
                    'f1': float(f1),
                    'accuracy': float(accuracy)
                })
            
            try:
                auroc = roc_auc_score(y_true, y_scores / 100.0)
                auprc = average_precision_score(y_true, y_scores / 100.0)
            except:
                auroc = 0.0
                auprc = 0.0
            
            best_f1_idx = max(range(len(threshold_metrics)), key=lambda i: threshold_metrics[i]['f1'])
            optimal_threshold = threshold_metrics[best_f1_idx]
            
            reports['kaggle'] = {
                'dataset': 'kaggle',
                'n_patients': len(kaggle_data),
                'n_sepsis': int(y_true.sum()),
                'n_non_sepsis': int((1 - y_true).sum()),
                'prevalence': float(y_true.mean()),
                'auroc': float(auroc),
                'auprc': float(auprc),
                'threshold_metrics': threshold_metrics,
                'optimal_threshold': optimal_threshold
            }
        else:
            reports['kaggle'] = {
                "error": "Insufficient data",
                "n_patients": len(kaggle_data)
            }
        
        reports['synthetic'] = {
            "error": "No synthetic data with labels",
            "n_patients": 0
        }
        
        return reports
    except Exception as e:
        print(f"Error generating validation reports: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patients/{patient_id}/early-warning")
async def get_early_warning(patient_id: str, db: AsyncSession = Depends(get_db)):
    """Multi-Agent Early Warning System: 6 specialized agents analyzing patient deterioration"""
    patient = await get_patient_from_db(patient_id, db)
    if not patient:
        patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    ground_truth = patient.get('ground_truth', {})
    
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    bp_parts = vitals['blood_pressure'].split('/')
    map_pressure = (int(bp_parts[0]) + 2 * int(bp_parts[1])) / 3
    
    system_prompt = """You are a multi-agent early warning system for sepsis detection.
    Analyze the patient from 6 specialized perspectives and generate a consensus early warning assessment.
    
    Return ONLY valid JSON matching this exact schema:
    {
      "overall_ews_score": 0-100,
      "severity": "critical|warning|info|stable",
      "trend": "rising|stable|falling",
      "time_to_breach": "X.Xh" or null,
      "agent_evidence": [
        {
          "agent": "Hemodynamics Agent|Infection Agent|Metabolic Agent|Respiratory Agent|Data Quality Agent|Orchestrator",
          "score": 0-100,
          "severity": "critical|warning|info|stable",
          "confidence": 0.0-1.0,
          "reasons": ["Reason 1", "Reason 2"],
          "icon": "activity|alert-triangle|beaker|thermometer|trending-up|stethoscope"
        }
      ],
      "conflicts": [
        {
          "between": ["Agent A", "Agent B"],
          "reason": "Description of disagreement"
        }
      ],
      "recommended_actions": [
        {
          "action": "Action description",
          "urgency": "immediate|soon|routine",
          "rationale": "Why this action is needed"
        }
      ],
      "clinical_reasoning": "Brief consensus explanation"
    }
    
    Guidelines for each agent:
    - Hemodynamics Agent: Analyze HR velocity, MAP, BP trends, perfusion markers
    - Infection Agent: Evaluate temp, WBC, SIRS criteria, suspected infection sources
    - Metabolic Agent: Assess lactate levels, clearance, acid-base status
    - Respiratory Agent: Review RR, SpO2, oxygenation (if available)
    - Data Quality Agent: Flag missing/stale labs, identify data gaps affecting confidence
    - Orchestrator: Synthesize all agent inputs, resolve conflicts, generate consensus
    
    Conflict detection:
    - Flag when agents disagree on severity (e.g., one says critical, another says stable)
    - Explain the source of disagreement
    
    Overall EWS score:
    - Weighted ensemble of all agent scores
    - Time-weighted: recent changes matter more
    - Confidence-weighted: higher confidence agents weighted more"""
    
    user_prompt = f"""Generate multi-agent early warning assessment for this patient:

Patient: {patient['name']}, {patient['age']}y {patient['gender']} in {patient['room']}
Diagnosis: {patient['diagnosis']}
Current Risk Score: {patient['risk_score']}/100 ({patient['risk_level']} RISK)
SIRS Criteria: {patient['sirs_criteria']}/4
qSOFA Score: {ground_truth.get('qsofa_score', 0)}
SOFA Score: {ground_truth.get('sofa_score', 0)}

Current Vitals:
- HR: {vitals['heart_rate']} bpm, RR: {vitals['respiratory_rate']}, BP: {vitals['blood_pressure']} (MAP {map_pressure:.0f} mmHg)
- SpO2: {vitals['spo2']}%, Temp: {vitals['temperature']}°C

Current Labs:
- WBC: {labs['wbc']} K/µL, Lactate: {labs['lactate']} mmol/L

12-Hour Trends:
- HR: {trends['hr_change']:+.1f} bpm ({trends['hr_pct_change']:+.1f}%), Peak: {trends['max_hr']} bpm
- Temp: {trends['temp_change']:+.1f}°C ({trends['temp_pct_change']:+.1f}%), Peak: {trends['max_temp']}°C
- WBC: {trends['wbc_change']:+.1f} K/µL ({trends['wbc_pct_change']:+.1f}%), Peak: {trends['max_wbc']} K/µL
- Lactate: {trends['lactate_change']:+.1f} mmol/L ({trends['lactate_pct_change']:+.1f}%), Peak: {trends['max_lactate']} mmol/L

Devices: {', '.join([d['type'] + f" (Day {d['days']})" for d in patient['devices']])}

Generate analysis from all 6 agents:
1. Hemodynamics Agent - cardiovascular stability
2. Infection Agent - infection markers and SIRS
3. Metabolic Agent - lactate and metabolic status
4. Respiratory Agent - oxygenation and ventilation
5. Data Quality Agent - data completeness and reliability
6. Orchestrator - consensus and conflict resolution

Provide overall EWS score, trend, agent evidence, conflicts, and recommended actions."""

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        ews_data = json.loads(content)
        
        return {
            "patient_id": patient_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            **ews_data
        }
    except json.JSONDecodeError as e:
        return {
            "patient_id": patient_id,
            "overall_ews_score": patient['risk_score'],
            "severity": patient['risk_level'].lower(),
            "trend": "stable",
            "time_to_breach": None,
            "agent_evidence": [
                {
                    "agent": "Orchestrator",
                    "score": patient['risk_score'],
                    "severity": patient['risk_level'].lower(),
                    "confidence": 0.5,
                    "reasons": ["Unable to generate multi-agent analysis. Using baseline risk."],
                    "icon": "stethoscope"
                }
            ],
            "conflicts": [],
            "recommended_actions": [
                {
                    "action": "Continue monitoring",
                    "urgency": "routine",
                    "rationale": "Unable to generate specific recommendations"
                }
            ],
            "clinical_reasoning": "Unable to generate multi-agent analysis. Using simplified assessment.",
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/realtime")
async def realtime_websocket(websocket: WebSocket):
    await websocket.accept()
    
    realtime_endpoint = os.getenv("AZURE_OPENAI_REALTIME_ENDPOINT")
    realtime_api_key = os.getenv("AZURE_OPENAI_REALTIME_API_KEY")
    
    if not realtime_endpoint or not realtime_api_key:
        await websocket.close(code=1008, reason="Realtime API not configured")
        return
    
    azure_ws = None
    try:
        headers = {
            "api-key": realtime_api_key,
            "Content-Type": "application/json"
        }
        
        async with websockets.connect(realtime_endpoint, extra_headers=headers) as azure_ws:
            async def forward_to_azure():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await azure_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"Error forwarding to Azure: {e}")
            
            async def forward_to_client():
                try:
                    async for message in azure_ws:
                        await websocket.send_text(message)
                except Exception as e:
                    print(f"Error forwarding to client: {e}")
            
            await asyncio.gather(
                forward_to_azure(),
                forward_to_client()
            )
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))

@app.post("/api/agui/session")
async def create_session(patient_id: Optional[str] = None):
    """Create a new AG-UI session and return a signed token"""
    return create_agui_session(patient_id)

@app.websocket("/api/agui/ws")
async def agui_websocket(websocket: WebSocket, token: str):
    """AG-UI unified WebSocket endpoint for all modalities"""
    await handle_agui_websocket(
        websocket, 
        token, 
        MOCK_PATIENTS, 
        client, 
        generate_12hour_history, 
        calculate_trend_features
    )

static_dir = Path(__file__).parent.parent.parent / "sepsis-frontend" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="spa")
