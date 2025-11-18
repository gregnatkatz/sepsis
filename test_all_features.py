#!/usr/bin/env python3
"""
Comprehensive testing script for all 5 game-changing features
Tests across 20 diverse patient scenarios
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_horizon_forecast(patient_id):
    """Test Horizon Forecast feature"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}/horizon-forecast", timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "forecasts": len(data.get("forecasts", [])),
            "has_reasoning": "reasoning" in data,
            "data": data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_next_best_action(patient_id):
    """Test Next Best Action feature"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}/next-best-action", timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "actions": len(data.get("actions", [])),
            "has_reasoning": "reasoning" in data,
            "data": data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_sepsis_bundle(patient_id):
    """Test Sepsis Bundle feature"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}/sepsis-bundle", timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "tasks": len(data.get("tasks", [])),
            "has_orchestration": "orchestration_reasoning" in data,
            "data": data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_what_if_simulator(patient_id):
    """Test What-If Simulator feature"""
    try:
        payload = {
            "intervention": "Start broad-spectrum antibiotics (Vancomycin + Piperacillin-Tazobactam)",
            "parameters": {
                "antibiotic_type": "broad_spectrum",
                "timing": "immediate"
            }
        }
        response = requests.post(f"{BASE_URL}/api/patients/{patient_id}/what-if", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "has_prediction": "predicted_outcome" in data,
            "has_confidence": "confidence" in data,
            "data": data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_early_warning(patient_id):
    """Test Early Warning System feature"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}/early-warning", timeout=60)
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "agents": len(data.get("agent_assessments", [])),
            "has_consensus": "consensus" in data,
            "data": data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_patient_info(patient_id):
    """Get patient information"""
    try:
        response = requests.get(f"{BASE_URL}/api/patients/{patient_id}", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def run_comprehensive_test():
    """Run comprehensive test across 20 patient scenarios"""
    
    print("=" * 80)
    print("COMPREHENSIVE FEATURE TESTING - 20 PATIENT SCENARIOS")
    print("=" * 80)
    print(f"Start Time: {datetime.now().isoformat()}")
    print()
    
    response = requests.get(f"{BASE_URL}/api/patients")
    all_patients = response.json()["patients"]
    
    test_patients = []
    risk_levels = {"CRITICAL": [], "HIGH": [], "MODERATE": [], "LOW": []}
    
    for patient in all_patients:
        risk_level = patient.get("risk_level", "UNKNOWN")
        if risk_level in risk_levels:
            risk_levels[risk_level].append(patient["id"])
    
    test_patients.extend(risk_levels["CRITICAL"][:5])
    test_patients.extend(risk_levels["HIGH"][:5])
    test_patients.extend(risk_levels["MODERATE"][:5])
    test_patients.extend(risk_levels["LOW"][:5])
    
    while len(test_patients) < 20 and len(test_patients) < len(all_patients):
        for patient in all_patients:
            if patient["id"] not in test_patients:
                test_patients.append(patient["id"])
                if len(test_patients) >= 20:
                    break
    
    results = {
        "total_patients": len(test_patients),
        "test_timestamp": datetime.now().isoformat(),
        "patients": []
    }
    
    for idx, patient_id in enumerate(test_patients[:20], 1):
        print(f"\n{'=' * 80}")
        print(f"Testing Patient {idx}/20 - ID: {patient_id}")
        print(f"{'=' * 80}")
        
        patient_info = get_patient_info(patient_id)
        if "error" in patient_info:
            print(f"❌ Failed to get patient info: {patient_info['error']}")
            continue
        
        patient_name = patient_info.get("name", "Unknown")
        risk_level = patient_info.get("risk_level", "UNKNOWN")
        risk_score = patient_info.get("risk_score", 0)
        
        print(f"Patient: {patient_name}")
        print(f"Risk Level: {risk_level} (Score: {risk_score})")
        print()
        
        patient_results = {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "features": {}
        }
        
        print("1️⃣  Testing Horizon Forecast...")
        forecast_result = test_horizon_forecast(patient_id)
        patient_results["features"]["horizon_forecast"] = forecast_result
        if forecast_result["success"]:
            print(f"   ✅ SUCCESS - {forecast_result['forecasts']} forecasts generated")
        else:
            print(f"   ❌ FAILED - {forecast_result.get('error', 'Unknown error')}")
        time.sleep(1)
        
        print("2️⃣  Testing Next Best Action...")
        action_result = test_next_best_action(patient_id)
        patient_results["features"]["next_best_action"] = action_result
        if action_result["success"]:
            print(f"   ✅ SUCCESS - {action_result['actions']} actions recommended")
        else:
            print(f"   ❌ FAILED - {action_result.get('error', 'Unknown error')}")
        time.sleep(1)
        
        print("3️⃣  Testing Sepsis Bundle...")
        bundle_result = test_sepsis_bundle(patient_id)
        patient_results["features"]["sepsis_bundle"] = bundle_result
        if bundle_result["success"]:
            print(f"   ✅ SUCCESS - {bundle_result['tasks']} tasks orchestrated")
        else:
            print(f"   ❌ FAILED - {bundle_result.get('error', 'Unknown error')}")
        time.sleep(1)
        
        print("4️⃣  Testing What-If Simulator...")
        whatif_result = test_what_if_simulator(patient_id)
        patient_results["features"]["what_if_simulator"] = whatif_result
        if whatif_result["success"]:
            print(f"   ✅ SUCCESS - Prediction generated")
        else:
            print(f"   ❌ FAILED - {whatif_result.get('error', 'Unknown error')}")
        time.sleep(1)
        
        print("5️⃣  Testing Early Warning System...")
        warning_result = test_early_warning(patient_id)
        patient_results["features"]["early_warning"] = warning_result
        if warning_result["success"]:
            print(f"   ✅ SUCCESS - {warning_result['agents']} agents assessed")
        else:
            print(f"   ❌ FAILED - {warning_result.get('error', 'Unknown error')}")
        time.sleep(1)
        
        results["patients"].append(patient_results)
        print(f"\n✅ Completed testing for Patient {idx}/20")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results["patients"]) * 5
    successful_tests = 0
    feature_success = {
        "horizon_forecast": 0,
        "next_best_action": 0,
        "sepsis_bundle": 0,
        "what_if_simulator": 0,
        "early_warning": 0
    }
    
    for patient in results["patients"]:
        for feature, result in patient["features"].items():
            if result.get("success"):
                successful_tests += 1
                feature_success[feature] += 1
    
    print(f"\nTotal Patients Tested: {len(results['patients'])}")
    print(f"Total Tests Run: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {(successful_tests/total_tests*100):.1f}%")
    print()
    print("Feature Success Rates:")
    for feature, count in feature_success.items():
        rate = (count / len(results["patients"]) * 100) if results["patients"] else 0
        print(f"  {feature}: {count}/{len(results['patients'])} ({rate:.1f}%)")
    
    output_file = f"/home/ubuntu/sepsis/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print(f"\nEnd Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    run_comprehensive_test()
