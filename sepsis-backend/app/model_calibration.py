"""
Model Calibration Module
Implements logistic regression calibration to map risk scores to calibrated probabilities
"""

from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import pickle
import os

class RiskScoreCalibrator:
    """
    Calibrates risk scores using logistic regression
    Maps raw risk scores to calibrated probabilities
    """
    
    def __init__(self):
        self.calibrator = None
        self.is_fitted = False
        
    def fit(self, risk_scores: np.ndarray, labels: np.ndarray) -> Dict[str, Any]:
        """
        Fit logistic regression calibrator on risk scores and labels
        
        Args:
            risk_scores: Array of raw risk scores
            labels: Array of binary labels (0 or 1)
            
        Returns:
            Dictionary with calibration metrics
        """
        X = risk_scores.reshape(-1, 1)
        y = labels
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        self.calibrator = LogisticRegression(random_state=42, max_iter=1000)
        self.calibrator.fit(X_train, y_train)
        self.is_fitted = True
        
        train_probs = self.calibrator.predict_proba(X_train)[:, 1]
        test_probs = self.calibrator.predict_proba(X_test)[:, 1]
        
        from sklearn.calibration import calibration_curve
        
        try:
            prob_true_train, prob_pred_train = calibration_curve(
                y_train, train_probs, n_bins=10, strategy='uniform'
            )
            prob_true_test, prob_pred_test = calibration_curve(
                y_test, test_probs, n_bins=10, strategy='uniform'
            )
        except:
            prob_true_train, prob_pred_train = np.array([]), np.array([])
            prob_true_test, prob_pred_test = np.array([]), np.array([])
        
        return {
            "coefficients": {
                "intercept": float(self.calibrator.intercept_[0]),
                "slope": float(self.calibrator.coef_[0][0])
            },
            "train_size": len(X_train),
            "test_size": len(X_test),
            "calibration_curve_train": {
                "prob_true": prob_true_train.tolist(),
                "prob_pred": prob_pred_train.tolist()
            },
            "calibration_curve_test": {
                "prob_true": prob_true_test.tolist(),
                "prob_pred": prob_pred_test.tolist()
            }
        }
    
    def predict_proba(self, risk_scores: np.ndarray) -> np.ndarray:
        """
        Predict calibrated probabilities from risk scores
        
        Args:
            risk_scores: Array of raw risk scores
            
        Returns:
            Array of calibrated probabilities
        """
        if not self.is_fitted:
            raise ValueError("Calibrator must be fitted before prediction")
        
        X = risk_scores.reshape(-1, 1)
        probs = self.calibrator.predict_proba(X)[:, 1]
        return probs
    
    def save(self, filepath: str):
        """Save calibrator to disk"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.calibrator, f)
    
    def load(self, filepath: str):
        """Load calibrator from disk"""
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.calibrator = pickle.load(f)
            self.is_fitted = True
            return True
        return False


def train_calibrator_on_kaggle(patients: List[Dict[str, Any]]) -> Tuple[RiskScoreCalibrator, Dict[str, Any]]:
    """
    Train calibrator on Kaggle dataset
    
    Args:
        patients: List of patient records with risk_score and sepsis_label
        
    Returns:
        Tuple of (calibrator, metrics)
    """
    kaggle_patients = [
        p for p in patients 
        if p.get('id', '').startswith('kaggle-') or p.get('id', '').startswith('KGL-')
    ]
    
    if not kaggle_patients:
        raise ValueError("No Kaggle patients found for calibration")
    
    risk_scores = []
    labels = []
    
    for p in kaggle_patients:
        cohort_tags = p.get('cohort_tags', [])
        if isinstance(cohort_tags, str):
            import json
            cohort_tags = json.loads(cohort_tags)
        
        sepsis_label = 0
        for tag in cohort_tags:
            if tag.startswith('sepsis_'):
                sepsis_label = int(tag.split('_')[1])
                break
        
        risk_scores.append(p.get('risk_score', 0))
        labels.append(sepsis_label)
    
    risk_scores = np.array(risk_scores)
    labels = np.array(labels)
    
    calibrator = RiskScoreCalibrator()
    metrics = calibrator.fit(risk_scores, labels)
    
    metrics['n_patients'] = len(kaggle_patients)
    metrics['n_sepsis'] = int(labels.sum())
    metrics['prevalence'] = float(labels.mean())
    
    return calibrator, metrics
