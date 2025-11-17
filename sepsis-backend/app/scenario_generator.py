"""
Scenario Generator for Monte Carlo What-If Simulator
Generates 500+ semi-synthetic sepsis scenarios with treatment history
"""

import random
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

class InfectionSource(str, Enum):
    URINARY_TRACT = "urinary_tract"
    PULMONARY = "pulmonary"
    INTRA_ABDOMINAL = "intra_abdominal"
    SKIN_SOFT_TISSUE = "skin_soft_tissue"
    BLOODSTREAM = "bloodstream"
    UNKNOWN = "unknown"

class PathogenType(str, Enum):
    GRAM_NEGATIVE = "gram_negative"
    GRAM_POSITIVE = "gram_positive"
    MIXED = "mixed"
    FUNGAL = "fungal"
    UNKNOWN = "unknown"

class ResistanceProfile(str, Enum):
    SUSCEPTIBLE = "susceptible"
    ESBL = "esbl"  # Extended-spectrum beta-lactamase
    MRSA = "mrsa"  # Methicillin-resistant Staph aureus
    VRE = "vre"    # Vancomycin-resistant Enterococcus
    MDR = "mdr"    # Multi-drug resistant

@dataclass
class TreatmentEvent:
    """Single treatment event in patient history"""
    type: str  # fluid, antibiotic, vasopressor, lab, imaging
    t_start_min: int
    t_end_min: Optional[int] = None
    details: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            "type": self.type,
            "t_start_min": self.t_start_min,
            "t_end_min": self.t_end_min,
            **self.details
        }

