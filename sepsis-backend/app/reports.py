"""
Report generation for trending analytics and AI/RL impact visualization
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import FactOutcomes, FactEvalResults, DimPatient, DimTime
import json


async def get_trending_outcomes(
    window: str,
    cohort_filter: Optional[Dict[str, Any]],
    db: AsyncSession
) -> Dict[str, Any]:
    """Get trending outcomes data for Report tab"""
    
    now = datetime.utcnow()
    if window == "weekly":
        start_date = now - timedelta(weeks=12)  # 12 weeks of data
        group_by_days = 7
    elif window == "monthly":
        start_date = now - timedelta(days=180)  # 6 months of data
        group_by_days = 30
    else:
        start_date = now - timedelta(weeks=12)
        group_by_days = 7
    
    query = select(FactOutcomes).where(FactOutcomes.timestamp >= start_date)
    
    if cohort_filter:
        if "risk_level" in cohort_filter:
            query = query.join(DimPatient, FactOutcomes.patient_id == DimPatient.id)
            query = query.where(DimPatient.risk_level == cohort_filter["risk_level"])
    
    result = await db.execute(query.order_by(FactOutcomes.timestamp))
    outcomes = result.scalars().all()
    
    time_buckets = {}
    for outcome in outcomes:
        bucket_date = outcome.timestamp - timedelta(days=outcome.timestamp.weekday())
        bucket_key = bucket_date.strftime("%Y-%m-%d")
        
        if bucket_key not in time_buckets:
            time_buckets[bucket_key] = {
                "date": bucket_key,
                "survival_probs": [],
                "time_to_stability": [],
                "bundle_compliance": [],
                "early_warning_leadtime": [],
                "pathways": []
            }
        
        if outcome.survived is not None:
            time_buckets[bucket_key]["survival_probs"].append(outcome.survived)
        if outcome.time_to_stability_hr is not None:
            time_buckets[bucket_key]["time_to_stability"].append(outcome.time_to_stability_hr)
        if outcome.bundle_compliance_pct is not None:
            time_buckets[bucket_key]["bundle_compliance"].append(outcome.bundle_compliance_pct)
        if outcome.early_warning_leadtime_hr is not None:
            time_buckets[bucket_key]["early_warning_leadtime"].append(outcome.early_warning_leadtime_hr)
        if outcome.pathway_chosen:
            time_buckets[bucket_key]["pathways"].append(outcome.pathway_chosen)
    
    trending_data = []
    for bucket_key in sorted(time_buckets.keys()):
        bucket = time_buckets[bucket_key]
        
        survival_data = bucket["survival_probs"]
        time_data = bucket["time_to_stability"]
        bundle_data = bucket["bundle_compliance"]
        leadtime_data = bucket["early_warning_leadtime"]
        
        def calc_stats(data):
            if not data:
                return {"mean": 0, "p25": 0, "p50": 0, "p75": 0}
            sorted_data = sorted(data)
            n = len(sorted_data)
            return {
                "mean": sum(data) / n,
                "p25": sorted_data[int(n * 0.25)],
                "p50": sorted_data[int(n * 0.50)],
                "p75": sorted_data[int(n * 0.75)]
            }
        
        pathway_counts = {}
        for pathway in bucket["pathways"]:
            pathway_counts[pathway] = pathway_counts.get(pathway, 0) + 1
        
        trending_data.append({
            "date": bucket_key,
            "survival_prob": calc_stats(survival_data),
            "time_to_stability": calc_stats(time_data),
            "bundle_compliance": calc_stats(bundle_data),
            "early_warning_leadtime": calc_stats(leadtime_data),
            "pathway_distribution": pathway_counts,
            "sample_size": len(survival_data)
        })
    
    baseline_data = trending_data[:4] if len(trending_data) >= 4 else trending_data
    baseline_survival = sum(d["survival_prob"]["mean"] for d in baseline_data) / len(baseline_data) if baseline_data else 0
    baseline_time = sum(d["time_to_stability"]["mean"] for d in baseline_data) / len(baseline_data) if baseline_data else 0
    baseline_bundle = sum(d["bundle_compliance"]["mean"] for d in baseline_data) / len(baseline_data) if baseline_data else 0
    
    current_data = trending_data[-4:] if len(trending_data) >= 4 else trending_data
    current_survival = sum(d["survival_prob"]["mean"] for d in current_data) / len(current_data) if current_data else 0
    current_time = sum(d["time_to_stability"]["mean"] for d in current_data) / len(current_data) if current_data else 0
    current_bundle = sum(d["bundle_compliance"]["mean"] for d in current_data) / len(current_data) if current_data else 0
    
    survival_delta = ((current_survival - baseline_survival) / baseline_survival * 100) if baseline_survival > 0 else 0
    time_delta = ((baseline_time - current_time) / baseline_time * 100) if baseline_time > 0 else 0  # Inverted: reduction is good
    bundle_delta = ((current_bundle - baseline_bundle) / baseline_bundle * 100) if baseline_bundle > 0 else 0
    
    return {
        "window": window,
        "trending_data": trending_data,
        "baseline": {
            "survival_prob": baseline_survival,
            "time_to_stability": baseline_time,
            "bundle_compliance": baseline_bundle
        },
        "current": {
            "survival_prob": current_survival,
            "time_to_stability": current_time,
            "bundle_compliance": current_bundle
        },
        "deltas": {
            "survival_pct": round(survival_delta, 1),
            "time_reduction_pct": round(time_delta, 1),
            "bundle_improvement_pct": round(bundle_delta, 1)
        },
        "executive_summary": {
            "survival_improvement": f"+{survival_delta:.1f}%" if survival_delta > 0 else f"{survival_delta:.1f}%",
            "time_reduction": f"−{time_delta:.1f}h" if time_delta > 0 else f"+{abs(time_delta):.1f}h",
            "bundle_improvement": f"+{bundle_delta:.1f}%" if bundle_delta > 0 else f"{bundle_delta:.1f}%"
        }
    }


async def get_pathway_adoption(
    window: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """Get pathway adoption trends over time"""
    
    now = datetime.utcnow()
    if window == "weekly":
        start_date = now - timedelta(weeks=12)
    else:
        start_date = now - timedelta(days=180)
    
    query = select(FactOutcomes).where(FactOutcomes.timestamp >= start_date)
    result = await db.execute(query.order_by(FactOutcomes.timestamp))
    outcomes = result.scalars().all()
    
    time_buckets = {}
    for outcome in outcomes:
        bucket_date = outcome.timestamp - timedelta(days=outcome.timestamp.weekday())
        bucket_key = bucket_date.strftime("%Y-%m-%d")
        
        if bucket_key not in time_buckets:
            time_buckets[bucket_key] = {}
        
        pathway = outcome.pathway_chosen or "unknown"
        time_buckets[bucket_key][pathway] = time_buckets[bucket_key].get(pathway, 0) + 1
    
    adoption_data = []
    for bucket_key in sorted(time_buckets.keys()):
        bucket = time_buckets[bucket_key]
        total = sum(bucket.values())
        
        pathway_pcts = {
            pathway: (count / total * 100) if total > 0 else 0
            for pathway, count in bucket.items()
        }
        
        adoption_data.append({
            "date": bucket_key,
            "pathways": pathway_pcts,
            "total_cases": total
        })
    
    return {
        "window": window,
        "adoption_data": adoption_data
    }
