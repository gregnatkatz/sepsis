#!/usr/bin/env python3
"""
Validation harness to systematically test all 34 patients' AI insights.
"""

import sys
sys.path.insert(0, '/home/ubuntu/sepsis-copilot/sepsis-backend')

from mock_patients import MOCK_PATIENTS
import requests
import json
import time
from datetime import datetime
from collections import defaultdict

API_URL = "http://localhost:8000"

def validate_insight_schema(insight):
    """Validate that insight matches expected schema"""
    required_fields = ['id', 'severity', 'category', 'title', 'description', 'agent', 'icon', 'ts']
    errors = []
    
    for field in required_fields:
        if field not in insight:
            errors.append(f"Missing required field: {field}")
    
    if 'severity' in insight and insight['severity'] not in ['critical', 'warning', 'info', 'success']:
        errors.append(f"Invalid severity: {insight['severity']}")
    
    if 'category' in insight and insight['category'] not in ['deterioration', 'labs', 'hemodynamics', 'sepsis', 'monitoring', 'other']:
        errors.append(f"Invalid category: {insight['category']}")
    
    return errors

def check_insight_alignment(patient, insights):
    """Check if insights align with ground truth"""
    issues = []
    ground_truth = patient.get('ground_truth', {})
    
    if ground_truth.get('sepsis_confirmed'):
        critical_or_warning = [i for i in insights if i['severity'] in ['critical', 'warning']]
        if not critical_or_warning:
            issues.append(f"Sepsis patient {patient['name']} has no critical/warning alerts")
        
        sepsis_mentioned = any('sepsis' in i['title'].lower() or 'sepsis' in i['description'].lower() 
                              for i in insights)
        if not sepsis_mentioned and ground_truth.get('sepsis_source'):
            issues.append(f"Sepsis patient {patient['name']} has no sepsis-related insights")
    
    if patient['risk_level'] == 'LOW':
        critical_alerts = [i for i in insights if i['severity'] == 'critical']
        if critical_alerts:
            issues.append(f"LOW risk patient {patient['name']} has critical alerts: {[i['title'] for i in critical_alerts]}")
    
    if patient['risk_level'] == 'CRITICAL':
        critical_alerts = [i for i in insights if i['severity'] == 'critical']
        if not critical_alerts:
            issues.append(f"CRITICAL patient {patient['name']} has no critical alerts")
    
    qsofa = ground_truth.get('qsofa_score', 0)
    if qsofa >= 2:
        organ_mentioned = any('hypotension' in i['description'].lower() or 
                             'respiratory' in i['description'].lower() or
                             'mental' in i['description'].lower()
                             for i in insights)
        if not organ_mentioned:
            issues.append(f"Patient {patient['name']} has qSOFA {qsofa} but no organ dysfunction mentioned")
    
    return issues

def test_patient_insights(patient_id):
    """Test AI insights for a single patient"""
    start_time = time.time()
    
    try:
        response = requests.get(f"{API_URL}/api/patients/{patient_id}/ai-insights", timeout=30)
        latency = (time.time() - start_time) * 1000  # ms
        
        if response.status_code != 200:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}",
                'latency': latency
            }
        
        data = response.json()
        insights = data.get('cards', [])
        
        schema_errors = []
        for insight in insights:
            errors = validate_insight_schema(insight)
            schema_errors.extend(errors)
        
        return {
            'success': True,
            'latency': latency,
            'num_insights': len(insights),
            'insights': insights,
            'schema_errors': schema_errors,
            'data': data
        }
    
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return {
            'success': False,
            'error': str(e),
            'latency': latency
        }

