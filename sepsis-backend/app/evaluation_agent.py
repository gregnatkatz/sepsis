"""
Evaluation Agent for running batch Monte Carlo evaluations across patients
Caches results in database for performance
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import FactEvalResults, EvaluationRun, DimPatient
from app.monte_carlo import run_monte_carlo
import asyncio


async def get_cached_evaluation(
    patient_id: str,
    samples: int,
    seed: Optional[int],
    db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """Get cached evaluation result from database"""
    content_hash = f"{patient_id}|{samples}|{seed or 0}"
    
    result = await db.execute(
        select(FactEvalResults)
        .where(FactEvalResults.content_hash == content_hash)
        .order_by(FactEvalResults.timestamp.desc())
        .limit(1)
    )
    cached = result.scalar_one_or_none()
    
    if cached:
        return json.loads(cached.json_result)
    
    return None


async def cache_evaluation_result(
    patient_id: str,
    samples: int,
    seed: Optional[int],
    result: Dict[str, Any],
    db: AsyncSession
) -> None:
    """Cache evaluation result to database"""
    content_hash = f"{patient_id}|{samples}|{seed or 0}"
    
    top_pathway = result.get("top_3_pathways", [{}])[0]
    expected_outcomes = top_pathway.get("expected_outcomes", {})
    
    survival_prob = expected_outcomes.get("survival_prob", {}).get("mean", 0)
    time_to_stability = expected_outcomes.get("time_to_stability_hr", {}).get("mean", 24)
    organ_preservation = expected_outcomes.get("organ_preservation_score", {}).get("mean", 50)
    
    time_score = max(0, 1 - (time_to_stability / 24))
    organ_score = organ_preservation / 100
    
    composite_score = (0.6 * survival_prob) + (0.25 * time_score) + (0.15 * organ_score)
    
    today = datetime.utcnow()
    date_key = int(today.strftime("%Y%m%d"))
    
    eval_result = FactEvalResults(
        patient_id=patient_id,
        time_key=date_key,
        timestamp=datetime.utcnow(),
        model="model-router",
        samples=samples,
        seed=seed,
        content_hash=content_hash,
        json_result=json.dumps(result),
        composite_score=composite_score,
        best_pathway=top_pathway.get("pathway_name", "Unknown"),
        survival_prob=survival_prob,
        time_to_stability=time_to_stability,
        organ_preservation=organ_preservation
    )
    
    db.add(eval_result)
    await db.commit()


async def run_evaluation_for_patient(
    patient_data: Dict[str, Any],
    samples: int,
    seed: Optional[int],
    db: AsyncSession,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Run Monte Carlo evaluation for a single patient with caching"""
    patient_id = patient_data["id"]
    
    if use_cache:
        cached = await get_cached_evaluation(patient_id, samples, seed, db)
        if cached:
            return cached
    
    result = await run_monte_carlo_simulation(patient_data, samples_per_pathway=samples, seed=seed)
    
    await cache_evaluation_result(patient_id, samples, seed, result, db)
    
    return result


async def run_batch_evaluation(
    patient_ids: Optional[List[str]],
    samples: int,
    seed: Optional[int],
    db: AsyncSession,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Run batch evaluation across multiple patients"""
    
    eval_run = EvaluationRun(
        patient_id=None if not patient_ids else ",".join(patient_ids),
        samples=samples,
        seed=seed,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(eval_run)
    await db.commit()
    await db.refresh(eval_run)
    
    try:
        if patient_ids:
            query = select(DimPatient).where(DimPatient.id.in_(patient_ids))
        else:
            query = select(DimPatient)
        
        result = await db.execute(query)
        patients = result.scalars().all()
        
        from app.main import get_patient_from_db
        
        results = []
        for patient in patients:
            patient_data = await get_patient_from_db(patient.id, db)
            if patient_data:
                eval_result = await run_evaluation_for_patient(
                    patient_data, samples, seed, db, use_cache
                )
                results.append({
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "result": eval_result
                })
        
        eval_run.status = "completed"
        eval_run.finished_at = datetime.utcnow()
        eval_run.results_count = len(results)
        await db.commit()
        
        return {
            "run_id": eval_run.id,
            "status": "completed",
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        eval_run.status = "failed"
        eval_run.finished_at = datetime.utcnow()
        eval_run.error = str(e)
        await db.commit()
        
        raise


async def get_evaluation_run_status(run_id: int, db: AsyncSession) -> Dict[str, Any]:
    """Get status of an evaluation run"""
    result = await db.execute(
        select(EvaluationRun).where(EvaluationRun.id == run_id)
    )
    eval_run = result.scalar_one_or_none()
    
    if not eval_run:
        return {"error": "Evaluation run not found"}
    
    return {
        "run_id": eval_run.id,
        "status": eval_run.status,
        "samples": eval_run.samples,
        "started_at": eval_run.started_at.isoformat() if eval_run.started_at else None,
        "finished_at": eval_run.finished_at.isoformat() if eval_run.finished_at else None,
        "results_count": eval_run.results_count,
        "error": eval_run.error
    }
