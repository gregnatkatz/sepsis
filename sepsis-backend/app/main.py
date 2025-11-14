from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock_patients import MOCK_PATIENTS
from app.agui import create_agui_session, handle_agui_websocket

load_dotenv()

app = FastAPI()

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

class ChatRequest(BaseModel):
    message: str
    patient_id: Optional[str] = None

class PatientQuery(BaseModel):
    room: Optional[str] = None
    patient_id: Optional[str] = None

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/patients")
async def get_patients():
    return {"patients": MOCK_PATIENTS}

@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: str):
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
    high_risk = [p for p in MOCK_PATIENTS if p["risk_score"] >= 60]
    return {"patients": high_risk, "count": len(high_risk)}

def generate_12hour_history(patient: Dict) -> Dict:
    """Generate 12-hour historical data based on current/previous values and risk level"""
    vitals_current = patient["vitals"]["current"]
    vitals_prev = patient["vitals"]["previous"]
    labs_current = patient["labs"]["current"]
    labs_prev = patient["labs"]["previous"]
    
    history = []
    now = datetime.now()
    
    for i in range(13):
        hour_offset = 12 - i
        timestamp = (now - timedelta(hours=hour_offset)).isoformat()
        
        if patient["risk_level"] in ["CRITICAL", "HIGH"]:
            progress = i / 12.0
            hr = vitals_prev["heart_rate"] + (vitals_current["heart_rate"] - vitals_prev["heart_rate"]) * progress
            temp = vitals_prev["temperature"] + (vitals_current["temperature"] - vitals_prev["temperature"]) * progress
            wbc = labs_prev["wbc"] + (labs_current["wbc"] - labs_prev["wbc"]) * progress
            lactate = labs_prev["lactate"] + (labs_current["lactate"] - labs_prev["lactate"]) * progress
        else:
            progress = i / 12.0
            hr = vitals_prev["heart_rate"] + (vitals_current["heart_rate"] - vitals_prev["heart_rate"]) * progress * 0.5
            temp = vitals_prev["temperature"] + (vitals_current["temperature"] - vitals_prev["temperature"]) * progress * 0.3
            wbc = labs_prev["wbc"] + (labs_current["wbc"] - labs_prev["wbc"]) * progress * 0.4
            lactate = labs_prev["lactate"] + (labs_current["lactate"] - labs_prev["lactate"]) * progress * 0.2
        
        history.append({
            "timestamp": timestamp,
            "heart_rate": round(hr, 1),
            "temperature": round(temp, 1),
            "wbc": round(wbc, 1),
            "lactate": round(lactate, 1)
        })
    
    return {"history": history}

@app.get("/api/patients/{patient_id}/history")
async def get_patient_history(patient_id: str):
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return generate_12hour_history(patient)

