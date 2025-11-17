"""
Batch Evaluation Framework for RL Policy Learning
Demonstrates how RL improves treatment selection over time
"""

import json
import time
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

from app.scenario_generator import load_scenarios_from_jsonl
from app.monte_carlo import generate_candidate_treatments, run_monte_carlo, rank_pathways
from app.rl_policy import ContextualBanditPolicy, BaselinePolicy, PolicyMetrics


@dataclass
class BatchResults:
    """Results from evaluating a batch of scenarios"""
    batch_id: int
    num_scenarios: int
    policy_metrics: PolicyMetrics
    baseline_metrics: PolicyMetrics
    improvement: Dict[str, float]  # RL vs baseline improvement
    top_candidates: Dict[str, int]  # Candidate name -> selection count
    stratified_metrics: Dict[str, Dict[str, float]]  # By risk level and infection source
    timestamp: str
    
    def to_dict(self):
        return {
            'batch_id': self.batch_id,
            'num_scenarios': self.num_scenarios,
            'policy_metrics': self.policy_metrics.to_dict(),
            'baseline_metrics': self.baseline_metrics.to_dict(),
            'improvement': self.improvement,
            'top_candidates': self.top_candidates,
            'stratified_metrics': self.stratified_metrics,
            'timestamp': self.timestamp
        }


