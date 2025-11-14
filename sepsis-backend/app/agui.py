
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import secrets
from openai import AzureOpenAI
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

agui_sessions = {}

class AGUISession:
    def __init__(self, session_id: str, patient_id: Optional[str] = None):
        self.session_id = session_id
        self.patient_id = patient_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.context = {}

def create_agui_session(patient_id: Optional[str] = None):
    """Create a new AG-UI session and return a signed token"""
    session_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    
    session = AGUISession(session_id, patient_id)
    agui_sessions[token] = session
    
    return {
        "sessionId": session_id,
        "token": token,
        "expiresIn": 3600
    }

def create_agui_event(event_type: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized AG-UI event"""
    return {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "sessionId": session_id,
        "ts": datetime.now().isoformat(),
        "payload": payload
    }

async def handle_agui_websocket(websocket: WebSocket, token: str, mock_patients, client: AzureOpenAI, generate_12hour_history, calculate_trend_features):
    """AG-UI unified WebSocket endpoint for all modalities"""
    await websocket.accept()
    
    session = agui_sessions.get(token)
    if not session:
        await websocket.send_json(create_agui_event(
            "error",
            "unknown",
            {"code": "INVALID_TOKEN", "message": "Invalid or expired session token"}
        ))
        await websocket.close()
        return
    
    session.last_activity = datetime.now()
    
    try:
        await websocket.send_json(create_agui_event(
            "session.ready",
            session.session_id,
            {"sessionId": session.session_id, "capabilities": ["text", "voice", "tools"]}
        ))
        
        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            payload = data.get("payload", {})
            
            session.last_activity = datetime.now()
            
            if event_type == "input.text":
                message = payload.get("message", "")
                patient_id = payload.get("patientId") or session.patient_id
                
                if patient_id:
                    patient = next((p for p in mock_patients if p["id"] == patient_id), None)
                    if patient:
                        session.patient_id = patient_id
                        session.context["patient"] = patient
                
                try:
                    response = client.chat.completions.create(
                        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT41", "gpt-4.1"),
                        messages=[
                            {"role": "system", "content": "You are a clinical AI assistant for sepsis prevention."},
                            {"role": "user", "content": message}
                        ],
                        stream=True,
                        temperature=0.7,
                        max_tokens=800
                    )
                    
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            await websocket.send_json(create_agui_event(
                                "agent.response.delta",
                                session.session_id,
                                {"content": content}
                            ))
                    
                    await websocket.send_json(create_agui_event(
                        "agent.response.done",
                        session.session_id,
                        {}
                    ))
                except Exception as e:
                    await websocket.send_json(create_agui_event(
                        "error",
                        session.session_id,
                        {"code": "CHAT_ERROR", "message": str(e)}
                    ))
            
            elif event_type == "patient.open":
                patient_id = payload.get("patientId")
                patient = next((p for p in mock_patients if p["id"] == patient_id), None)
                
                if patient:
                    session.patient_id = patient_id
                    session.context["patient"] = patient
                    
                    await websocket.send_json(create_agui_event(
                        "patient.opened",
                        session.session_id,
                        {"patient": patient}
                    ))
                else:
                    await websocket.send_json(create_agui_event(
                        "error",
                        session.session_id,
                        {"code": "PATIENT_NOT_FOUND", "message": f"Patient {patient_id} not found"}
                    ))
            
            elif event_type == "analysis.request":
                patient_id = payload.get("patientId") or session.patient_id
                patient = next((p for p in mock_patients if p["id"] == patient_id), None)
                
                if not patient:
                    await websocket.send_json(create_agui_event(
                        "error",
                        session.session_id,
                        {"code": "NO_PATIENT", "message": "No patient in context"}
                    ))
                    continue
                
                history_data = generate_12hour_history(patient)
                trends = calculate_trend_features(patient, history_data["history"])
                
                await websocket.send_json(create_agui_event(
                    "ui.chart.update",
                    session.session_id,
                    {"history": history_data["history"], "trends": trends}
                ))
                
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
                    
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            await websocket.send_json(create_agui_event(
                                "agent.response.delta",
                                session.session_id,
                                {"content": content, "type": "analysis"}
                            ))
                    
                    await websocket.send_json(create_agui_event(
                        "agent.response.done",
                        session.session_id,
                        {"type": "analysis"}
                    ))
                except Exception as e:
                    await websocket.send_json(create_agui_event(
                        "error",
                        session.session_id,
                        {"code": "ANALYSIS_ERROR", "message": str(e)}
                    ))
            
            elif event_type == "tool.call":
                tool_name = payload.get("tool")
                tool_args = payload.get("args", {})
                
                if tool_name == "get_patient":
                    patient_id = tool_args.get("patientId")
                    patient = next((p for p in mock_patients if p["id"] == patient_id), None)
                    
                    await websocket.send_json(create_agui_event(
                        "tool.result",
                        session.session_id,
                        {"tool": "get_patient", "result": patient}
                    ))
                
                elif tool_name == "get_patients":
                    await websocket.send_json(create_agui_event(
                        "tool.result",
                        session.session_id,
                        {"tool": "get_patients", "result": mock_patients}
                    ))
                
                elif tool_name == "get_history":
                    patient_id = tool_args.get("patientId")
                    patient = next((p for p in mock_patients if p["id"] == patient_id), None)
                    
                    if patient:
                        history = generate_12hour_history(patient)
                        await websocket.send_json(create_agui_event(
                            "tool.result",
                            session.session_id,
                            {"tool": "get_history", "result": history}
                        ))
                    else:
                        await websocket.send_json(create_agui_event(
                            "error",
                            session.session_id,
                            {"code": "PATIENT_NOT_FOUND", "message": f"Patient {patient_id} not found"}
                        ))
            
            elif event_type == "session.close":
                await websocket.send_json(create_agui_event(
                    "session.closed",
                    session.session_id,
                    {}
                ))
                break
            
            else:
                await websocket.send_json(create_agui_event(
                    "error",
                    session.session_id,
                    {"code": "UNKNOWN_EVENT", "message": f"Unknown event type: {event_type}"}
                ))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"AG-UI WebSocket error: {e}")
        try:
            await websocket.send_json(create_agui_event(
                "error",
                session.session_id,
                {"code": "SERVER_ERROR", "message": str(e)}
            ))
        except:
            pass
    finally:
        if token in agui_sessions:
            del agui_sessions[token]