def calculate_trend_features(patient: Dict, history: List[Dict]) -> Dict:
    """Calculate trend features for AI analysis"""
    if len(history) < 2:
        return {}
    
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
async def get_ai_insights(patient_id: str):
    """Generate structured AI insights as alert cards for better readability"""
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
async def get_horizon_forecast(patient_id: str):
    """Predictive Horizon Forecasting: 1h/3h/6h sepsis risk predictions with personalized baselines"""
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    
    baseline_risk = patient['risk_score']
    
    hr_velocity = trends['hr_change'] / 12  # per hour
    temp_velocity = trends['temp_change'] / 12
    lactate_velocity = trends['lactate_change'] / 12
    
    risk_velocity = 0
    if hr_velocity > 0:
        risk_velocity += hr_velocity * 0.5
    if temp_velocity > 0:
        risk_velocity += temp_velocity * 2
    if lactate_velocity > 0:
        risk_velocity += lactate_velocity * 5
    
    forecast_1h = min(100, max(0, baseline_risk + risk_velocity * 1))
    forecast_3h = min(100, max(0, baseline_risk + risk_velocity * 3))
    forecast_6h = min(100, max(0, baseline_risk + risk_velocity * 6))
    
    confidence = 0.85 if abs(trends['hr_pct_change']) < 10 else 0.65
    
    time_to_breach = None
    if risk_velocity > 0 and baseline_risk < 70:
        hours_to_breach = (70 - baseline_risk) / risk_velocity
        if hours_to_breach <= 12:
            time_to_breach = f"{hours_to_breach:.1f}h"
    
    return {
        "patient_id": patient_id,
        "current_risk": baseline_risk,
        "forecasts": [
            {"horizon": "1h", "risk": round(forecast_1h, 1), "confidence": confidence},
            {"horizon": "3h", "risk": round(forecast_3h, 1), "confidence": confidence * 0.9},
            {"horizon": "6h", "risk": round(forecast_6h, 1), "confidence": confidence * 0.8}
        ],
        "time_to_breach": time_to_breach,
        "trend_direction": "rising" if risk_velocity > 0 else "stable" if risk_velocity == 0 else "falling",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/patients/{patient_id}/next-best-action")
async def get_next_best_action(patient_id: str):
    """Next Best Action: Concrete recommendations with expected value and confidence"""
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    history_data = generate_12hour_history(patient)
    trends = calculate_trend_features(patient, history_data["history"])
    ground_truth = patient.get('ground_truth', {})
    
    actions = []
    
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    
    if labs['lactate'] > 2.0 or trends['lactate_change'] > 0.5:
        actions.append({
            "action_type": "lab",
            "title": "Draw Lactate Now",
            "rationale": f"Current lactate {labs['lactate']} mmol/L, trending up {trends['lactate_change']:+.1f}",
            "expected_benefit": "high",
            "confidence": 0.92,
            "urgency": "immediate",
            "order": 1
        })
    
    if patient['sirs_criteria'] >= 2 and labs['wbc'] > 12:
        actions.append({
            "action_type": "lab",
            "title": "Obtain Blood Cultures (2 sets)",
            "rationale": f"SIRS {patient['sirs_criteria']}/4, WBC {labs['wbc']} K/µL",
            "expected_benefit": "high",
            "confidence": 0.88,
            "urgency": "immediate",
            "order": 2
        })
    
    bp_parts = vitals['blood_pressure'].split('/')
    map_pressure = (int(bp_parts[0]) + 2 * int(bp_parts[1])) / 3
    if map_pressure < 65 or int(bp_parts[0]) < 90:
        actions.append({
            "action_type": "intervention",
            "title": "Start 30 mL/kg Crystalloid Bolus",
            "rationale": f"MAP {map_pressure:.0f} mmHg, SBP {bp_parts[0]} mmHg (hypotensive)",
            "expected_benefit": "high",
            "confidence": 0.95,
            "urgency": "immediate",
            "order": 3
        })
    
    if vitals['spo2'] < 92:
        actions.append({
            "action_type": "intervention",
            "title": "Increase O2 Support",
            "rationale": f"SpO2 {vitals['spo2']}% (hypoxemic)",
            "expected_benefit": "medium",
            "confidence": 0.85,
            "urgency": "immediate",
            "order": 4
        })
    
    if patient['risk_level'] in ['CRITICAL', 'HIGH']:
        actions.append({
            "action_type": "monitoring",
            "title": "Repeat Vitals in 15 Minutes",
            "rationale": f"{patient['risk_level']} risk, close monitoring required",
            "expected_benefit": "medium",
            "confidence": 0.90,
            "urgency": "soon",
            "order": 5
        })
    
    if ground_truth.get('sepsis_confirmed') and ground_truth.get('sofa_score', 0) >= 6:
        actions.append({
            "action_type": "escalation",
            "title": "Consider ICU Consult",
            "rationale": f"SOFA score {ground_truth.get('sofa_score')}, severe organ dysfunction",
            "expected_benefit": "high",
            "confidence": 0.87,
            "urgency": "soon",
            "order": 6
        })
    
    return {
        "patient_id": patient_id,
        "actions": sorted(actions, key=lambda x: x['order'])[:5],  # Top 5 actions
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/patients/{patient_id}/sepsis-bundle")
async def get_sepsis_bundle(patient_id: str):
    """1-Hour Sepsis Bundle Autopilot: Live timers, checkboxes, escalation"""
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    ground_truth = patient.get('ground_truth', {})
    
    bundle_active = patient['risk_level'] in ['CRITICAL', 'HIGH'] or ground_truth.get('sepsis_confirmed')
    
    if not bundle_active:
        return {
            "patient_id": patient_id,
            "bundle_active": False,
            "message": "Sepsis bundle not activated for this patient"
        }
    
    onset_time = ground_truth.get('sepsis_onset_time')
    if onset_time:
        bundle_start = datetime.fromisoformat(onset_time.replace('Z', ''))
    else:
        bundle_start = datetime.utcnow() - timedelta(minutes=30)
    
    elapsed_minutes = (datetime.utcnow() - bundle_start).total_seconds() / 60
    remaining_minutes = max(0, 60 - elapsed_minutes)
    
    tasks = [
        {
            "id": "lactate",
            "title": "Measure Lactate",
            "completed": elapsed_minutes > 10,
            "blocked": False,
            "blocker_reason": None,
            "order": 1
        },
        {
            "id": "cultures",
            "title": "Obtain Blood Cultures (2 sets)",
            "completed": elapsed_minutes > 15,
            "blocked": False,
            "blocker_reason": None,
            "order": 2
        },
        {
            "id": "antibiotics",
            "title": "Administer Broad-Spectrum Antibiotics",
            "completed": elapsed_minutes > 45,
            "blocked": elapsed_minutes < 15,
            "blocker_reason": "Waiting for blood cultures" if elapsed_minutes < 15 else None,
            "order": 3
        },
        {
            "id": "fluids",
            "title": "30 mL/kg Crystalloid Bolus",
            "completed": elapsed_minutes > 35,
            "blocked": False,
            "blocker_reason": None,
            "order": 4
        },
        {
            "id": "reassess",
            "title": "Reassess Hemodynamics",
            "completed": elapsed_minutes > 55,
            "blocked": elapsed_minutes < 35,
            "blocker_reason": "Waiting for fluid bolus completion" if elapsed_minutes < 35 else None,
            "order": 5
        }
    ]
    
    completed_count = sum(1 for t in tasks if t['completed'])
    blocked_count = sum(1 for t in tasks if t['blocked'] and not t['completed'])
    
    escalation_needed = remaining_minutes < 15 and completed_count < len(tasks)
    
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
        "escalation_needed": escalation_needed,
        "escalation_message": "Bundle completion at risk - consider charge nurse notification" if escalation_needed else None,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/patients/{patient_id}/what-if")
async def what_if_simulator(patient_id: str, intervention: Dict[str, Any]):
    """What-If Simulator: Predict impact of interventions on risk trajectory"""
    patient = next((p for p in MOCK_PATIENTS if p["id"] == patient_id), None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    current_risk = patient['risk_score']
    vitals = patient['vitals']['current']
    labs = patient['labs']['current']
    
    predicted_risk = current_risk
    predicted_vitals = vitals.copy()
    predicted_labs = labs.copy()
    effects = []
    
    if intervention.get('fluids_ml'):
        fluid_amount = intervention['fluids_ml']
        bp_parts = vitals['blood_pressure'].split('/')
        sbp = int(bp_parts[0])
        dbp = int(bp_parts[1])
        
        sbp_increase = min(20, fluid_amount / 150)
        dbp_increase = min(10, fluid_amount / 300)
        
        predicted_vitals['blood_pressure'] = f"{sbp + int(sbp_increase)}/{dbp + int(dbp_increase)}"
        predicted_risk -= sbp_increase * 0.5
        effects.append(f"BP increase: {sbp}→{sbp + int(sbp_increase)} mmHg")
    
    if intervention.get('oxygen_increase'):
        spo2_increase = min(5, intervention['oxygen_increase'] * 2)
        predicted_vitals['spo2'] = min(100, vitals['spo2'] + spo2_increase)
        predicted_risk -= spo2_increase * 0.3
        effects.append(f"SpO2 increase: {vitals['spo2']}→{predicted_vitals['spo2']}%")
    
    if intervention.get('antibiotics'):
        predicted_risk -= 10
        effects.append("Antibiotics: Expected risk reduction 10 points over 6h")
    
    if intervention.get('fluids_ml') or intervention.get('antibiotics'):
        lactate_reduction = 0.3 if intervention.get('fluids_ml') else 0
        lactate_reduction += 0.5 if intervention.get('antibiotics') else 0
        predicted_labs['lactate'] = max(0.5, labs['lactate'] - lactate_reduction)
        effects.append(f"Lactate reduction: {labs['lactate']}→{predicted_labs['lactate']:.1f} mmol/L")
    
    predicted_risk = max(0, min(100, predicted_risk))
    
    ground_truth = patient.get('ground_truth', {})
    current_sofa = ground_truth.get('sofa_score', 0)
    predicted_sofa = current_sofa
    
    if intervention.get('fluids_ml'):
        predicted_sofa = max(0, predicted_sofa - 1)
    if intervention.get('oxygen_increase'):
        predicted_sofa = max(0, predicted_sofa - 1)
    
    return {
        "patient_id": patient_id,
        "intervention": intervention,
        "current_state": {
            "risk_score": current_risk,
            "vitals": vitals,
            "labs": labs,
            "sofa_score": current_sofa
        },
        "predicted_state": {
            "risk_score": round(predicted_risk, 1),
            "vitals": predicted_vitals,
            "labs": predicted_labs,
            "sofa_score": predicted_sofa
        },
        "effects": effects,
        "risk_reduction": round(current_risk - predicted_risk, 1),
        "confidence": 0.75,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

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
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(
            str(static_dir / "index.html"),
            headers={"Cache-Control": "no-store, max-age=0, must-revalidate"}
        )
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(
            str(static_dir / "index.html"),
            headers={"Cache-Control": "no-store, max-age=0, must-revalidate"}
        )
