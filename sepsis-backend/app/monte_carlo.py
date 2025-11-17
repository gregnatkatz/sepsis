"""
Monte Carlo What-If Simulator for Sepsis Treatment Pathways
Generates candidate treatments, runs stochastic simulations, and ranks top 3 pathways
"""

import random
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class FluidType(str, Enum):
    CRYSTALLOID = "crystalloid"
    COLLOID = "colloid"

class VasopressorType(str, Enum):
    NOREPINEPHRINE = "norepinephrine"
    VASOPRESSIN = "vasopressin"
    DOPAMINE = "dopamine"
    EPINEPHRINE = "epinephrine"

class AntibioticCoverage(str, Enum):
    BROAD_SPECTRUM = "broad_spectrum"
    TARGETED = "targeted"
    EMPIRIC = "empiric"

@dataclass
class TreatmentCandidate:
    """Represents a treatment pathway candidate"""
    name: str
    fluids_ml: int
    fluids_type: FluidType
    fluids_rate_ml_hr: int
    vasopressor: VasopressorType
    vasopressor_dose_mcg_kg_min: float
    vasopressor_timing_min: int  # Minutes after fluids
    antibiotics: AntibioticCoverage
    antibiotics_timing_min: int  # Minutes from now
    reassessment_intervals_min: List[int]

@dataclass
class SimulationOutcome:
    """Results from a single Monte Carlo simulation run"""
    survival_prob: float
    time_to_stability_hr: float
    organ_preservation_score: float  # 0-100
    final_map: float
    final_lactate: float
    final_sofa: int
    fluid_overload_risk: float
    hypotension_duration_min: float
    adverse_events: List[str]

