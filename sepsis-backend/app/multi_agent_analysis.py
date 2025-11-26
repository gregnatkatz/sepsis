"""
Multi-Agent Analysis System for Comprehensive Sepsis Assessment

Architecture:
1. Specialized Agents - One per clinical domain (Vitals, Hematology, Metabolic, etc.)
2. Aggregation Layer - Synthesizes findings, identifies cross-system correlations
3. RAG Deep Search - Vector store for raw data + agent results retrieval

Based on real sepsis pathophysiology and clinical decision-making patterns.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
import hashlib

from app.llm_client import get_llm_client, ModelType


# ==================== Data Contracts ====================

class AgentIssue(BaseModel):
    """Individual clinical issue identified by an agent"""
    id: str
    label: str
    severity: Literal["low", "moderate", "high", "critical"]
    evidence: List[str]
    related_parameters: List[str]
    clinical_significance: str


class AgentFinding(BaseModel):
    """Structured output from a specialized agent"""
    agent_name: str
    domain: str
    summary: str
    issues: List[AgentIssue]
    trends: Dict[str, str]  # parameter -> trend description
    overall_risk: Literal["low", "moderate", "high", "critical"]
    confidence: float
    recommendations: List[str]


class CrossSystemCorrelation(BaseModel):
    """Correlation identified across multiple organ systems"""
    id: str
    pattern_name: str
    involved_systems: List[str]
    evidence: List[str]
    clinical_interpretation: str
    severity: Literal["low", "moderate", "high", "critical"]


class AggregatedAnalysis(BaseModel):
    """Final aggregated analysis from all agents"""
    patient_id: str
    timestamp: str
    agent_findings: List[AgentFinding]
    cross_system_correlations: List[CrossSystemCorrelation]
    overall_assessment: str
    primary_concerns: List[str]
    sepsis_trajectory: Literal["improving", "stable", "worsening", "critical"]
    mortality_risk: Literal["low", "moderate", "high", "very_high"]
    recommended_actions: List[str]
    confidence_score: float


# ==================== Simple RAG Implementation ====================

class SimpleRAGStore:
    """
    Simple in-memory vector store for RAG retrieval.
    Uses TF-IDF-like embeddings with cosine similarity.
    """
    
    def __init__(self):
        self.documents: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self.vocab: Dict[str, int] = {}
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        import re
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def _build_vocab(self, all_tokens: List[List[str]]):
        """Build vocabulary from all documents"""
        vocab_set = set()
        for tokens in all_tokens:
            vocab_set.update(tokens)
        self.vocab = {word: idx for idx, word in enumerate(sorted(vocab_set))}
    
    def _vectorize(self, tokens: List[str]) -> np.ndarray:
        """Convert tokens to TF vector"""
        vec = np.zeros(len(self.vocab))
        for token in tokens:
            if token in self.vocab:
                vec[self.vocab[token]] += 1
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
    
    def add_documents(self, documents: List[Dict]):
        """
        Add documents to the store.
        Each document should have 'content', 'type', and 'metadata' keys.
        """
        self.documents.extend(documents)
        
        # Tokenize all documents
        all_tokens = [self._tokenize(doc['content']) for doc in self.documents]
        
        # Build vocabulary
        self._build_vocab(all_tokens)
        
        # Vectorize all documents
        if len(self.vocab) > 0:
            self.embeddings = np.array([self._vectorize(tokens) for tokens in all_tokens])
        else:
            self.embeddings = np.zeros((len(self.documents), 1))
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for most relevant documents"""
        if not self.documents or self.embeddings is None:
            return []
        
        query_tokens = self._tokenize(query)
        query_vec = self._vectorize(query_tokens).reshape(1, -1)
        
        # Compute similarities
        similarities = cosine_similarity(query_vec, self.embeddings)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append({
                    **self.documents[idx],
                    'similarity': float(similarities[idx])
                })
        
        return results


# ==================== Specialized Agents ====================

