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
from app.llm_client import get_llm_client, ModelType

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
    """Predictive Horizon Forecasting: 1h/3h/6h sepsis risk predictions with personalized baselines using Azure OpenAI"""
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
async def get_next_best_action(patient_id: str):
    """Next Best Action: Concrete recommendations with expected value and confidence using Azure OpenAI"""
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
async def get_sepsis_bundle(patient_id: str):
    """1-Hour Sepsis Bundle Autopilot: Live timers, checkboxes, escalation using Azure OpenAI"""
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
async def monte_carlo_what_if(patient_id: str, params: Dict[str, Any] = None):
    """
    Monte Carlo What-If Simulator: Generate top 3 treatment pathways with 100x simulation
    Auto-recommends fluids, vasopressors, antibiotics based on patient state
    """
    from app.monte_carlo import (
        generate_candidate_treatments,
        run_monte_carlo,
        rank_pathways
    )
    
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

@app.get("/api/patients/{patient_id}/early-warning")
async def get_early_warning(patient_id: str):
    """Multi-Agent Early Warning System: 6 specialized agents analyzing patient deterioration"""
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
