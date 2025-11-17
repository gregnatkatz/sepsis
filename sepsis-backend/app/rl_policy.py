"""
Reinforcement Learning Policy for Sepsis Treatment Pathway Selection
Uses contextual bandit approach to learn optimal treatment selection
"""

import numpy as np
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class PolicyMetrics:
    """Metrics for evaluating policy performance"""
    win_rate: float  # Fraction where chosen candidate is rank-1
    mean_utility: float  # Average utility of chosen candidates
    mean_regret: float  # Average difference from best candidate
    safety_score: float  # 1 - adverse_event_rate
    
    def to_dict(self):
        return asdict(self)


class ContextualBanditPolicy:
    """
    Contextual bandit policy for treatment pathway selection
    Learns which pathway works best for different patient phenotypes
    """
    
    def __init__(self, epsilon: float = 0.1, learning_rate: float = 0.01):
        """
        Args:
            epsilon: Exploration rate (0-1)
            learning_rate: Learning rate for weight updates
        """
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        
        self.candidate_weights = {}  # candidate_name -> feature_weights dict
        
        self.candidate_counts = defaultdict(int)
        self.candidate_rewards = defaultdict(list)
        
        self.training_history = []
    
    def extract_features(self, scenario: Dict[str, Any]) -> np.ndarray:
        """
        Extract feature vector from scenario for policy input
        
        Features:
        - Demographics: age (normalized), weight_kg (normalized)
        - Vitals: MAP, HR, SpO2, temp
        - Labs: lactate, WBC
        - Risk: risk_score, SOFA, qSOFA, SIRS
        - Comorbidities: CHF, CKD, COPD, DM, cirrhosis, immunosuppressed (binary)
        - Physiology: fluid_responsiveness, vasopressor_sensitivity, antibiotic_susceptibility
        - Infection: source (one-hot), resistance (one-hot)
        - Treatment history: cumulative_fluids (normalized), on_pressors (binary), antibiotic_exposed (binary)
        """
        features = []
        
        demographics = scenario.get('demographics', {})
        features.append(demographics.get('age', 65) / 100.0)  # Normalize to 0-1
        features.append(demographics.get('weight_kg', 70) / 100.0)
        
        presentation = scenario.get('presentation', {})
        t0_vitals = presentation.get('t0_vitals', {})
        sbp = t0_vitals.get('sbp', 90)
        dbp = t0_vitals.get('dbp', 60)
        map_val = (sbp + 2 * dbp) / 3
        features.append(map_val / 100.0)  # Normalize MAP
        features.append(t0_vitals.get('hr', 100) / 150.0)  # Normalize HR
        features.append(t0_vitals.get('spo2', 92) / 100.0)  # Normalize SpO2
        features.append((t0_vitals.get('temp_c', 38.0) - 36.0) / 5.0)  # Normalize temp
        
        t0_labs = presentation.get('t0_labs', {})
        features.append(min(t0_labs.get('lactate', 2.0) / 10.0, 1.0))  # Normalize lactate
        features.append(min(t0_labs.get('wbc', 15.0) / 30.0, 1.0))  # Normalize WBC
        
        risk = scenario.get('risk', {})
        features.append(risk.get('risk_score', 50) / 100.0)
        features.append(risk.get('sofa', 4) / 15.0)
        features.append(risk.get('qsofa', 1) / 3.0)
        features.append(risk.get('sirs', 2) / 4.0)
        
        comorbidities = demographics.get('comorbidities', [])
        features.append(1.0 if 'CHF' in comorbidities else 0.0)
        features.append(1.0 if 'CKD' in comorbidities else 0.0)
        features.append(1.0 if 'COPD' in comorbidities else 0.0)
        features.append(1.0 if 'DM' in comorbidities else 0.0)
        features.append(1.0 if 'cirrhosis' in comorbidities else 0.0)
        features.append(1.0 if 'immunosuppressed' in comorbidities else 0.0)
        
        physiology = scenario.get('physiology_baseline', {})
        features.append(physiology.get('fluid_responsiveness', 0.6))
        features.append(physiology.get('vasopressor_sensitivity', 0.7))
        features.append(physiology.get('antibiotic_susceptibility', 0.85))
        
        infection = scenario.get('infection', {})
        source = infection.get('source', 'unknown')
        features.append(1.0 if source == 'urinary_tract' else 0.0)
        features.append(1.0 if source == 'pulmonary' else 0.0)
        features.append(1.0 if source == 'intra_abdominal' else 0.0)
        features.append(1.0 if source == 'skin_soft_tissue' else 0.0)
        features.append(1.0 if source == 'bloodstream' else 0.0)
        
        resistance = infection.get('resistance_profile', 'susceptible')
        features.append(1.0 if resistance == 'esbl' else 0.0)
        features.append(1.0 if resistance == 'mrsa' else 0.0)
        features.append(1.0 if resistance == 'vre' else 0.0)
        features.append(1.0 if resistance == 'mdr' else 0.0)
        
        current_state = scenario.get('current_state', {})
        features.append(min(current_state.get('cumulative_fluids_ml', 0) / 3000.0, 1.0))
        features.append(1.0 if current_state.get('current_pressors', {}) else 0.0)
        features.append(1.0 if current_state.get('antibiotics_last_6h', []) else 0.0)
        
        features.append(1.0)
        
        return np.array(features, dtype=np.float32)
    
    def predict_utility(self, features: np.ndarray, candidate_name: str) -> float:
        """Predict expected utility for a candidate given features"""
        if candidate_name not in self.candidate_weights:
            self.candidate_weights[candidate_name] = np.random.randn(len(features)) * 0.01
        
        weights = self.candidate_weights[candidate_name]
        return float(np.dot(weights, features))
    
    def select_action(
        self,
        scenario: Dict[str, Any],
        candidate_names: List[str],
        explore: bool = True
    ) -> str:
        """
        Select a treatment candidate for the given scenario
        
        Args:
            scenario: Patient scenario dict
            candidate_names: List of available candidate names
            explore: Whether to use epsilon-greedy exploration
        
        Returns:
            Selected candidate name
        """
        features = self.extract_features(scenario)
        
        if explore and np.random.random() < self.epsilon:
            return np.random.choice(candidate_names)
        
        utilities = {name: self.predict_utility(features, name) for name in candidate_names}
        return max(utilities, key=utilities.get)
    
    def update(
        self,
        scenario: Dict[str, Any],
        candidate_name: str,
        reward: float
    ):
        """
        Update policy weights based on observed reward
        
        Args:
            scenario: Patient scenario dict
            candidate_name: Chosen candidate name
            reward: Observed utility/reward
        """
        features = self.extract_features(scenario)
        
        predicted = self.predict_utility(features, candidate_name)
        
        error = reward - predicted
        gradient = self.learning_rate * error * features
        
        self.candidate_weights[candidate_name] += gradient
        
        self.candidate_counts[candidate_name] += 1
        self.candidate_rewards[candidate_name].append(reward)
        
        self.training_history.append({
            'candidate': candidate_name,
            'reward': reward,
            'predicted': predicted,
            'error': error
        })
    
    def evaluate(
        self,
        scenarios: List[Dict[str, Any]],
        monte_carlo_results: Dict[str, List[Dict[str, Any]]]
    ) -> PolicyMetrics:
        """
        Evaluate policy performance on a set of scenarios
        
        Args:
            scenarios: List of scenario dicts
            monte_carlo_results: Dict mapping scenario_id to list of MC results per candidate
        
        Returns:
            PolicyMetrics with win_rate, mean_utility, mean_regret, safety_score
        """
        wins = 0
        total_utility = 0.0
        total_regret = 0.0
        total_adverse_events = 0.0
        
        for scenario in scenarios:
            scenario_id = scenario['scenario_id']
            results = monte_carlo_results.get(scenario_id, [])
            
            if not results:
                continue
            
            candidate_names = [r['candidate_name'] for r in results]
            
            chosen_name = self.select_action(scenario, candidate_names, explore=False)
            
            chosen_result = next((r for r in results if r['candidate_name'] == chosen_name), None)
            if not chosen_result:
                continue
            
            chosen_utility = chosen_result['expected_utility']
            
            best_result = max(results, key=lambda r: r['expected_utility'])
            best_utility = best_result['expected_utility']
            
            if chosen_name == best_result['candidate_name']:
                wins += 1
            
            total_utility += chosen_utility
            total_regret += (best_utility - chosen_utility)
            total_adverse_events += chosen_result.get('adverse_event_rate', 0.0)
        
        n = len(scenarios)
        return PolicyMetrics(
            win_rate=wins / n if n > 0 else 0.0,
            mean_utility=total_utility / n if n > 0 else 0.0,
            mean_regret=total_regret / n if n > 0 else 0.0,
            safety_score=1.0 - (total_adverse_events / n) if n > 0 else 1.0
        )
    
    def get_feature_importance(self, candidate_name: str) -> Dict[str, float]:
        """Get feature importance (absolute weight values) for a candidate"""
        if candidate_name not in self.candidate_weights:
            return {}
        
        weights = self.candidate_weights[candidate_name]
        feature_names = [
            'age', 'weight', 'MAP', 'HR', 'SpO2', 'temp',
            'lactate', 'WBC', 'risk_score', 'SOFA', 'qSOFA', 'SIRS',
            'CHF', 'CKD', 'COPD', 'DM', 'cirrhosis', 'immunosuppressed',
            'fluid_responsiveness', 'vasopressor_sensitivity', 'antibiotic_susceptibility',
            'source_UTI', 'source_pneumonia', 'source_abdominal', 'source_skin', 'source_bloodstream',
            'resistance_ESBL', 'resistance_MRSA', 'resistance_VRE', 'resistance_MDR',
            'cumulative_fluids', 'on_pressors', 'antibiotic_exposed',
            'bias'
        ]
        
        importance = {}
        for i, name in enumerate(feature_names):
            if i < len(weights):
                importance[name] = abs(float(weights[i]))
        
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def save(self, filepath: str):
        """Save policy to file"""
        data = {
            'epsilon': self.epsilon,
            'learning_rate': self.learning_rate,
            'candidate_weights': {k: v.tolist() for k, v in self.candidate_weights.items()},
            'candidate_counts': dict(self.candidate_counts),
            'candidate_rewards': {k: v for k, v in self.candidate_rewards.items()}
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, filepath: str):
        """Load policy from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.epsilon = data['epsilon']
        self.learning_rate = data['learning_rate']
        self.candidate_weights = {k: np.array(v) for k, v in data['candidate_weights'].items()}
        self.candidate_counts = defaultdict(int, data['candidate_counts'])
        self.candidate_rewards = defaultdict(list, data['candidate_rewards'])


class BaselinePolicy:
    """
    Baseline policy that always selects the first candidate (rule-based)
    Used for comparison with RL policy
    """
    
    def select_action(
        self,
        scenario: Dict[str, Any],
        candidate_names: List[str],
        explore: bool = True
    ) -> str:
        """Always select first candidate"""
        return candidate_names[0] if candidate_names else None
    
    def evaluate(
        self,
        scenarios: List[Dict[str, Any]],
        monte_carlo_results: Dict[str, List[Dict[str, Any]]]
    ) -> PolicyMetrics:
        """Evaluate baseline policy performance"""
        wins = 0
        total_utility = 0.0
        total_regret = 0.0
        total_adverse_events = 0.0
        
        for scenario in scenarios:
            scenario_id = scenario['scenario_id']
            results = monte_carlo_results.get(scenario_id, [])
            
            if not results:
                continue
            
            chosen_result = results[0]
            chosen_utility = chosen_result['expected_utility']
            
            best_result = max(results, key=lambda r: r['expected_utility'])
            best_utility = best_result['expected_utility']
            
            if chosen_result['candidate_name'] == best_result['candidate_name']:
                wins += 1
            
            total_utility += chosen_utility
            total_regret += (best_utility - chosen_utility)
            total_adverse_events += chosen_result.get('adverse_event_rate', 0.0)
        
        n = len(scenarios)
        return PolicyMetrics(
            win_rate=wins / n if n > 0 else 0.0,
            mean_utility=total_utility / n if n > 0 else 0.0,
            mean_regret=total_regret / n if n > 0 else 0.0,
            safety_score=1.0 - (total_adverse_events / n) if n > 0 else 1.0
        )