# Concurrency limiter for Azure OpenAI rate limits
AGENT_SEMAPHORE = asyncio.Semaphore(4)

# Agent output cache
AGENT_CACHE: Dict[str, AgentFinding] = {}


def get_cache_key(patient_id: str, agent_name: str, data_hash: str) -> str:
    """Generate cache key for agent results"""
    return f"{patient_id}:{agent_name}:{data_hash}"


def hash_data(data: Dict) -> str:
    """Generate hash of data for caching"""
    return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:8]


AGENT_SYSTEM_PROMPTS = {
    "vitals": """You are the Vitals Analysis Agent, a specialist in analyzing vital sign trends for sepsis patients.

Your role is to analyze:
- Heart rate (HR) trends and variability
- Blood pressure (SBP, DBP, MAP) patterns
- Respiratory rate (RR) and work of breathing
- Temperature patterns (fever, hypothermia)
- Oxygen saturation (SpO2) and FiO2 requirements
- Urine output trends
- Glasgow Coma Scale (GCS) changes

Focus on identifying:
- SIRS criteria fulfillment
- Signs of shock (warm vs cold shock patterns)
- Hemodynamic instability
- Respiratory distress
- Neurological changes

You MUST respond with ONLY a valid JSON object matching this exact schema:
{
  "agent_name": "vitals",
  "domain": "Vital Signs & Hemodynamics",
  "summary": "2-3 sentence summary of findings",
  "issues": [
    {
      "id": "unique_id",
      "label": "Issue name",
      "severity": "low|moderate|high|critical",
      "evidence": ["specific data points"],
      "related_parameters": ["parameter names"],
      "clinical_significance": "why this matters"
    }
  ],
  "trends": {"parameter": "trend description"},
  "overall_risk": "low|moderate|high|critical",
  "confidence": 0.0-1.0,
  "recommendations": ["specific actions"]
}""",

    "hematology": """You are the Hematology Analysis Agent, a specialist in analyzing blood count and coagulation parameters.

Your role is to analyze:
- White blood cell count (WBC) and differential
- Neutrophil count and bands (left shift)
- Lymphocyte count (lymphopenia in sepsis)
- Hemoglobin and hematocrit
- Platelet count and trends
- Red cell distribution width (RDW)

Focus on identifying:
- Leukocytosis or leukopenia
- Left shift (bandemia)
- Thrombocytopenia progression
- Anemia development
- Signs of bone marrow suppression

You MUST respond with ONLY a valid JSON object matching this exact schema:
{
  "agent_name": "hematology",
  "domain": "Hematology & CBC",
  "summary": "2-3 sentence summary of findings",
  "issues": [...],
  "trends": {...},
  "overall_risk": "low|moderate|high|critical",
  "confidence": 0.0-1.0,
  "recommendations": [...]
}""",

    "metabolic": """You are the Metabolic Analysis Agent, a specialist in analyzing metabolic and organ function parameters.

Your role is to analyze:
- Electrolytes (Na, K, Cl, HCO3, Ca, Mg, Phos)
- Renal function (BUN, Creatinine, eGFR)
- Liver function (AST, ALT, ALP, Bilirubin, Albumin)
- Glucose control
- Anion gap
- Lactate dehydrogenase (LDH)

Focus on identifying:
- Acute kidney injury (AKI) staging
- Hepatic dysfunction
- Electrolyte derangements
- Metabolic acidosis
- Multi-organ dysfunction patterns

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema.""",

    "coagulation": """You are the Coagulation Analysis Agent, a specialist in analyzing hemostasis and coagulation parameters.

Your role is to analyze:
- PT/INR trends
- aPTT
- Fibrinogen levels
- D-dimer
- Platelet count (from hematology context)
- Antithrombin III, Protein C/S

Focus on identifying:
- Disseminated intravascular coagulation (DIC)
- Coagulopathy progression
- Bleeding risk
- Thrombotic risk
- Sepsis-induced coagulopathy (SIC)

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema.""",

    "abg": """You are the ABG & Respiratory Analysis Agent, a specialist in analyzing arterial blood gas and respiratory parameters.

Your role is to analyze:
- pH and acid-base status
- PaCO2 and respiratory compensation
- PaO2 and oxygenation
- HCO3 and metabolic component
- Base excess/deficit
- Lactate levels and clearance
- P/F ratio (PaO2/FiO2)
- A-a gradient

Focus on identifying:
- Metabolic acidosis (lactic vs non-lactic)
- Respiratory failure (Type I vs II)
- ARDS criteria
- Lactate clearance patterns (survivor vs non-survivor)
- Compensation adequacy

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema.""",

    "inflammatory": """You are the Inflammatory Markers Analysis Agent, a specialist in analyzing infection and inflammation parameters.

Your role is to analyze:
- C-reactive protein (CRP) trends
- Procalcitonin (PCT) levels and kinetics
- Ferritin
- Interleukin-6 (IL-6)
- ESR
- Other cytokine markers

Focus on identifying:
- Bacterial vs viral infection patterns
- Severity of inflammatory response
- Response to treatment (PCT kinetics)
- Cytokine storm patterns
- Hyperinflammation vs immunosuppression

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema.""",

    "cardiac": """You are the Cardiac Analysis Agent, a specialist in analyzing cardiac function and hemodynamic parameters.

Your role is to analyze:
- Troponin levels (myocardial injury)
- BNP/NT-proBNP (cardiac stress)
- Ejection fraction
- Cardiac output and SVR
- Central venous pressure (CVP)
- ScvO2 (central venous oxygen saturation)
- Arrhythmia patterns

Focus on identifying:
- Septic cardiomyopathy
- Myocardial injury
- Hemodynamic phenotype (hyperdynamic vs hypodynamic)
- Fluid responsiveness indicators
- Vasopressor requirements

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema.""",

    "microbiology": """You are the Microbiology Analysis Agent, a specialist in analyzing culture and infection source data.

Your role is to analyze:
- Blood culture results and timing
- Urine culture results
- Respiratory culture results
- Wound/other culture results
- Organism identification
- Antibiotic susceptibilities
- Source control status

Focus on identifying:
- Likely infection source
- Organism patterns (gram positive vs negative, MDR)
- Antibiotic coverage adequacy
- Source control needs
- Time to appropriate antibiotics

You MUST respond with ONLY a valid JSON object matching the AgentFinding schema."""
}