def generate_candidate_treatments(patient: Dict[str, Any]) -> List[TreatmentCandidate]:
    """
    Generate 4-6 evidence-based treatment candidates based on patient state
    Uses Surviving Sepsis Campaign guidelines as foundation
    """
    risk_score = patient.get('risk_score', 50)
    risk_level = patient.get('risk_level', 'MODERATE')
    vitals = patient.get('vitals', {}).get('current', {})
    labs = patient.get('labs', {}).get('current', {})
    ground_truth = patient.get('ground_truth', {})
    
    bp = vitals.get('blood_pressure', '120/80')
    bp_parts = bp.split('/')
    sbp = int(bp_parts[0])
    dbp = int(bp_parts[1])
    map_pressure = (sbp + 2 * dbp) / 3
    
    lactate = labs.get('lactate', 2.0)
    weight_kg = 70  # Assume average weight
    
    candidates = []
    
    candidates.append(TreatmentCandidate(
        name="Aggressive Fluid-First",
        fluids_ml=2100,  # 30 mL/kg for 70kg
        fluids_type=FluidType.CRYSTALLOID,
        fluids_rate_ml_hr=2100,  # Within 1 hour
        vasopressor=VasopressorType.NOREPINEPHRINE,
        vasopressor_dose_mcg_kg_min=0.05,
        vasopressor_timing_min=60,  # After fluids if MAP still <65
        antibiotics=AntibioticCoverage.BROAD_SPECTRUM,
        antibiotics_timing_min=15,  # Within 1 hour
        reassessment_intervals_min=[30, 60, 120]
    ))
    
    if lactate > 4.0 or map_pressure < 60:
        candidates.append(TreatmentCandidate(
            name="Early Vasopressor + Fluids",
            fluids_ml=1500,  # ~20 mL/kg
            fluids_type=FluidType.CRYSTALLOID,
            fluids_rate_ml_hr=1500,
            vasopressor=VasopressorType.NOREPINEPHRINE,
            vasopressor_dose_mcg_kg_min=0.1,
            vasopressor_timing_min=15,  # Start early
            antibiotics=AntibioticCoverage.BROAD_SPECTRUM,
            antibiotics_timing_min=10,
            reassessment_intervals_min=[15, 30, 60]
        ))
    
    candidates.append(TreatmentCandidate(
        name="Conservative Fluid + Early Antibiotics",
        fluids_ml=1000,  # ~15 mL/kg
        fluids_type=FluidType.CRYSTALLOID,
        fluids_rate_ml_hr=1000,
        vasopressor=VasopressorType.NOREPINEPHRINE,
        vasopressor_dose_mcg_kg_min=0.05,
        vasopressor_timing_min=45,
        antibiotics=AntibioticCoverage.BROAD_SPECTRUM,
        antibiotics_timing_min=5,  # Very early
        reassessment_intervals_min=[30, 60, 120]
    ))
    
    if risk_level in ['CRITICAL', 'HIGH']:
        candidates.append(TreatmentCandidate(
            name="Dual Vasopressor Strategy",
            fluids_ml=1500,
            fluids_type=FluidType.CRYSTALLOID,
            fluids_rate_ml_hr=1500,
            vasopressor=VasopressorType.NOREPINEPHRINE,
            vasopressor_dose_mcg_kg_min=0.15,  # Higher dose, plan to add vasopressin
            vasopressor_timing_min=20,
            antibiotics=AntibioticCoverage.BROAD_SPECTRUM,
            antibiotics_timing_min=10,
            reassessment_intervals_min=[15, 30, 45, 60]
        ))
    
    if risk_level in ['MODERATE', 'LOW']:
        candidates.append(TreatmentCandidate(
            name="Staged Reassessment",
            fluids_ml=1500,
            fluids_type=FluidType.CRYSTALLOID,
            fluids_rate_ml_hr=750,  # Slower rate
            vasopressor=VasopressorType.NOREPINEPHRINE,
            vasopressor_dose_mcg_kg_min=0.05,
            vasopressor_timing_min=90,  # Later if needed
            antibiotics=AntibioticCoverage.EMPIRIC,
            antibiotics_timing_min=30,
            reassessment_intervals_min=[60, 120, 180]
        ))
    
    if ground_truth.get('septic_cardiomyopathy') or sbp < 80:
        candidates.append(TreatmentCandidate(
            name="Colloid-Based Resuscitation",
            fluids_ml=1000,
            fluids_type=FluidType.COLLOID,
            fluids_rate_ml_hr=1000,
            vasopressor=VasopressorType.NOREPINEPHRINE,
            vasopressor_dose_mcg_kg_min=0.08,
            vasopressor_timing_min=30,
            antibiotics=AntibioticCoverage.BROAD_SPECTRUM,
            antibiotics_timing_min=15,
            reassessment_intervals_min=[30, 60, 120]
        ))
    
    return candidates[:6]  # Return up to 6 candidates

