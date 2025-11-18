"""
Extract raw features with trend features from Kaggle time-series data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def load_kaggle_raw_data(csv_path: str):
    """Load raw Kaggle dataset"""
    print(f"Loading Kaggle dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows from {df['Patient_ID'].nunique():,} patients")
    return df

def calculate_trend_features(patient_df: pd.DataFrame, lookback_hours: int = 6):
    """Calculate trend features (changes over lookback window)"""
    if len(patient_df) < 2:
        return {}
    
    # Get current and past values
    current = patient_df.iloc[-1]
    
    # Find row from lookback_hours ago
    past_idx = max(0, len(patient_df) - lookback_hours - 1)
    past = patient_df.iloc[past_idx]
    
    trends = {}
    
    # Vital signs trends
    for col in ['HR', 'Temp', 'SBP', 'DBP', 'MAP', 'Resp', 'O2Sat']:
        if pd.notna(current[col]) and pd.notna(past[col]):
            trends[f'{col}_trend_{lookback_hours}h'] = current[col] - past[col]
            trends[f'{col}_pct_change_{lookback_hours}h'] = ((current[col] - past[col]) / past[col] * 100) if past[col] != 0 else 0
        else:
            trends[f'{col}_trend_{lookback_hours}h'] = 0
            trends[f'{col}_pct_change_{lookback_hours}h'] = 0
    
    # Lab trends
    for col in ['WBC', 'Lactate', 'Creatinine', 'Glucose', 'Hct', 'Platelets']:
        if pd.notna(current[col]) and pd.notna(past[col]):
            trends[f'{col}_trend_{lookback_hours}h'] = current[col] - past[col]
            trends[f'{col}_pct_change_{lookback_hours}h'] = ((current[col] - past[col]) / past[col] * 100) if past[col] != 0 else 0
        else:
            trends[f'{col}_trend_{lookback_hours}h'] = 0
            trends[f'{col}_pct_change_{lookback_hours}h'] = 0
    
    return trends

def extract_features_per_patient(patient_df: pd.DataFrame):
    """Extract features for a single patient (using last hour)"""
    latest = patient_df.iloc[-1]
    
    features = {}
    
    # SIRS components
    features['temp'] = float(latest['Temp']) if pd.notna(latest['Temp']) else 37.0
    features['hr'] = float(latest['HR']) if pd.notna(latest['HR']) else 80.0
    features['resp'] = float(latest['Resp']) if pd.notna(latest['Resp']) else 16.0
    features['wbc'] = float(latest['WBC']) if pd.notna(latest['WBC']) else 8.0
    
    # SIRS criteria
    features['sirs_temp'] = 1 if (features['temp'] < 36 or features['temp'] > 38) else 0
    features['sirs_hr'] = 1 if features['hr'] > 90 else 0
    features['sirs_resp'] = 1 if features['resp'] > 20 else 0
    features['sirs_wbc'] = 1 if (features['wbc'] < 4 or features['wbc'] > 12) else 0
    features['sirs_count'] = features['sirs_temp'] + features['sirs_hr'] + features['sirs_resp'] + features['sirs_wbc']
    
    # Vitals
    features['sbp'] = float(latest['SBP']) if pd.notna(latest['SBP']) else 120.0
    features['dbp'] = float(latest['DBP']) if pd.notna(latest['DBP']) else 80.0
    features['map'] = float(latest['MAP']) if pd.notna(latest['MAP']) else 93.0
    features['o2sat'] = float(latest['O2Sat']) if pd.notna(latest['O2Sat']) else 98.0
    
    # Labs
    features['lactate'] = float(latest['Lactate']) if pd.notna(latest['Lactate']) else 1.0
    features['creatinine'] = float(latest['Creatinine']) if pd.notna(latest['Creatinine']) else 1.0
    features['glucose'] = float(latest['Glucose']) if pd.notna(latest['Glucose']) else 100.0
    features['hct'] = float(latest['Hct']) if pd.notna(latest['Hct']) else 40.0
    features['platelets'] = float(latest['Platelets']) if pd.notna(latest['Platelets']) else 200.0
    
    # Demographics
    features['age'] = int(latest['Age']) if pd.notna(latest['Age']) else 65
    features['gender'] = int(latest['Gender']) if pd.notna(latest['Gender']) else 0
    features['iculos'] = int(latest['ICULOS']) if pd.notna(latest['ICULOS']) else 1
    
    # Trend features (6h and 12h)
    trends_6h = calculate_trend_features(patient_df, lookback_hours=6)
    trends_12h = calculate_trend_features(patient_df, lookback_hours=12)
    
    features.update(trends_6h)
    features.update(trends_12h)
    
    # Label
    features['sepsis_label'] = int(patient_df['SepsisLabel'].max())
    features['patient_id'] = int(latest['Patient_ID'])
    
    return features

def main():
    csv_path = "/home/ubuntu/sepsis/data/Dataset.csv"
    
    df = load_kaggle_raw_data(csv_path)
    
    print("\nExtracting features with trends...")
    all_features = []
    
    for patient_id, patient_df in df.groupby('Patient_ID'):
        if patient_id % 5000 == 0:
            print(f"Processing patient {patient_id}...")
        
        features = extract_features_per_patient(patient_df)
        all_features.append(features)
    
    # Convert to DataFrame
    features_df = pd.DataFrame(all_features)
    
    print(f"\n=== Feature Extraction Complete ===")
    print(f"Total patients: {len(features_df)}")
    print(f"Total features: {len(features_df.columns)}")
    print(f"Sepsis cases: {features_df['sepsis_label'].sum()} ({features_df['sepsis_label'].mean()*100:.1f}%)")
    
    print(f"\nFeature columns:")
    print(features_df.columns.tolist())
    
    # Save to CSV
    output_path = "kaggle_features_with_trends.csv"
    features_df.to_csv(output_path, index=False)
    print(f"\nSaved features to {output_path}")
    
    print(f"\nSample features:")
    print(features_df.head(3).to_string())

if __name__ == "__main__":
    main()