async def run_specialized_agent(
    agent_name: str,
    patient_data: Dict,
    comprehensive_data: Dict
) -> AgentFinding:
    """
    Run a specialized agent to analyze a specific clinical domain.
    Uses Azure OpenAI with structured output.
    """
    # Check cache first
    data_hash = hash_data(comprehensive_data.get("current_parameters", {}))
    cache_key = get_cache_key(patient_data.get("id", "unknown"), agent_name, data_hash)
    
    if cache_key in AGENT_CACHE:
        return AGENT_CACHE[cache_key]
    
    # Get system prompt for this agent
    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_name, AGENT_SYSTEM_PROMPTS["vitals"])
    
    # Prepare data for the agent
    current_params = comprehensive_data.get("current_parameters", {})
    timepoints = comprehensive_data.get("timepoints", [])
    
    # Extract relevant category data
    category_mapping = {
        "vitals": ["vitals", "scores"],
        "hematology": ["cbc"],
        "metabolic": ["metabolic", "renal"],
        "coagulation": ["coagulation"],
        "abg": ["abg"],
        "inflammatory": ["inflammatory"],
        "cardiac": ["cardiac"],
        "microbiology": ["microbiology", "imaging"]
    }
    
    relevant_categories = category_mapping.get(agent_name, [agent_name])
    
    # Build context for the agent
    relevant_data = {}
    for cat in relevant_categories:
        if cat in current_params:
            relevant_data[cat] = current_params[cat]
    
    # Get time series for relevant parameters
    time_series = {}
    params_by_cat = comprehensive_data.get("parameters_by_category", {})
    for cat in relevant_categories:
        if cat in params_by_cat:
            time_series[cat] = params_by_cat[cat]
    
    # Build user message
    user_message = f"""Analyze the following clinical data for patient {patient_data.get('name', 'Unknown')}:

Patient Info:
- Age: {patient_data.get('age', 'Unknown')}
- Diagnosis: {patient_data.get('diagnosis', 'Unknown')}
- Risk Level: {patient_data.get('risk_level', 'Unknown')}
- Risk Score: {patient_data.get('risk_score', 'Unknown')}

Current Parameters:
{json.dumps(relevant_data, indent=2, default=str)}

120-Hour Time Series (sampled):
{json.dumps({k: {pk: pv['values'][:5] for pk, pv in v.items()} for k, v in list(time_series.items())[:2]}, indent=2, default=str)}

Provide your analysis as a JSON object following the schema in your instructions."""

    # Call Azure OpenAI with rate limiting
    async with AGENT_SEMAPHORE:
        try:
            client = get_llm_client(ModelType.GPT41)
            
            response = await client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            result_dict = json.loads(response_text)
            
            # Validate and create AgentFinding
            finding = AgentFinding(
                agent_name=result_dict.get("agent_name", agent_name),
                domain=result_dict.get("domain", agent_name.title()),
                summary=result_dict.get("summary", "Analysis completed"),
                issues=[AgentIssue(**issue) for issue in result_dict.get("issues", [])],
                trends=result_dict.get("trends", {}),
                overall_risk=result_dict.get("overall_risk", "moderate"),
                confidence=result_dict.get("confidence", 0.7),
                recommendations=result_dict.get("recommendations", [])
            )
            
            # Cache result
            AGENT_CACHE[cache_key] = finding
            
            return finding
            
        except json.JSONDecodeError as e:
            # Return a default finding if JSON parsing fails
            return AgentFinding(
                agent_name=agent_name,
                domain=agent_name.title(),
                summary=f"Analysis completed with parsing issues: {str(e)[:50]}",
                issues=[],
                trends={},
                overall_risk="moderate",
                confidence=0.5,
                recommendations=["Manual review recommended due to parsing issues"]
            )
        except Exception as e:
            return AgentFinding(
                agent_name=agent_name,
                domain=agent_name.title(),
                summary=f"Analysis error: {str(e)[:100]}",
                issues=[],
                trends={},
                overall_risk="moderate",
                confidence=0.3,
                recommendations=["Manual review recommended due to analysis error"]
            )