def run_single_simulation(
    patient: Dict[str, Any],
    candidate: TreatmentCandidate,
    rng: random.Random
) -> SimulationOutcome:
    """
    Run a single stochastic simulation of treatment pathway
    Uses physiologic model with parameter variance
    """
    vitals = patient.get('vitals', {}).get('current', {})
    labs = patient.get('labs', {}).get('current', {})
    ground_truth = patient.get('ground_truth', {})
    
    bp = vitals.get('blood_pressure', '120/80')
    bp_parts = bp.split('/')
    sbp = int(bp_parts[0])
    dbp = int(bp_parts[1])
    initial_map = (sbp + 2 * dbp) / 3
    
    initial_lactate = labs.get('lactate', 2.0)
    initial_sofa = ground_truth.get('sofa_score', 4)
    hr = vitals.get('heart_rate', 90)
    
    fluid_responsiveness = rng.gauss(0.6, 0.15)  # 0-1 scale
    fluid_responsiveness = max(0.1, min(1.0, fluid_responsiveness))
    
    vasopressor_sensitivity = rng.gauss(0.7, 0.12)
    vasopressor_sensitivity = max(0.3, min(1.0, vasopressor_sensitivity))
    
    antibiotic_susceptibility = rng.gauss(0.85, 0.1)
    antibiotic_susceptibility = max(0.5, min(1.0, antibiotic_susceptibility))
    
    baseline_mortality_risk = patient.get('risk_score', 50) / 100.0
    
    fluid_effect_map = 0
    fluid_overload_penalty = 0
    
    if candidate.fluids_ml > 0:
        fluid_ml_per_kg = candidate.fluids_ml / 70  # Assume 70kg
        base_map_increase = fluid_ml_per_kg * 0.3 * fluid_responsiveness
        fluid_effect_map = base_map_increase * (1 - rng.uniform(0, 0.2))  # Variance
        
        if fluid_ml_per_kg > 30:
            fluid_overload_penalty = (fluid_ml_per_kg - 30) * 0.01 * (1 - fluid_responsiveness)
    
    vasopressor_effect_map = 0
    vasopressor_penalty = 0
    
    if candidate.vasopressor_dose_mcg_kg_min > 0:
        dose = candidate.vasopressor_dose_mcg_kg_min
        base_map_increase = dose * 100 * vasopressor_sensitivity
        vasopressor_effect_map = base_map_increase * (1 - rng.uniform(0, 0.15))
        
        if dose > 0.2:
            vasopressor_penalty = (dose - 0.2) * 0.05
    
    antibiotic_effect = 0
    antibiotic_timing_bonus = 0
    
    if candidate.antibiotics_timing_min <= 60:
        timing_factor = 1.0 - (candidate.antibiotics_timing_min / 60) * 0.3
        antibiotic_effect = 0.15 * antibiotic_susceptibility * timing_factor
        
        if candidate.antibiotics_timing_min <= 30:
            antibiotic_timing_bonus = 0.05  # Extra bonus for very early
    
    final_map = initial_map + fluid_effect_map + vasopressor_effect_map
    final_map = max(50, min(110, final_map))  # Physiologic bounds
    
    lactate_clearance = 0
    if final_map >= 65:
        lactate_clearance = 0.3 * (final_map - 65) / 20  # Better perfusion = better clearance
    lactate_clearance += antibiotic_effect * 0.5  # Antibiotics help
    
    final_lactate = initial_lactate * (1 - lactate_clearance)
    final_lactate = max(0.5, final_lactate)
    
    sofa_improvement = 0
    if final_map >= 65:
        sofa_improvement += 1
    if final_lactate < 2.0:
        sofa_improvement += 1
    if antibiotic_effect > 0.1:
        sofa_improvement += 1
    
    final_sofa = max(0, initial_sofa - sofa_improvement)
    
    survival_prob = 1.0 - baseline_mortality_risk
    survival_prob += antibiotic_effect + antibiotic_timing_bonus
    survival_prob += 0.1 if final_map >= 65 else -0.1
    survival_prob += 0.1 if final_lactate < 2.0 else -0.05
    survival_prob -= fluid_overload_penalty
    survival_prob -= vasopressor_penalty
    survival_prob = max(0.1, min(0.99, survival_prob))
    
    time_to_stability = 6.0  # Base time
    if candidate.antibiotics_timing_min <= 30:
        time_to_stability -= 1.5
    if final_map >= 70:
        time_to_stability -= 1.0
    if candidate.vasopressor_timing_min <= 30:
        time_to_stability -= 0.5
    time_to_stability = max(1.0, time_to_stability)
    
    organ_preservation = 70.0  # Base
    organ_preservation += (final_map - 65) * 0.5 if final_map >= 65 else (final_map - 65) * 1.0
    organ_preservation += (2.0 - final_lactate) * 5 if final_lactate < 2.0 else 0
    organ_preservation -= fluid_overload_penalty * 100
    organ_preservation -= vasopressor_penalty * 50
    organ_preservation = max(0, min(100, organ_preservation))
    
    hypotension_duration = 0
    if initial_map < 65:
        if candidate.vasopressor_timing_min <= 30:
            hypotension_duration = candidate.vasopressor_timing_min
        else:
            hypotension_duration = 60  # Assume 1 hour if delayed
    
    adverse_events = []
    if fluid_overload_penalty > 0.02:
        adverse_events.append("Fluid overload risk")
    if vasopressor_penalty > 0.01:
        adverse_events.append("High vasopressor dose")
    if candidate.antibiotics_timing_min > 60:
        adverse_events.append("Delayed antibiotics")
    
    return SimulationOutcome(
        survival_prob=survival_prob,
        time_to_stability_hr=time_to_stability,
        organ_preservation_score=organ_preservation,
        final_map=final_map,
        final_lactate=final_lactate,
        final_sofa=final_sofa,
        fluid_overload_risk=fluid_overload_penalty,
        hypotension_duration_min=hypotension_duration,
        adverse_events=adverse_events
    )