@dataclass
class SepsisScenario:
    """Complete sepsis scenario with treatment history"""
    schema_version: str = "1.0"
    scenario_id: str = ""
    seed: int = 0
    variant_of: Optional[str] = None
    
    age: int = 65
    gender: str = "M"
    weight_kg: float = 70.0
    comorbidities: List[str] = None
    
    infection_source: str = InfectionSource.UNKNOWN.value
    suspected_pathogen: str = PathogenType.UNKNOWN.value
    resistance_profile: str = ResistanceProfile.SUSCEPTIBLE.value
    
    fluid_responsiveness: float = 0.6  # 0-1 scale
    vasopressor_sensitivity: float = 0.7  # 0-1 scale
    antibiotic_susceptibility: float = 0.85  # 0-1 scale
    septic_cardiomyopathy: bool = False
    egfr: float = 60.0  # Renal function
    
    sbp: int = 90
    dbp: int = 55
    hr: int = 110
    rr: int = 24
    spo2: int = 92
    temp_c: float = 38.5
    wbc: float = 15.0
    lactate: float = 2.5
    
    hr_delta: int = 0
    lactate_delta: float = 0.0
    temp_delta: float = 0.0
    
    treatment_events: List[Dict[str, Any]] = None
    cumulative_fluids_ml: int = 0
    antibiotics_last_6h: List[str] = None
    current_pressors: Dict[str, float] = None
    
    delta_map_30m_post_fluids: Optional[int] = None
    lactate_clearance_6h: Optional[float] = None
    fluid_balance_ml_6h: int = 0
    pressors_high_dose_flag: bool = False
    
    t_now_min: int = 0
    current_map: float = 65.0
    current_lactate: float = 2.5
    
    risk_score: int = 50
    risk_level: str = "MODERATE"
    sirs: int = 2
    qsofa: int = 1
    sofa: int = 4
    
    survival: bool = True
    time_to_stability_hr: float = 4.0
    organ_dysfunction_renal: bool = False
    organ_dysfunction_hepatic: bool = False
    organ_dysfunction_cns: bool = False
    
    tags: List[str] = None
    
    def __post_init__(self):
        if self.comorbidities is None:
            self.comorbidities = []
        if self.treatment_events is None:
            self.treatment_events = []
        if self.antibiotics_last_6h is None:
            self.antibiotics_last_6h = []
        if self.current_pressors is None:
            self.current_pressors = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "variant_of": self.variant_of,
            "demographics": {
                "age": self.age,
                "gender": self.gender,
                "weight_kg": self.weight_kg,
                "comorbidities": self.comorbidities
            },
            "infection": {
                "source": self.infection_source,
                "suspected_pathogen": self.suspected_pathogen,
                "resistance_profile": self.resistance_profile
            },
            "physiology_baseline": {
                "fluid_responsiveness": self.fluid_responsiveness,
                "vasopressor_sensitivity": self.vasopressor_sensitivity,
                "antibiotic_susceptibility": self.antibiotic_susceptibility,
                "septic_cardiomyopathy": self.septic_cardiomyopathy,
                "renal_function": {"egfr": self.egfr}
            },
            "presentation": {
                "t0_vitals": {
                    "sbp": self.sbp,
                    "dbp": self.dbp,
                    "hr": self.hr,
                    "rr": self.rr,
                    "spo2": self.spo2,
                    "temp_c": self.temp_c
                },
                "t0_labs": {
                    "wbc": self.wbc,
                    "lactate": self.lactate
                },
                "trend_12h": {
                    "hr_delta": self.hr_delta,
                    "lactate_delta": self.lactate_delta,
                    "temp_delta": self.temp_delta
                }
            },
            "treatment_history": {
                "events": self.treatment_events,
                "response_features": {
                    "delta_map_30m_post_fluids": self.delta_map_30m_post_fluids,
                    "lactate_clearance_6h": self.lactate_clearance_6h,
                    "fluid_balance_ml_6h": self.fluid_balance_ml_6h,
                    "pressors_high_dose_flag": self.pressors_high_dose_flag
                }
            },
            "current_state": {
                "t_now_min": self.t_now_min,
                "map": self.current_map,
                "hr": self.hr,
                "spo2": self.spo2,
                "lactate": self.current_lactate,
                "current_pressors": self.current_pressors,
                "antibiotics_last_6h": self.antibiotics_last_6h,
                "cumulative_fluids_ml": self.cumulative_fluids_ml
            },
            "risk": {
                "risk_score": self.risk_score,
                "risk_level": self.risk_level,
                "sirs": self.sirs,
                "qsofa": self.qsofa,
                "sofa": self.sofa
            },
            "ground_truth": {
                "survival": self.survival,
                "time_to_stability_hr": self.time_to_stability_hr,
                "organ_dysfunction": {
                    "renal": self.organ_dysfunction_renal,
                    "hepatic": self.organ_dysfunction_hepatic,
                    "cns": self.organ_dysfunction_cns
                }
            },
            "tags": self.tags
        }