class BatchEvaluator:
    """
    Evaluates RL policy across multiple batches to show learning curves
    """
    
    def __init__(self, scenarios_path: str, batch_size: int = 100):
        """
        Args:
            scenarios_path: Path to JSONL file with scenarios
            batch_size: Number of scenarios per batch
        """
        self.scenarios_path = scenarios_path
        self.batch_size = batch_size
        self.scenarios = load_scenarios_from_jsonl(scenarios_path)
        self.num_batches = len(self.scenarios) // batch_size
        
        self.rl_policy = ContextualBanditPolicy(epsilon=0.1, learning_rate=0.01)
        self.baseline_policy = BaselinePolicy()
        
        self.batch_results = []
        self.monte_carlo_cache = {}  # Cache MC results per scenario
    
    def run_monte_carlo_for_scenario(
        self,
        scenario: Dict[str, Any],
        samples: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Run Monte Carlo simulation for all candidates in a scenario
        
        Returns:
            List of MC results per candidate with expected_utility
        """
        scenario_id = scenario['scenario_id']
        
        if scenario_id in self.monte_carlo_cache:
            return self.monte_carlo_cache[scenario_id]
        
        patient = self._scenario_to_patient(scenario)
        
        candidates = generate_candidate_treatments(patient)
        
        mc_results = []
        for candidate in candidates:
            result = run_monte_carlo(patient, candidate, samples=samples, seed=scenario['seed'])
            mc_results.append(result)
        
        ranked = rank_pathways(mc_results)
        
        self.monte_carlo_cache[scenario_id] = ranked
        
        return ranked
    
    def _scenario_to_patient(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Convert scenario format to patient format for MC engine"""
        presentation = scenario.get('presentation', {})
        t0_vitals = presentation.get('t0_vitals', {})
        t0_labs = presentation.get('t0_labs', {})
        risk = scenario.get('risk', {})
        ground_truth = scenario.get('ground_truth', {})
        physiology = scenario.get('physiology_baseline', {})
        
        sbp = t0_vitals.get('sbp', 90)
        dbp = t0_vitals.get('dbp', 60)
        bp = f"{sbp}/{dbp}"
        
        return {
            'id': scenario['scenario_id'],
            'name': f"Patient {scenario['scenario_id']}",
            'risk_score': risk.get('risk_score', 50),
            'risk_level': risk.get('risk_level', 'MODERATE'),
            'vitals': {
                'current': {
                    'blood_pressure': bp,
                    'heart_rate': t0_vitals.get('hr', 100),
                    'respiratory_rate': t0_vitals.get('rr', 20),
                    'temperature': t0_vitals.get('temp_c', 38.0),
                    'oxygen_saturation': t0_vitals.get('spo2', 92)
                }
            },
            'labs': {
                'current': {
                    'lactate': t0_labs.get('lactate', 2.0),
                    'white_blood_cell_count': t0_labs.get('wbc', 15.0)
                }
            },
            'ground_truth': {
                'sofa_score': risk.get('sofa', 4),
                'septic_cardiomyopathy': physiology.get('septic_cardiomyopathy', False)
            }
        }
    
    def train_on_batch(
        self,
        batch_scenarios: List[Dict[str, Any]],
        samples: int = 100
    ):
        """
        Train RL policy on a batch of scenarios
        
        Args:
            batch_scenarios: List of scenario dicts
            samples: Monte Carlo samples per candidate
        """
        for scenario in batch_scenarios:
            mc_results = self.run_monte_carlo_for_scenario(scenario, samples=samples)
            
            candidate_names = [r['candidate_name'] for r in mc_results]
            
            chosen_name = self.rl_policy.select_action(scenario, candidate_names, explore=True)
            
            chosen_result = next((r for r in mc_results if r['candidate_name'] == chosen_name), None)
            if chosen_result:
                reward = chosen_result['expected_utility']
                
                self.rl_policy.update(scenario, chosen_name, reward)
    
    def evaluate_on_batch(
        self,
        batch_scenarios: List[Dict[str, Any]],
        batch_id: int,
        samples: int = 100
    ) -> BatchResults:
        """
        Evaluate both RL and baseline policies on a batch
        
        Args:
            batch_scenarios: List of scenario dicts
            batch_id: Batch identifier
            samples: Monte Carlo samples per candidate
        
        Returns:
            BatchResults with metrics and comparisons
        """
        monte_carlo_results = {}
        for scenario in batch_scenarios:
            scenario_id = scenario['scenario_id']
            mc_results = self.run_monte_carlo_for_scenario(scenario, samples=samples)
            monte_carlo_results[scenario_id] = mc_results
        
        rl_metrics = self.rl_policy.evaluate(batch_scenarios, monte_carlo_results)
        
        baseline_metrics = self.baseline_policy.evaluate(batch_scenarios, monte_carlo_results)
        
        improvement = {
            'win_rate': rl_metrics.win_rate - baseline_metrics.win_rate,
            'mean_utility': rl_metrics.mean_utility - baseline_metrics.mean_utility,
            'mean_regret': baseline_metrics.mean_regret - rl_metrics.mean_regret,  # Lower is better
            'safety_score': rl_metrics.safety_score - baseline_metrics.safety_score
        }
        
        top_candidates = {}
        for scenario in batch_scenarios:
            scenario_id = scenario['scenario_id']
            results = monte_carlo_results.get(scenario_id, [])
            if results:
                candidate_names = [r['candidate_name'] for r in results]
                chosen = self.rl_policy.select_action(scenario, candidate_names, explore=False)
                top_candidates[chosen] = top_candidates.get(chosen, 0) + 1
        
        stratified_metrics = self._compute_stratified_metrics(
            batch_scenarios, monte_carlo_results
        )
        
        return BatchResults(
            batch_id=batch_id,
            num_scenarios=len(batch_scenarios),
            policy_metrics=rl_metrics,
            baseline_metrics=baseline_metrics,
            improvement=improvement,
            top_candidates=top_candidates,
            stratified_metrics=stratified_metrics,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def _compute_stratified_metrics(
        self,
        scenarios: List[Dict[str, Any]],
        monte_carlo_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Dict[str, float]]:
        """Compute metrics stratified by risk level and infection source"""
        stratified = {}
        
        risk_groups = {}
        for scenario in scenarios:
            risk_level = scenario.get('risk', {}).get('risk_level', 'MODERATE')
            if risk_level not in risk_groups:
                risk_groups[risk_level] = []
            risk_groups[risk_level].append(scenario)
        
        for risk_level, group_scenarios in risk_groups.items():
            if group_scenarios:
                metrics = self.rl_policy.evaluate(group_scenarios, monte_carlo_results)
                stratified[f'risk_{risk_level}'] = {
                    'win_rate': metrics.win_rate,
                    'mean_utility': metrics.mean_utility,
                    'count': len(group_scenarios)
                }
        
        source_groups = {}
        for scenario in scenarios:
            source = scenario.get('infection', {}).get('source', 'unknown')
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(scenario)
        
        for source, group_scenarios in source_groups.items():
            if group_scenarios and len(group_scenarios) >= 5:  # Only if enough samples
                metrics = self.rl_policy.evaluate(group_scenarios, monte_carlo_results)
                stratified[f'source_{source}'] = {
                    'win_rate': metrics.win_rate,
                    'mean_utility': metrics.mean_utility,
                    'count': len(group_scenarios)
                }
        
        return stratified
    
    def run_sequential_batches(
        self,
        num_batches: int = 5,
        samples: int = 100,
        train_on_previous: bool = True
    ) -> List[BatchResults]:
        """
        Run sequential batch evaluation to demonstrate learning curves
        
        Args:
            num_batches: Number of batches to evaluate
            samples: Monte Carlo samples per candidate
            train_on_previous: Whether to train on previous batches before evaluating next
        
        Returns:
            List of BatchResults showing improvement over time
        """
        results = []
        
        for batch_id in range(num_batches):
            start_idx = batch_id * self.batch_size
            end_idx = start_idx + self.batch_size
            batch_scenarios = self.scenarios[start_idx:end_idx]
            
            if not batch_scenarios:
                break
            
            print(f"\n{'='*80}")
            print(f"Batch {batch_id + 1}/{num_batches} - {len(batch_scenarios)} scenarios")
            print(f"{'='*80}")
            
            if batch_id == 0:
                print("Training on batch 1...")
                self.train_on_batch(batch_scenarios, samples=samples)
                print("Evaluating batch 1...")
                batch_result = self.evaluate_on_batch(batch_scenarios, batch_id + 1, samples=samples)
            else:
                print(f"Evaluating batch {batch_id + 1} (holdout)...")
                batch_result = self.evaluate_on_batch(batch_scenarios, batch_id + 1, samples=samples)
                
                if train_on_previous:
                    print(f"Training on batch {batch_id + 1}...")
                    self.train_on_batch(batch_scenarios, samples=samples)
            
            results.append(batch_result)
            
            print(f"\nRL Policy Metrics:")
            print(f"  Win Rate: {batch_result.policy_metrics.win_rate:.1%}")
            print(f"  Mean Utility: {batch_result.policy_metrics.mean_utility:.3f}")
            print(f"  Mean Regret: {batch_result.policy_metrics.mean_regret:.3f}")
            print(f"  Safety Score: {batch_result.policy_metrics.safety_score:.3f}")
            
            print(f"\nBaseline Policy Metrics:")
            print(f"  Win Rate: {batch_result.baseline_metrics.win_rate:.1%}")
            print(f"  Mean Utility: {batch_result.baseline_metrics.mean_utility:.3f}")
            print(f"  Mean Regret: {batch_result.baseline_metrics.mean_regret:.3f}")
            
            print(f"\nImprovement (RL vs Baseline):")
            print(f"  Win Rate: +{batch_result.improvement['win_rate']:.1%}")
            print(f"  Mean Utility: +{batch_result.improvement['mean_utility']:.3f}")
            print(f"  Regret Reduction: {batch_result.improvement['mean_regret']:.3f}")
        
        return results
    
    def generate_learning_curves(self, results: List[BatchResults]) -> Dict[str, Any]:
        """Generate learning curve data for visualization"""
        batches = [r.batch_id for r in results]
        
        return {
            'batches': batches,
            'rl_win_rate': [r.policy_metrics.win_rate for r in results],
            'baseline_win_rate': [r.baseline_metrics.win_rate for r in results],
            'rl_utility': [r.policy_metrics.mean_utility for r in results],
            'baseline_utility': [r.baseline_metrics.mean_utility for r in results],
            'rl_regret': [r.policy_metrics.mean_regret for r in results],
            'baseline_regret': [r.baseline_metrics.mean_regret for r in results],
            'improvement_win_rate': [r.improvement['win_rate'] for r in results],
            'improvement_utility': [r.improvement['mean_utility'] for r in results]
        }
    
    def generate_insights_report(self, results: List[BatchResults]) -> Dict[str, Any]:
        """
        Generate insights report showing what RL learned
        
        Returns:
            Dict with insights about policy improvements and feature importance
        """
        first_batch = results[0]
        last_batch = results[-1]
        
        overall_improvement = {
            'win_rate_change': last_batch.policy_metrics.win_rate - first_batch.policy_metrics.win_rate,
            'utility_change': last_batch.policy_metrics.mean_utility - first_batch.policy_metrics.mean_utility,
            'regret_reduction': first_batch.policy_metrics.mean_regret - last_batch.policy_metrics.mean_regret
        }
        
        all_candidates = {}
        for result in results:
            for candidate, count in result.top_candidates.items():
                all_candidates[candidate] = all_candidates.get(candidate, 0) + count
        
        feature_importance = {}
        for candidate in all_candidates.keys():
            importance = self.rl_policy.get_feature_importance(candidate)
            feature_importance[candidate] = dict(list(importance.items())[:10])  # Top 10 features
        
        stratified_insights = {}
        for result in results[-1:]:  # Use last batch
            for key, metrics in result.stratified_metrics.items():
                stratified_insights[key] = metrics
        
        return {
            'overall_improvement': overall_improvement,
            'candidate_preferences': all_candidates,
            'feature_importance': feature_importance,
            'stratified_insights': stratified_insights,
            'num_batches': len(results),
            'total_scenarios': sum(r.num_scenarios for r in results)
        }
    
    def save_results(self, results: List[BatchResults], output_path: str):
        """Save batch results to JSON file"""
        data = {
            'batch_results': [r.to_dict() for r in results],
            'learning_curves': self.generate_learning_curves(results),
            'insights_report': self.generate_insights_report(results),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ Results saved to {output_path}")
    
    def save_comprehensive_table(self, output_path: str):
        """Save comprehensive CSV table of all scenario results"""
        import csv
        
        rows = []
        for scenario_id, mc_results in self.monte_carlo_cache.items():
            scenario = next((s for s in self.scenarios if s['scenario_id'] == scenario_id), None)
            if not scenario:
                continue
            
            risk_level = scenario.get('risk', {}).get('risk_level', 'UNKNOWN')
            infection_source = scenario.get('infection', {}).get('source', 'unknown')
            
            for result in mc_results:
                candidate_names = [r['candidate_name'] for r in mc_results]
                chosen_by_rl = self.rl_policy.select_action(scenario, candidate_names, explore=False)
                chosen_by_baseline = self.baseline_policy.select_action(scenario, candidate_names, explore=False)
                
                rows.append({
                    'scenario_id': scenario_id,
                    'risk_level': risk_level,
                    'infection_source': infection_source,
                    'candidate_name': result['candidate_name'],
                    'expected_utility': result['expected_utility'],
                    'survival_mean': result['expected_outcomes']['survival_prob']['mean'],
                    'time_to_stability_mean': result['expected_outcomes']['time_to_stability_hr']['mean'],
                    'organ_preservation_mean': result['expected_outcomes']['organ_preservation_score']['mean'],
                    'adverse_event_rate': result['adverse_event_rate'],
                    'chosen_by_rl': 1 if result['candidate_name'] == chosen_by_rl else 0,
                    'chosen_by_baseline': 1 if result['candidate_name'] == chosen_by_baseline else 0
                })
        
        with open(output_path, 'w', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        print(f"✅ Comprehensive table saved to {output_path}")


if __name__ == "__main__":
    evaluator = BatchEvaluator(
        scenarios_path="/home/ubuntu/sepsis/sepsis-backend/app/data/sepsis_scenarios.jsonl",
        batch_size=100
    )
    
    print("="*80)
    print("RL POLICY BATCH EVALUATION")
    print("Demonstrating how RL improves treatment selection over time")
    print("="*80)
    
    results = evaluator.run_sequential_batches(num_batches=5, samples=100, train_on_previous=True)
    
    evaluator.save_results(
        results,
        "/home/ubuntu/sepsis/sepsis-backend/app/data/rl_batch_results.json"
    )
    
    evaluator.save_comprehensive_table(
        "/home/ubuntu/sepsis/sepsis-backend/app/data/comprehensive_table.csv"
    )
    
    print("\n" + "="*80)
    print("EVALUATION COMPLETE")
    print("="*80)