# ==================== Aggregation Layer ====================

AGGREGATOR_SYSTEM_PROMPT = """You are the Master Aggregation Agent for sepsis analysis. Your role is to synthesize findings from 8 specialized agents and identify cross-system correlations.

You receive structured findings from:
1. Vitals Agent - Hemodynamic and vital sign analysis
2. Hematology Agent - CBC and blood count analysis
3. Metabolic Agent - Organ function and electrolytes
4. Coagulation Agent - Hemostasis and DIC assessment
5. ABG Agent - Acid-base and respiratory analysis
6. Inflammatory Agent - Infection markers
7. Cardiac Agent - Cardiac function
8. Microbiology Agent - Culture and source analysis

Your tasks:
1. Identify CROSS-SYSTEM CORRELATIONS (e.g., "elevated lactate + low platelets + high D-dimer = DIC pattern")
2. Synthesize an OVERALL ASSESSMENT
3. Determine SEPSIS TRAJECTORY (improving/stable/worsening/critical)
4. Estimate MORTALITY RISK
5. Prioritize RECOMMENDED ACTIONS

Known sepsis patterns to look for:
- Warm shock: High CO, low SVR, warm extremities, wide pulse pressure
- Cold shock: Low CO, high SVR, cool extremities, narrow pulse pressure
- DIC: Low platelets + high D-dimer + prolonged PT/INR + low fibrinogen
- ARDS: Low P/F ratio + bilateral infiltrates + high PEEP requirement
- AKI: Rising creatinine + low urine output + high BUN
- Septic cardiomyopathy: Low EF + high troponin + high BNP
- Multi-organ dysfunction: Multiple organ systems showing high risk

You MUST respond with ONLY a valid JSON object matching this schema:
{
  "cross_system_correlations": [
    {
      "id": "unique_id",
      "pattern_name": "Pattern name (e.g., DIC, ARDS)",
      "involved_systems": ["system1", "system2"],
      "evidence": ["specific findings"],
      "clinical_interpretation": "what this means",
      "severity": "low|moderate|high|critical"
    }
  ],
  "overall_assessment": "Comprehensive 3-4 sentence assessment",
  "primary_concerns": ["ranked list of concerns"],
  "sepsis_trajectory": "improving|stable|worsening|critical",
  "mortality_risk": "low|moderate|high|very_high",
  "recommended_actions": ["prioritized actions"],
  "confidence_score": 0.0-1.0
}"""


