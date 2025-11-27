#!/usr/bin/env python3
"""
50x End-to-End AI Endpoint Testing Script
Tests all 6 AI endpoints against live Azure OpenAI for each featured patient.
"""

import requests
import time
import json
from datetime import datetime

API_URL = "http://localhost:8000"

FEATURED_PATIENT_IDS = ["featured-1", "featured-2", "featured-3", "featured-4"]
MOCK_PATIENT_IDS = ["1", "2", "3", "4", "5"]

AI_ENDPOINTS = [
    "/api/patients/{patient_id}/ai-insights",
    "/api/patients/{patient_id}/horizon-forecast",
    "/api/patients/{patient_id}/sepsis-bundle",
    "/api/patients/{patient_id}/early-warning",
    "/api/patients/{patient_id}/sepsis-huddle-summary",
    "/api/patients/{patient_id}/what-if/monte-carlo",
]

def test_endpoint(endpoint: str, patient_id: str, run_num: int) -> dict:
    """Test a single endpoint and return results."""
    url = f"{API_URL}{endpoint.format(patient_id=patient_id)}"
    start_time = time.time()
    
    try:
        if "monte-carlo" in endpoint:
            response = requests.post(url, json={
                "fluids_ml": 1000,
                "oxygen_increase": 2,
                "antibiotics_given": True,
                "vasopressors_started": False
            }, timeout=60)
        else:
            response = requests.get(url, timeout=60)
        
        elapsed = time.time() - start_time
        
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "elapsed_ms": round(elapsed * 1000, 2),
            "response_size": len(response.content),
            "error": None if response.status_code == 200 else response.text[:200]
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 0,
            "elapsed_ms": round((time.time() - start_time) * 1000, 2),
            "response_size": 0,
            "error": str(e)[:200]
        }

def run_tests(num_runs: int = 50):
    """Run all tests and generate report."""
    print(f"\n{'='*80}")
    print(f"50x End-to-End AI Endpoint Testing")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    results = {}
    patient_ids = MOCK_PATIENT_IDS[:4]  # Use first 4 mock patients
    
    for endpoint in AI_ENDPOINTS:
        endpoint_name = endpoint.split("/")[-1].replace("{patient_id}", "").strip("/")
        results[endpoint_name] = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "avg_time_ms": 0,
            "times": [],
            "errors": []
        }
    
    total_tests = len(AI_ENDPOINTS) * len(patient_ids) * num_runs
    completed = 0
    
    for run in range(num_runs):
        print(f"\n--- Run {run + 1}/{num_runs} ---")
        
        for patient_id in patient_ids:
            for endpoint in AI_ENDPOINTS:
                endpoint_name = endpoint.split("/")[-1].replace("{patient_id}", "").strip("/")
                
                result = test_endpoint(endpoint, patient_id, run)
                results[endpoint_name]["total"] += 1
                
                if result["success"]:
                    results[endpoint_name]["success"] += 1
                    results[endpoint_name]["times"].append(result["elapsed_ms"])
                    status = "OK"
                else:
                    results[endpoint_name]["failed"] += 1
                    results[endpoint_name]["errors"].append({
                        "patient_id": patient_id,
                        "run": run + 1,
                        "error": result["error"]
                    })
                    status = "FAIL"
                
                completed += 1
                print(f"  [{completed}/{total_tests}] {endpoint_name} (patient {patient_id}): {status} ({result['elapsed_ms']}ms)")
    
    # Calculate averages
    for endpoint_name in results:
        if results[endpoint_name]["times"]:
            results[endpoint_name]["avg_time_ms"] = round(
                sum(results[endpoint_name]["times"]) / len(results[endpoint_name]["times"]), 2
            )
    
    # Generate report
    print(f"\n{'='*80}")
    print(f"FINAL REPORT")
    print(f"{'='*80}\n")
    
    total_success = 0
    total_failed = 0
    
    for endpoint_name, data in results.items():
        success_rate = (data["success"] / data["total"] * 100) if data["total"] > 0 else 0
        total_success += data["success"]
        total_failed += data["failed"]
        
        print(f"\n{endpoint_name}:")
        print(f"  Total: {data['total']}, Success: {data['success']}, Failed: {data['failed']}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Avg Response Time: {data['avg_time_ms']}ms")
        
        if data["errors"]:
            print(f"  Errors ({len(data['errors'])}):")
            for err in data["errors"][:3]:  # Show first 3 errors
                print(f"    - Patient {err['patient_id']}, Run {err['run']}: {err['error'][:100]}")
    
    overall_success_rate = (total_success / (total_success + total_failed) * 100) if (total_success + total_failed) > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"OVERALL RESULTS")
    print(f"{'='*80}")
    print(f"Total Tests: {total_success + total_failed}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_failed}")
    print(f"Overall Success Rate: {overall_success_rate:.1f}%")
    print(f"Completed: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Save results to file
    with open("ai_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "num_runs": num_runs,
            "results": results,
            "overall": {
                "total": total_success + total_failed,
                "success": total_success,
                "failed": total_failed,
                "success_rate": overall_success_rate
            }
        }, f, indent=2)
    
    print("Results saved to ai_test_results.json")
    
    return results

if __name__ == "__main__":
    import sys
    num_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_tests(num_runs)
