"""
Generate comprehensive validation reports for both Kaggle and Synthetic datasets
"""

import asyncio
import numpy as np
from sqlalchemy import select
from app.database import AsyncSessionLocal, DimPatient
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix
import json

async def generate_validation_reports():
    """Generate validation metrics for both datasets"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DimPatient.risk_score, DimPatient.cohort_tags, DimPatient.id)
        )
        data = result.all()
        
        kaggle_data = []
        synthetic_data = []
        
        for row in data:
            cohort_tags = json.loads(row.cohort_tags) if row.cohort_tags else []
            
            sepsis_label = 0
            for tag in cohort_tags:
                if tag.startswith('sepsis_'):
                    sepsis_label = int(tag.split('_')[1])
                    break
            
            is_kaggle = 'kaggle' in cohort_tags
            is_synthetic = 'synthetic' in cohort_tags
            
            if is_kaggle:
                kaggle_data.append({
                    'risk_score': row.risk_score,
                    'sepsis_label': sepsis_label
                })
            elif is_synthetic:
                synthetic_data.append({
                    'risk_score': row.risk_score,
                    'sepsis_label': sepsis_label
                })
        
        print(f"Kaggle patients: {len(kaggle_data)}")
        print(f"Synthetic patients: {len(synthetic_data)}")
        
        reports = {}
        
        for dataset_name, dataset in [('kaggle', kaggle_data), ('synthetic', synthetic_data)]:
            if not dataset:
                reports[dataset_name] = {"error": "No data"}
                continue
            
            y_true = np.array([d['sepsis_label'] for d in dataset])
            y_scores = np.array([d['risk_score'] for d in dataset])
            
            thresholds = [16, 20, 25, 30, 35, 40, 45, 50]
            threshold_metrics = []
            
            for threshold in thresholds:
                y_pred = (y_scores >= threshold).astype(int)
                
                tp = ((y_pred == 1) & (y_true == 1)).sum()
                fp = ((y_pred == 1) & (y_true == 0)).sum()
                fn = ((y_pred == 0) & (y_true == 1)).sum()
                tn = ((y_pred == 0) & (y_true == 0)).sum()
                
                sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
                specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
                ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
                npv = tn / (tn + fn) if (tn + fn) > 0 else 0
                f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
                accuracy = (tp + tn) / len(y_true)
                
                threshold_metrics.append({
                    'threshold': threshold,
                    'tp': int(tp),
                    'fp': int(fp),
                    'fn': int(fn),
                    'tn': int(tn),
                    'sensitivity': float(sensitivity),
                    'specificity': float(specificity),
                    'ppv': float(ppv),
                    'npv': float(npv),
                    'f1': float(f1),
                    'accuracy': float(accuracy)
                })
            
            try:
                auroc = roc_auc_score(y_true, y_scores / 100.0)
                auprc = average_precision_score(y_true, y_scores / 100.0)
            except:
                auroc = 0.0
                auprc = 0.0
            
            best_f1_idx = max(range(len(threshold_metrics)), key=lambda i: threshold_metrics[i]['f1'])
            optimal_threshold = threshold_metrics[best_f1_idx]
            
            reports[dataset_name] = {
                'dataset': dataset_name,
                'n_patients': len(dataset),
                'n_sepsis': int(y_true.sum()),
                'n_non_sepsis': int((1 - y_true).sum()),
                'prevalence': float(y_true.mean()),
                'auroc': float(auroc),
                'auprc': float(auprc),
                'threshold_metrics': threshold_metrics,
                'optimal_threshold': optimal_threshold,
                'risk_score_distribution': {
                    'sepsis': {
                        'mean': float(y_scores[y_true == 1].mean()) if y_true.sum() > 0 else 0,
                        'median': float(np.median(y_scores[y_true == 1])) if y_true.sum() > 0 else 0,
                        'std': float(y_scores[y_true == 1].std()) if y_true.sum() > 0 else 0
                    },
                    'non_sepsis': {
                        'mean': float(y_scores[y_true == 0].mean()) if (1 - y_true).sum() > 0 else 0,
                        'median': float(np.median(y_scores[y_true == 0])) if (1 - y_true).sum() > 0 else 0,
                        'std': float(y_scores[y_true == 0].std()) if (1 - y_true).sum() > 0 else 0
                    }
                }
            }
        
        with open('/tmp/validation_reports.json', 'w') as f:
            json.dump(reports, f, indent=2)
        
        print("\n=== Validation Reports Generated ===")
        print(json.dumps(reports, indent=2))
        
        return reports

if __name__ == "__main__":
    asyncio.run(generate_validation_reports())
