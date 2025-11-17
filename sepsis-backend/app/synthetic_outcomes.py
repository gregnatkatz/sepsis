"""
Generate synthetic historical outcome data for Report tab
Shows AI/RL impact over 12 weeks with realistic trends
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np


def generate_synthetic_outcomes(weeks: int = 12) -> Dict[str, Any]:
    """
    Generate synthetic outcome data showing AI/RL improvement over time
    
    Trends:
    - Survival probability: starts at 0.72, improves to 0.85 (+18%)
    - Time to stability: starts at 18h, decreases to 12h (-33%)
    - Bundle compliance: starts at 65%, improves to 88% (+35%)
    - Early warning lead time: starts at 2h, improves to 4.5h (+125%)
    """
    
    start_date = datetime.utcnow() - timedelta(weeks=weeks)
    trending_data = []
    
    baseline_survival = 0.72
    baseline_time = 18.0
    baseline_bundle = 65.0
    baseline_leadtime = 2.0
    
    target_survival = 0.85
    target_time = 12.0
    target_bundle = 88.0
    target_leadtime = 4.5
    
    baseline_pathways = {"standard": 0.60, "aggressive": 0.25, "conservative": 0.15}
    target_pathways = {"ai_optimized": 0.55, "standard": 0.30, "aggressive": 0.10, "conservative": 0.05}
    
    for week in range(weeks + 1):
        progress = week / weeks
        
        noise_factor = 1.0 + random.uniform(-0.05, 0.05)
        s_curve = 1 / (1 + np.exp(-10 * (progress - 0.5)))
        
        survival_mean = baseline_survival + (target_survival - baseline_survival) * s_curve
        time_mean = baseline_time - (baseline_time - target_time) * s_curve
        bundle_mean = baseline_bundle + (target_bundle - baseline_bundle) * s_curve
        leadtime_mean = baseline_leadtime + (target_leadtime - baseline_leadtime) * s_curve
        
        def add_percentiles(mean, std_pct=0.08):
            std = mean * std_pct
            return {
                "mean": mean * noise_factor,
                "p25": max(0, (mean - std) * noise_factor),
                "p50": mean * noise_factor,
                "p75": min(1.0 if mean < 1 else 100, (mean + std) * noise_factor)
            }
        
        pathway_dist = {}
        for pathway, baseline_pct in baseline_pathways.items():
            target_pct = target_pathways.get(pathway, 0)
            pathway_dist[pathway] = baseline_pct + (target_pct - baseline_pct) * s_curve
        
        if progress > 0.3:
            pathway_dist["ai_optimized"] = target_pathways["ai_optimized"] * min(1.0, (progress - 0.3) / 0.7)
            total = sum(pathway_dist.values())
            pathway_dist = {k: v / total for k, v in pathway_dist.items()}
        
        sample_size = int(20 + 10 * week)
        
        week_date = start_date + timedelta(weeks=week)
        
        trending_data.append({
            "date": week_date.strftime("%Y-%m-%d"),
            "week": week,
            "survival_prob": add_percentiles(survival_mean, 0.06),
            "time_to_stability": add_percentiles(time_mean, 0.12),
            "bundle_compliance": add_percentiles(bundle_mean, 0.08),
            "early_warning_leadtime": add_percentiles(leadtime_mean, 0.15),
            "pathway_distribution": {k: round(v * 100, 1) for k, v in pathway_dist.items()},
            "sample_size": sample_size
        })
    
    baseline_data = trending_data[:4]
    baseline = {
        "survival_prob": np.mean([d["survival_prob"]["mean"] for d in baseline_data]),
        "time_to_stability": np.mean([d["time_to_stability"]["mean"] for d in baseline_data]),
        "bundle_compliance": np.mean([d["bundle_compliance"]["mean"] for d in baseline_data])
    }
    
    current_data = trending_data[-4:]
    current = {
        "survival_prob": np.mean([d["survival_prob"]["mean"] for d in current_data]),
        "time_to_stability": np.mean([d["time_to_stability"]["mean"] for d in current_data]),
        "bundle_compliance": np.mean([d["bundle_compliance"]["mean"] for d in current_data])
    }
    
    survival_delta = ((current["survival_prob"] - baseline["survival_prob"]) / baseline["survival_prob"]) * 100
    time_delta = ((baseline["time_to_stability"] - current["time_to_stability"]) / baseline["time_to_stability"]) * 100
    bundle_delta = ((current["bundle_compliance"] - baseline["bundle_compliance"]) / baseline["bundle_compliance"]) * 100
    
    return {
        "window": "weekly",
        "trending_data": trending_data,
        "baseline": baseline,
        "current": current,
        "deltas": {
            "survival_pct": round(survival_delta, 1),
            "time_reduction_pct": round(time_delta, 1),
            "bundle_improvement_pct": round(bundle_delta, 1)
        },
        "executive_summary": {
            "survival_improvement": f"+{survival_delta:.1f}%" if survival_delta > 0 else f"{survival_delta:.1f}%",
            "time_reduction": f"−{time_delta:.1f}%" if time_delta > 0 else f"+{abs(time_delta):.1f}%",
            "bundle_improvement": f"+{bundle_delta:.1f}%" if bundle_delta > 0 else f"{bundle_delta:.1f}%",
            "total_patients": sum(d["sample_size"] for d in trending_data),
            "weeks_tracked": weeks
        }
    }


def generate_pathway_adoption(weeks: int = 12) -> Dict[str, Any]:
    """Generate synthetic pathway adoption data over time"""
    
    start_date = datetime.utcnow() - timedelta(weeks=weeks)
    adoption_data = []
    
    for week in range(weeks + 1):
        progress = week / weeks
        s_curve = 1 / (1 + np.exp(-10 * (progress - 0.5)))
        
        pathways = {
            "standard": 60 - 30 * s_curve,  # Decreases from 60% to 30%
            "aggressive": 25 - 15 * s_curve,  # Decreases from 25% to 10%
            "conservative": 15 - 10 * s_curve,  # Decreases from 15% to 5%
            "ai_optimized": 0 + 55 * s_curve  # Increases from 0% to 55%
        }
        
        total = sum(pathways.values())
        pathways = {k: v / total * 100 for k, v in pathways.items()}
        
        week_date = start_date + timedelta(weeks=week)
        total_cases = int(20 + 10 * week)
        
        adoption_data.append({
            "date": week_date.strftime("%Y-%m-%d"),
            "pathways": {k: round(v, 1) for k, v in pathways.items()},
            "total_cases": total_cases
        })
    
    return {
        "window": "weekly",
        "adoption_data": adoption_data
    }
