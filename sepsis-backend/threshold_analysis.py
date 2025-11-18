"""
Threshold Analysis for Sepsis Risk Score Optimization
Analyzes different threshold values to optimize PPV, sensitivity, and F1 score
"""

import asyncio
import numpy as np
from sqlalchemy import select
from app.database import AsyncSessionLocal, DimPatient
from sklearn.metrics import roc_curve, precision_recall_curve, auc
import json

async def analyze_thresholds():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DimPatient.risk_score, DimPatient.cohort_tags)
            .where(DimPatient.cohort_tags.like('%kaggle%'))
        )
        data = result.all()
        
        y_true = []
        y_scores = []
        
        for row in data:
            cohort_tags = json.loads(row.cohort_tags) if row.cohort_tags else []
            sepsis_label = 0
            for tag in cohort_tags:
                if tag.startswith('sepsis_'):
                    sepsis_label = int(tag.split('_')[1])
                    break
            
            y_true.append(sepsis_label)
            y_scores.append(row.risk_score)
        
        y_true = np.array(y_true)
        y_scores = np.array(y_scores)
        
        print(f"=== Dataset Overview ===")
        print(f"Total patients: {len(y_true):,}")
        print(f"Sepsis cases: {y_true.sum():,} ({y_true.mean()*100:.1f}%)")
        print(f"Non-sepsis: {len(y_true) - y_true.sum():,} ({(1-y_true.mean())*100:.1f}%)")
        print()
        
        print(f"=== Risk Score Distribution ===")
        print(f"Overall: mean={y_scores.mean():.1f}, median={np.median(y_scores):.1f}, std={y_scores.std():.1f}")
        print(f"Sepsis patients: mean={y_scores[y_true==1].mean():.1f}, median={np.median(y_scores[y_true==1]):.1f}")
        print(f"Non-sepsis patients: mean={y_scores[y_true==0].mean():.1f}, median={np.median(y_scores[y_true==0]):.1f}")
        print()
        
        thresholds_to_test = [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]
        
        print("=== Threshold Analysis ===")
        print(f"{'Threshold':<12} {'TP':<8} {'FP':<8} {'FN':<8} {'TN':<8} {'Sens':<10} {'Spec':<10} {'PPV':<10} {'NPV':<10} {'F1':<10} {'Acc':<10}")
        print("-" * 130)
        
        results = []
        for threshold in thresholds_to_test:
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
            
            print(f"{threshold:<12} {tp:<8} {fp:<8} {fn:<8} {tn:<8} {sensitivity:<10.3f} {specificity:<10.3f} {ppv:<10.3f} {npv:<10.3f} {f1:<10.3f} {accuracy:<10.3f}")
            
            results.append({
                'threshold': threshold,
                'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn),
                'sensitivity': sensitivity, 'specificity': specificity,
                'ppv': ppv, 'npv': npv, 'f1': f1, 'accuracy': accuracy
            })
        
        print()
        print("=== Optimal Thresholds for Different Objectives ===")
        
        best_f1 = 0
        best_f1_threshold = 0
        best_f1_metrics = {}
        
        for threshold in range(0, 101):
            y_pred = (y_scores >= threshold).astype(int)
            tp = ((y_pred == 1) & (y_true == 1)).sum()
            fp = ((y_pred == 1) & (y_true == 0)).sum()
            fn = ((y_pred == 0) & (y_true == 1)).sum()
            tn = ((y_pred == 0) & (y_true == 0)).sum()
            
            f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0
            
            if f1 > best_f1:
                best_f1 = f1
                best_f1_threshold = threshold
                sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
                ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
                best_f1_metrics = {
                    'threshold': threshold,
                    'f1': f1,
                    'sensitivity': sensitivity,
                    'ppv': ppv,
                    'tp': int(tp),
                    'fp': int(fp)
                }
        
        print(f"1. Max F1 Score: threshold={best_f1_threshold}, F1={best_f1:.3f}, Sensitivity={best_f1_metrics['sensitivity']:.3f}, PPV={best_f1_metrics['ppv']:.3f}")
        
        ppv_80_found = False
        for threshold in range(100, -1, -1):
            y_pred = (y_scores >= threshold).astype(int)
            tp = ((y_pred == 1) & (y_true == 1)).sum()
            fp = ((y_pred == 1) & (y_true == 0)).sum()
            fn = ((y_pred == 0) & (y_true == 1)).sum()
            
            ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
            
            if ppv >= 0.8 and (tp + fp) > 0:
                sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
                print(f"2. PPV >= 0.8: threshold={threshold}, PPV={ppv:.3f}, Sensitivity={sensitivity:.3f}, TP={tp}, FP={fp}")
                ppv_80_found = True
                break
        
        if not ppv_80_found:
            print("2. PPV >= 0.8: Not achievable with current risk scores")
        
        for threshold in range(0, 101):
            y_pred = (y_scores >= threshold).astype(int)
            tp = ((y_pred == 1) & (y_true == 1)).sum()
            fp = ((y_pred == 1) & (y_true == 0)).sum()
            fn = ((y_pred == 0) & (y_true == 1)).sum()
            
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            if sensitivity >= 0.6:
                ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
                print(f"3. Sensitivity >= 0.6: threshold={threshold}, Sensitivity={sensitivity:.3f}, PPV={ppv:.3f}, TP={tp}, FP={fp}")
                break
        
        best_balance = float('inf')
        best_balance_threshold = 0
        best_balance_metrics = {}
        
        for threshold in range(0, 101):
            y_pred = (y_scores >= threshold).astype(int)
            tp = ((y_pred == 1) & (y_true == 1)).sum()
            fp = ((y_pred == 1) & (y_true == 0)).sum()
            fn = ((y_pred == 0) & (y_true == 1)).sum()
            
            if (tp + fp) > 0 and (tp + fn) > 0:
                sensitivity = tp / (tp + fn)
                ppv = tp / (tp + fp)
                balance = abs(sensitivity - ppv)
                
                if balance < best_balance and sensitivity > 0.3 and ppv > 0.3:
                    best_balance = balance
                    best_balance_threshold = threshold
                    best_balance_metrics = {
                        'threshold': threshold,
                        'sensitivity': sensitivity,
                        'ppv': ppv,
                        'tp': int(tp),
                        'fp': int(fp)
                    }
        
        if best_balance_metrics:
            print(f"4. Balanced (Sens ≈ PPV): threshold={best_balance_metrics['threshold']}, Sensitivity={best_balance_metrics['sensitivity']:.3f}, PPV={best_balance_metrics['ppv']:.3f}")
        
        print()
        print("=== Overall Model Performance ===")
        from sklearn.metrics import roc_auc_score, average_precision_score
        
        auroc = roc_auc_score(y_true, y_scores / 100.0)
        auprc = average_precision_score(y_true, y_scores / 100.0)
        
        print(f"AUROC: {auroc:.3f}")
        print(f"AUPRC: {auprc:.3f}")
        
        print()
        print("=== RECOMMENDATIONS ===")
        print()
        print("**Current Issue:** The model has very low sensitivity (0.7%) because the threshold is too high (50).")
        print("Most sepsis patients have risk scores below 50, so they're not being flagged.")
        print()
        print("**Recommended Actions:**")
        print()
        print(f"1. **For Maximum Detection (High Sensitivity):**")
        print(f"   - Set threshold to {best_f1_threshold} (optimizes F1 score)")
        print(f"   - This will catch {best_f1_metrics['sensitivity']*100:.1f}% of sepsis cases")
        print(f"   - PPV will be {best_f1_metrics['ppv']*100:.1f}% (meaning {best_f1_metrics['ppv']*100:.1f}% of alerts are true sepsis)")
        print()
        print(f"2. **For High Confidence Alerts (PPV >= 80%):**")
        if ppv_80_found:
            print(f"   - Requires very high threshold (reduces sensitivity significantly)")
            print(f"   - Only use if false positives are extremely costly")
        else:
            print(f"   - Not achievable with current risk scoring model")
            print(f"   - Need to improve the underlying risk score calculation")
        print()
        print(f"3. **For Balanced Approach:**")
        if best_balance_metrics:
            print(f"   - Set threshold to {best_balance_metrics['threshold']}")
            print(f"   - Sensitivity: {best_balance_metrics['sensitivity']*100:.1f}%, PPV: {best_balance_metrics['ppv']*100:.1f}%")
        print()
        print("**Next Steps to Improve Model:**")
        print("- Add trend features (6-12 hour changes in vitals/labs)")
        print("- Re-weight SIRS/Vitals/Labs components based on Kaggle data")
        print("- Consider machine learning model (XGBoost/LightGBM) trained on Kaggle data")
        print("- Implement calibration (logistic regression on current risk scores)")
        
        return results

if __name__ == "__main__":
    asyncio.run(analyze_thresholds())