async def run_aggregator(
    patient_data: Dict,
    agent_findings: List[AgentFinding],
    rag_store: SimpleRAGStore
) -> Dict:
    """
    Run the master aggregator to synthesize all agent findings.
    Uses RAG to retrieve relevant context for deeper analysis.
    """
    # Build context from agent findings
    findings_summary = []
    for finding in agent_findings:
        findings_summary.append({
            "agent": finding.agent_name,
            "domain": finding.domain,
            "summary": finding.summary,
            "risk": finding.overall_risk,
            "confidence": finding.confidence,
            "issues": [{"label": i.label, "severity": i.severity} for i in finding.issues],
            "recommendations": finding.recommendations
        })
    
    # Use RAG to find relevant context
    high_risk_issues = [
        f"{f.agent_name}: {i.label}"
        for f in agent_findings
        for i in f.issues
        if i.severity in ["high", "critical"]
    ]
    
    rag_context = []
    if high_risk_issues:
        query = " ".join(high_risk_issues[:5])
        rag_results = rag_store.search(query, top_k=3)
        rag_context = [r['content'] for r in rag_results]
    
    # Build user message
    user_message = f"""Synthesize the following agent findings for patient {patient_data.get('name', 'Unknown')}:

Patient Info:
- Age: {patient_data.get('age', 'Unknown')}
- Diagnosis: {patient_data.get('diagnosis', 'Unknown')}
- Current Risk Level: {patient_data.get('risk_level', 'Unknown')}

Agent Findings:
{json.dumps(findings_summary, indent=2)}

Additional Context from RAG:
{json.dumps(rag_context, indent=2) if rag_context else "No additional context available"}

Provide your aggregated analysis as a JSON object following the schema in your instructions."""

    try:
        client = get_llm_client(ModelType.GPT41)
        
        response = await client.chat_completion(
            messages=[
                {"role": "system", "content": AGGREGATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        response_text = response["choices"][0]["message"]["content"].strip()
        
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        # Return default aggregation on error
        return {
            "cross_system_correlations": [],
            "overall_assessment": f"Aggregation completed with issues: {str(e)[:100]}",
            "primary_concerns": ["Manual review recommended"],
            "sepsis_trajectory": "stable",
            "mortality_risk": "moderate",
            "recommended_actions": ["Continue monitoring", "Manual clinical review"],
            "confidence_score": 0.5
        }


# ==================== Main Orchestrator ====================

async def run_multi_agent_analysis(
    patient_id: str,
    patient_data: Dict,
    comprehensive_data: Dict
) -> AggregatedAnalysis:
    """
    Orchestrate the full multi-agent analysis pipeline.
    
    1. Build RAG store with patient data
    2. Run all specialized agents in parallel
    3. Aggregate findings
    4. Return comprehensive analysis
    """
    # Build RAG store
    rag_store = SimpleRAGStore()
    
    # Add documents to RAG store
    documents = []
    
    # Add time series summaries
    for tp in comprehensive_data.get("timepoints", [])[:10]:
        hour = tp.get("hour", 0)
        phase = tp.get("phase", "unknown")
        severity = tp.get("severity", 0)
        
        doc_content = f"Hour {hour}: Phase={phase}, Severity={severity:.2f}"
        
        # Add key vitals
        vitals = tp.get("parameters", {}).get("vitals", {})
        if vitals:
            hr = vitals.get("heart_rate", {}).get("value", "N/A")
            map_val = vitals.get("map", {}).get("value", "N/A")
            temp = vitals.get("temperature", {}).get("value", "N/A")
            doc_content += f", HR={hr}, MAP={map_val}, Temp={temp}"
        
        # Add key labs
        abg = tp.get("parameters", {}).get("abg", {})
        if abg:
            lactate = abg.get("lactate_abg", {}).get("value", "N/A")
            ph = abg.get("ph", {}).get("value", "N/A")
            doc_content += f", Lactate={lactate}, pH={ph}"
        
        documents.append({
            "content": doc_content,
            "type": "timepoint",
            "metadata": {"hour": hour, "phase": phase}
        })
    
    # Add lactate clearance data
    for lc in comprehensive_data.get("lactate_clearance", []):
        documents.append({
            "content": f"Lactate clearance at hour {lc['hour']}: {lc['lactate']} mmol/L, clearance {lc['clearance_pct']}%",
            "type": "lactate_clearance",
            "metadata": lc
        })
    
    # Add archetype description
    documents.append({
        "content": f"Patient archetype: {comprehensive_data.get('archetype', 'unknown')} - {comprehensive_data.get('archetype_description', '')}",
        "type": "archetype",
        "metadata": {}
    })
    
    rag_store.add_documents(documents)
    
    # Run all specialized agents in parallel
    agent_names = ["vitals", "hematology", "metabolic", "coagulation", "abg", "inflammatory", "cardiac", "microbiology"]
    
    tasks = [
        run_specialized_agent(agent_name, patient_data, comprehensive_data)
        for agent_name in agent_names
    ]
    
    agent_findings = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and convert to AgentFinding objects
    valid_findings = []
    for finding in agent_findings:
        if isinstance(finding, AgentFinding):
            valid_findings.append(finding)
        elif isinstance(finding, Exception):
            # Create error finding
            valid_findings.append(AgentFinding(
                agent_name="error",
                domain="Error",
                summary=f"Agent error: {str(finding)[:100]}",
                issues=[],
                trends={},
                overall_risk="moderate",
                confidence=0.0,
                recommendations=["Manual review required"]
            ))
    
    # Run aggregator
    aggregation_result = await run_aggregator(patient_data, valid_findings, rag_store)
    
    # Build final analysis
    correlations = [
        CrossSystemCorrelation(**corr)
        for corr in aggregation_result.get("cross_system_correlations", [])
    ]
    
    analysis = AggregatedAnalysis(
        patient_id=patient_id,
        timestamp=datetime.now().isoformat(),
        agent_findings=valid_findings,
        cross_system_correlations=correlations,
        overall_assessment=aggregation_result.get("overall_assessment", "Analysis completed"),
        primary_concerns=aggregation_result.get("primary_concerns", []),
        sepsis_trajectory=aggregation_result.get("sepsis_trajectory", "stable"),
        mortality_risk=aggregation_result.get("mortality_risk", "moderate"),
        recommended_actions=aggregation_result.get("recommended_actions", []),
        confidence_score=aggregation_result.get("confidence_score", 0.7)
    )
    
    return analysis


def clear_agent_cache():
    """Clear the agent result cache"""
    global AGENT_CACHE
    AGENT_CACHE = {}