def run_monte_carlo(
    patient: Dict[str, Any],
    candidate: TreatmentCandidate,
    samples: int = 100,
    seed: int = None
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation for a treatment candidate
    Returns aggregated statistics and distributions
    """
    rng = random.Random(seed)
    outcomes = []
    
    for _ in range(samples):
        outcome = run_single_simulation(patient, candidate, rng)
        outcomes.append(outcome)
    
    survival_probs = [o.survival_prob for o in outcomes]
    times_to_stability = [o.time_to_stability_hr for o in outcomes]
    organ_scores = [o.organ_preservation_score for o in outcomes]
    final_maps = [o.final_map for o in outcomes]
    final_lactates = [o.final_lactate for o in outcomes]
    
    return {
        "candidate_name": candidate.name,
        "samples": samples,
        "expected_outcomes": {
            "survival_prob": {
                "mean": np.mean(survival_probs),
                "std": np.std(survival_probs),
                "p25": np.percentile(survival_probs, 25),
                "p50": np.percentile(survival_probs, 50),
                "p75": np.percentile(survival_probs, 75)
            },
            "time_to_stability_hr": {
                "mean": np.mean(times_to_stability),
                "std": np.std(times_to_stability),
                "p25": np.percentile(times_to_stability, 25),
                "p50": np.percentile(times_to_stability, 50),
                "p75": np.percentile(times_to_stability, 75)
            },
            "organ_preservation_score": {
                "mean": np.mean(organ_scores),
                "std": np.std(organ_scores),
                "p25": np.percentile(organ_scores, 25),
                "p50": np.percentile(organ_scores, 50),
                "p75": np.percentile(organ_scores, 75)
            },
            "final_map": {
                "mean": np.mean(final_maps),
                "std": np.std(final_maps)
            },
            "final_lactate": {
                "mean": np.mean(final_lactates),
                "std": np.std(final_lactates)
            }
        },
        "adverse_event_rate": sum(1 for o in outcomes if o.adverse_events) / samples,
        "common_adverse_events": _get_common_events([o.adverse_events for o in outcomes])
    }

def _get_common_events(all_events: List[List[str]]) -> List[str]:
    """Get most common adverse events"""
    event_counts = {}
    for events in all_events:
        for event in events:
            event_counts[event] = event_counts.get(event, 0) + 1
    
    sorted_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)
    return [event for event, count in sorted_events[:3]]

def rank_pathways(
    monte_carlo_results: List[Dict[str, Any]],
    weights: Dict[str, float] = None
) -> List[Dict[str, Any]]:
    """
    Rank treatment pathways by expected utility
    
    Default weights:
    - survival_prob: 0.6
    - time_to_stability: 0.25 (negative, faster is better)
    - organ_preservation: 0.15
    """
    if weights is None:
        weights = {
            "survival_prob": 0.6,
            "time_to_stability": 0.25,
            "organ_preservation": 0.15
        }
    
    ranked = []
    for result in monte_carlo_results:
        outcomes = result["expected_outcomes"]
        
        survival_score = outcomes["survival_prob"]["mean"]
        time_score = 1.0 - (outcomes["time_to_stability_hr"]["mean"] / 10.0)  # Normalize to 0-1
        organ_score = outcomes["organ_preservation_score"]["mean"] / 100.0  # Normalize to 0-1
        
        utility = (
            weights["survival_prob"] * survival_score +
            weights["time_to_stability"] * time_score +
            weights["organ_preservation"] * organ_score
        )
        
        utility -= result["adverse_event_rate"] * 0.1
        
        ranked.append({
            **result,
            "expected_utility": utility,
            "rank_score": utility
        })
    
    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    
    for idx, pathway in enumerate(ranked, 1):
        pathway["rank"] = idx
    
    return ranked