def run_validation():
    """Run validation on all 34 patients"""
    print("=" * 80)
    print("SEPSIS COPILOT - AI INSIGHTS VALIDATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Total patients: {len(MOCK_PATIENTS)}")
    print()
    
    results = []
    latencies = []
    severity_dist = defaultdict(int)
    category_dist = defaultdict(int)
    alignment_issues = []
    
    print("Testing all patients...")
    for i, patient in enumerate(MOCK_PATIENTS, 1):
        print(f"  [{i}/34] Testing {patient['name']} ({patient['risk_level']})...", end=' ')
        
        result = test_patient_insights(patient['id'])
        results.append({
            'patient': patient,
            'result': result
        })
        
        if result['success']:
            print(f"✓ {result['num_insights']} insights, {result['latency']:.0f}ms")
            latencies.append(result['latency'])
            
            for insight in result['insights']:
                severity_dist[insight.get('severity', 'unknown')] += 1
                category_dist[insight.get('category', 'unknown')] += 1
            
            issues = check_insight_alignment(patient, result['insights'])
            if issues:
                alignment_issues.extend([(patient['name'], issue) for issue in issues])
        else:
            print(f"✗ {result.get('error', 'Unknown error')}")
    
    print()
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    successful = sum(1 for r in results if r['result']['success'])
    print(f"Success rate: {successful}/{len(results)} ({100*successful/len(results):.1f}%)")
    
    if latencies:
        latencies.sort()
        print(f"\nLatency (ms):")
        print(f"  Min: {min(latencies):.0f}")
        print(f"  Median: {latencies[len(latencies)//2]:.0f}")
        print(f"  P95: {latencies[int(len(latencies)*0.95)]:.0f}")
        print(f"  P99: {latencies[int(len(latencies)*0.99)]:.0f}")
        print(f"  Max: {max(latencies):.0f}")
    
    insight_counts = [r['result']['num_insights'] for r in results if r['result']['success']]
    if insight_counts:
        print(f"\nInsights per patient:")
        print(f"  Min: {min(insight_counts)}")
        print(f"  Median: {sorted(insight_counts)[len(insight_counts)//2]}")
        print(f"  Max: {max(insight_counts)}")
        print(f"  Total: {sum(insight_counts)}")
    
    print(f"\nSeverity distribution:")
    for severity in ['critical', 'warning', 'info', 'success']:
        count = severity_dist[severity]
        pct = 100 * count / sum(severity_dist.values()) if severity_dist else 0
        print(f"  {severity}: {count} ({pct:.1f}%)")
    
    print(f"\nCategory distribution:")
    for category in sorted(category_dist.keys()):
        count = category_dist[category]
        pct = 100 * count / sum(category_dist.values()) if category_dist else 0
        print(f"  {category}: {count} ({pct:.1f}%)")
    
    schema_errors = []
    for r in results:
        if r['result']['success']:
            schema_errors.extend(r['result'].get('schema_errors', []))
    
    if schema_errors:
        print(f"\n⚠️  Schema validation errors: {len(schema_errors)}")
        for error in schema_errors[:10]:  # Show first 10
            print(f"  - {error}")
    else:
        print(f"\n✓ No schema validation errors")
    
    print()
    print("=" * 80)
    print("GROUND TRUTH ALIGNMENT")
    print("=" * 80)
    
    if alignment_issues:
        print(f"\n⚠️  Found {len(alignment_issues)} alignment issues:")
        for patient_name, issue in alignment_issues:
            print(f"  - {patient_name}: {issue}")
    else:
        print("\n✓ All insights align with ground truth")
    
    print()
    print("=" * 80)
    print("BREAKDOWN BY RISK LEVEL")
    print("=" * 80)
    
    for risk_level in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
        patients_at_level = [r for r in results if r['patient']['risk_level'] == risk_level]
        if not patients_at_level:
            continue
        
        print(f"\n{risk_level} ({len(patients_at_level)} patients):")
        
        sepsis_confirmed = sum(1 for r in patients_at_level 
                              if r['patient'].get('ground_truth', {}).get('sepsis_confirmed'))
        print(f"  Sepsis confirmed: {sepsis_confirmed}/{len(patients_at_level)}")
        
        avg_insights = sum(r['result']['num_insights'] for r in patients_at_level if r['result']['success']) / len(patients_at_level)
        print(f"  Avg insights: {avg_insights:.1f}")
        
        level_severity = defaultdict(int)
        for r in patients_at_level:
            if r['result']['success']:
                for insight in r['result']['insights']:
                    level_severity[insight.get('severity', 'unknown')] += 1
        
        if level_severity:
            print(f"  Severity breakdown:")
            for severity in ['critical', 'warning', 'info', 'success']:
                count = level_severity[severity]
                if count > 0:
                    print(f"    {severity}: {count}")
    
    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    
    report_path = '/home/ubuntu/sepsis-copilot/sepsis-backend/validation_report.json'
    with open(report_path, 'w') as f:
        json.dump({
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_patients': len(results),
                'successful': successful,
                'success_rate': successful / len(results),
                'latency': {
                    'min': min(latencies) if latencies else None,
                    'median': latencies[len(latencies)//2] if latencies else None,
                    'p95': latencies[int(len(latencies)*0.95)] if latencies else None,
                    'max': max(latencies) if latencies else None
                },
                'severity_distribution': dict(severity_dist),
                'category_distribution': dict(category_dist),
                'schema_errors': len(schema_errors),
                'alignment_issues': len(alignment_issues)
            },
            'alignment_issues': [{'patient': name, 'issue': issue} for name, issue in alignment_issues],
            'results': [{
                'patient_id': r['patient']['id'],
                'patient_name': r['patient']['name'],
                'risk_level': r['patient']['risk_level'],
                'sepsis_confirmed': r['patient'].get('ground_truth', {}).get('sepsis_confirmed'),
                'qsofa_score': r['patient'].get('ground_truth', {}).get('qsofa_score'),
                'sofa_score': r['patient'].get('ground_truth', {}).get('sofa_score'),
                'success': r['result']['success'],
                'latency': r['result'].get('latency'),
                'num_insights': r['result'].get('num_insights'),
                'insights': r['result'].get('insights', [])
            } for r in results]
        }, f, indent=2)
    
    print(f"\n✓ Detailed report saved to: {report_path}")

if __name__ == '__main__':
    run_validation()