class ScenarioGenerator:
    """Generate semi-synthetic sepsis scenarios"""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.scenario_counter = 0
    
    def generate_fresh_scenario(
        self,
        risk_level: str,
        infection_source: str = None
    ) -> SepsisScenario:
        """Generate a fresh ED presentation scenario (no prior treatment)"""
        self.scenario_counter += 1
        scenario_id = f"scn_{self.scenario_counter:06d}"
        seed = self.rng.randint(1, 1000000)
        
        if risk_level == "LOW":
            sbp_range = (100, 120)
            lactate_range = (1.0, 2.0)
            sofa_range = (0, 2)
            risk_score_range = (10, 30)
            survival_prob = 0.98
        elif risk_level == "MODERATE":
            sbp_range = (90, 100)
            lactate_range = (2.0, 3.0)
            sofa_range = (2, 4)
            risk_score_range = (30, 60)
            survival_prob = 0.90
        elif risk_level == "HIGH":
            sbp_range = (80, 90)
            lactate_range = (3.0, 4.5)
            sofa_range = (4, 7)
            risk_score_range = (60, 80)
            survival_prob = 0.75
        else:  # CRITICAL
            sbp_range = (60, 80)
            lactate_range = (4.5, 8.0)
            sofa_range = (7, 12)
            risk_score_range = (80, 95)
            survival_prob = 0.50
        
        age = self.rng.randint(45, 85)
        gender = self.rng.choice(["M", "F"])
        weight_kg = self.rng.gauss(75, 15)
        weight_kg = max(50, min(120, weight_kg))
        
        comorbidity_pool = ["CHF", "CKD", "COPD", "DM", "cirrhosis", "immunosuppressed"]
        num_comorbidities = 0
        if risk_level in ["HIGH", "CRITICAL"]:
            num_comorbidities = self.rng.randint(2, 4)
        elif risk_level == "MODERATE":
            num_comorbidities = self.rng.randint(1, 2)
        comorbidities = self.rng.sample(comorbidity_pool, min(num_comorbidities, len(comorbidity_pool)))
        
        if infection_source is None:
            infection_source = self.rng.choice(list(InfectionSource)).value
        
        if infection_source == InfectionSource.URINARY_TRACT.value:
            suspected_pathogen = PathogenType.GRAM_NEGATIVE.value
            resistance_prob = {"susceptible": 0.7, "esbl": 0.25, "mdr": 0.05}
        elif infection_source == InfectionSource.PULMONARY.value:
            suspected_pathogen = self.rng.choice([PathogenType.GRAM_POSITIVE.value, PathogenType.GRAM_NEGATIVE.value])
            resistance_prob = {"susceptible": 0.75, "mrsa": 0.15, "mdr": 0.10}
        elif infection_source == InfectionSource.SKIN_SOFT_TISSUE.value:
            suspected_pathogen = PathogenType.GRAM_POSITIVE.value
            resistance_prob = {"susceptible": 0.70, "mrsa": 0.25, "mdr": 0.05}
        else:
            suspected_pathogen = PathogenType.MIXED.value
            resistance_prob = {"susceptible": 0.65, "esbl": 0.15, "mrsa": 0.10, "mdr": 0.10}
        
        resistance_profile = self.rng.choices(
            list(resistance_prob.keys()),
            weights=list(resistance_prob.values())
        )[0]
        
        fluid_responsiveness = self.rng.gauss(0.6, 0.15)
        fluid_responsiveness = max(0.2, min(1.0, fluid_responsiveness))
        
        vasopressor_sensitivity = self.rng.gauss(0.7, 0.12)
        vasopressor_sensitivity = max(0.3, min(1.0, vasopressor_sensitivity))
        
        antibiotic_susceptibility = 0.9 if resistance_profile == "susceptible" else self.rng.uniform(0.4, 0.7)
        
        septic_cardiomyopathy = "CHF" in comorbidities or self.rng.random() < 0.15
        
        egfr = 90.0
        if "CKD" in comorbidities:
            egfr = self.rng.uniform(20, 50)
        else:
            egfr = self.rng.uniform(60, 100)
        
        sbp = self.rng.randint(*sbp_range)
        dbp = self.rng.randint(50, 70)
        hr = self.rng.randint(90, 130)
        rr = self.rng.randint(20, 32)
        spo2 = self.rng.randint(88, 96)
        temp_c = self.rng.uniform(37.5, 40.0)
        
        wbc = self.rng.uniform(12.0, 25.0)
        lactate = self.rng.uniform(*lactate_range)
        
        hr_delta = self.rng.randint(10, 30)
        lactate_delta = self.rng.uniform(0.5, 2.0)
        temp_delta = self.rng.uniform(0.5, 1.5)
        
        sofa = self.rng.randint(*sofa_range)
        sirs = self.rng.randint(2, 4)
        qsofa = min(3, sofa // 3)
        risk_score = self.rng.randint(*risk_score_range)
        
        survival = self.rng.random() < survival_prob
        time_to_stability = self.rng.uniform(2.0, 8.0) if survival else 0.0
        organ_dysfunction_renal = "CKD" in comorbidities or self.rng.random() < 0.3
        organ_dysfunction_hepatic = "cirrhosis" in comorbidities or self.rng.random() < 0.15
        organ_dysfunction_cns = risk_level == "CRITICAL" and self.rng.random() < 0.4
        
        tags = ["antibiotic_naive", "fresh_presentation"]
        if lactate > 4.0:
            tags.append("high_lactate")
        if sbp < 90:
            tags.append("hypotension")
        if resistance_profile != "susceptible":
            tags.append("resistance_risk")
        
        current_map = (sbp + 2 * dbp) / 3
        
        return SepsisScenario(
            scenario_id=scenario_id,
            seed=seed,
            age=age,
            gender=gender,
            weight_kg=weight_kg,
            comorbidities=comorbidities,
            infection_source=infection_source,
            suspected_pathogen=suspected_pathogen,
            resistance_profile=resistance_profile,
            fluid_responsiveness=fluid_responsiveness,
            vasopressor_sensitivity=vasopressor_sensitivity,
            antibiotic_susceptibility=antibiotic_susceptibility,
            septic_cardiomyopathy=septic_cardiomyopathy,
            egfr=egfr,
            sbp=sbp,
            dbp=dbp,
            hr=hr,
            rr=rr,
            spo2=spo2,
            temp_c=temp_c,
            wbc=wbc,
            lactate=lactate,
            hr_delta=hr_delta,
            lactate_delta=lactate_delta,
            temp_delta=temp_delta,
            t_now_min=0,
            current_map=current_map,
            current_lactate=lactate,
            risk_score=risk_score,
            risk_level=risk_level,
            sirs=sirs,
            qsofa=qsofa,
            sofa=sofa,
            survival=survival,
            time_to_stability_hr=time_to_stability,
            organ_dysfunction_renal=organ_dysfunction_renal,
            organ_dysfunction_hepatic=organ_dysfunction_hepatic,
            organ_dysfunction_cns=organ_dysfunction_cns,
            tags=tags
        )
    
    def generate_in_progress_scenario(
        self,
        risk_level: str,
        infection_source: str = None
    ) -> SepsisScenario:
        """Generate an in-progress scenario (1-12h post initial therapy)"""
        scenario = self.generate_fresh_scenario(risk_level, infection_source)
        
        t_now = self.rng.randint(60, 360)  # 1-6 hours post presentation
        scenario.t_now_min = t_now
        
        fluid_volume = self.rng.randint(1000, 2000)
        fluid_event = {
            "type": "fluid",
            "t_start_min": 0,
            "t_end_min": 45,
            "fluid_type": "crystalloid",
            "volume_ml": fluid_volume,
            "rate_ml_hr": fluid_volume * 60 // 45
        }
        scenario.treatment_events.append(fluid_event)
        scenario.cumulative_fluids_ml = fluid_volume
        
        map_increase = int(fluid_volume / 100 * scenario.fluid_responsiveness)
        scenario.delta_map_30m_post_fluids = map_increase
        scenario.current_map = scenario.current_map + map_increase
        
        antibiotic_timing = self.rng.randint(5, 60)
        antibiotic_agent = self.rng.choice(["piperacillin_tazobactam", "cefepime", "vancomycin"])
        antibiotic_event = {
            "type": "antibiotic",
            "t_start_min": antibiotic_timing,
            "agent": antibiotic_agent,
            "coverage": "broad",
            "dose": "standard",
            "route": "IV"
        }
        scenario.treatment_events.append(antibiotic_event)
        scenario.antibiotics_last_6h = [antibiotic_agent]
        
        if antibiotic_timing <= 60:
            lactate_clearance = 0.1 + (scenario.antibiotic_susceptibility * 0.2)
            scenario.lactate_clearance_6h = lactate_clearance
            scenario.current_lactate = scenario.lactate * (1 - lactate_clearance)
        
        if risk_level in ["HIGH", "CRITICAL"] and scenario.current_map < 65:
            pressor_timing = self.rng.randint(30, 90)
            pressor_dose = self.rng.uniform(0.05, 0.15)
            pressor_event = {
                "type": "vasopressor",
                "t_start_min": pressor_timing,
                "agent": "norepinephrine",
                "titration": [
                    {"t_min": pressor_timing, "dose_mcg_kg_min": pressor_dose}
                ]
            }
            scenario.treatment_events.append(pressor_event)
            scenario.current_pressors = {"norepinephrine": pressor_dose}
            scenario.pressors_high_dose_flag = pressor_dose > 0.2
            
            map_increase = int(pressor_dose * 100 * scenario.vasopressor_sensitivity)
            scenario.current_map += map_increase
        
        lab_event = {
            "type": "lab",
            "t_min": 60,
            "name": "lactate",
            "value": round(scenario.current_lactate, 1)
        }
        scenario.treatment_events.append(lab_event)
        
        scenario.tags = ["antibiotic_exposed", "in_progress"]
        if scenario.cumulative_fluids_ml > 2000:
            scenario.tags.append("fluid_loaded")
        if scenario.current_pressors:
            scenario.tags.append("on_pressors")
        if scenario.current_lactate > 4.0:
            scenario.tags.append("high_lactate")
        
        scenario.fluid_balance_ml_6h = scenario.cumulative_fluids_ml
        
        return scenario
    
    def generate_cohort(
        self,
        total_scenarios: int = 500,
        fresh_ratio: float = 0.6
    ) -> List[SepsisScenario]:
        """Generate a cohort of scenarios stratified by risk level and infection source"""
        scenarios = []
        
        risk_distribution = {
            "LOW": 0.20,
            "MODERATE": 0.25,
            "HIGH": 0.30,
            "CRITICAL": 0.25
        }
        
        infection_sources = [
            InfectionSource.URINARY_TRACT.value,
            InfectionSource.PULMONARY.value,
            InfectionSource.INTRA_ABDOMINAL.value,
            InfectionSource.SKIN_SOFT_TISSUE.value,
            InfectionSource.BLOODSTREAM.value
        ]
        
        num_fresh = int(total_scenarios * fresh_ratio)
        num_in_progress = total_scenarios - num_fresh
        
        for risk_level, proportion in risk_distribution.items():
            count = int(num_fresh * proportion)
            for _ in range(count):
                infection_source = self.rng.choice(infection_sources)
                scenario = self.generate_fresh_scenario(risk_level, infection_source)
                scenarios.append(scenario)
        
        for risk_level, proportion in risk_distribution.items():
            count = int(num_in_progress * proportion)
            for _ in range(count):
                infection_source = self.rng.choice(infection_sources)
                scenario = self.generate_in_progress_scenario(risk_level, infection_source)
                scenarios.append(scenario)
        
        self.rng.shuffle(scenarios)
        
        return scenarios


def save_scenarios_to_jsonl(scenarios: List[SepsisScenario], filepath: str):
    """Save scenarios to JSONL file (one scenario per line)"""
    with open(filepath, 'w') as f:
        for scenario in scenarios:
            json.dump(scenario.to_dict(), f)
            f.write('\n')


def load_scenarios_from_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Load scenarios from JSONL file"""
    scenarios = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                scenarios.append(json.loads(line))
    return scenarios


if __name__ == "__main__":
    generator = ScenarioGenerator(seed=42)
    scenarios = generator.generate_cohort(total_scenarios=500, fresh_ratio=0.6)
    
    output_path = "/home/ubuntu/sepsis/sepsis-backend/app/data/sepsis_scenarios.jsonl"
    save_scenarios_to_jsonl(scenarios, output_path)
    
    print(f"Generated {len(scenarios)} scenarios")
    print(f"Saved to {output_path}")
    
    risk_counts = {}
    fresh_count = 0
    in_progress_count = 0
    
    for scenario in scenarios:
        risk_level = scenario.risk_level
        risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        if "fresh_presentation" in scenario.tags:
            fresh_count += 1
        elif "in_progress" in scenario.tags:
            in_progress_count += 1
    
    print("\nRisk Level Distribution:")
    for risk_level, count in sorted(risk_counts.items()):
        print(f"  {risk_level}: {count} ({count/len(scenarios)*100:.1f}%)")
    
    print(f"\nFresh presentations: {fresh_count} ({fresh_count/len(scenarios)*100:.1f}%)")
    print(f"In-progress: {in_progress_count} ({in_progress_count/len(scenarios)*100:.1f}%)")
