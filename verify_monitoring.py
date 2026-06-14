#!/usr/bin/env python3
"""
Verification script for Luxline monitoring system.
Checks that all monitoring components are properly configured and accessible.
"""

import time
import requests
import sys
from typing import Tuple

def check_prometheus_metrics(backend_url: str = "http://localhost:8000") -> Tuple[bool, str]:
    """Check if backend is exposing Prometheus metrics."""
    try:
        response = requests.get(f"{backend_url}/metrics", timeout=5)
        if response.status_code == 200 and "luxline_requests_total" in response.text:
            return True, "✓ Backend metrics endpoint is working"
        return False, f"✗ Metrics endpoint returned invalid response (status: {response.status_code})"
    except Exception as e:
        return False, f"✗ Cannot reach backend metrics: {str(e)}"

def check_prometheus_server(prometheus_url: str = "http://localhost:9090") -> Tuple[bool, str]:
    """Check if Prometheus server is running."""
    try:
        response = requests.get(f"{prometheus_url}/-/healthy", timeout=5)
        if response.status_code == 200:
            return True, "✓ Prometheus server is running"
        return False, f"✗ Prometheus returned status {response.status_code}"
    except Exception as e:
        return False, f"✗ Cannot reach Prometheus: {str(e)}"

def check_prometheus_scraping(prometheus_url: str = "http://localhost:9090") -> Tuple[bool, str]:
    """Check if Prometheus is scraping backend metrics."""
    try:
        response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=5)
        if response.status_code == 200:
            data = response.json()
            active_targets = data.get("data", {}).get("activeTargets", [])
            if any("backend:8000" in str(t) for t in active_targets):
                return True, "✓ Prometheus is scraping backend metrics"
            return False, "✗ Prometheus not scraping backend target"
        return False, f"✗ Prometheus API returned status {response.status_code}"
    except Exception as e:
        return False, f"✗ Cannot check Prometheus targets: {str(e)}"

def check_grafana_server(grafana_url: str = "http://localhost:3000") -> Tuple[bool, str]:
    """Check if Grafana server is running."""
    try:
        response = requests.get(f"{grafana_url}/api/health", timeout=5)
        if response.status_code == 200:
            return True, "✓ Grafana server is running"
        return False, f"✗ Grafana returned status {response.status_code}"
    except Exception as e:
        return False, f"✗ Cannot reach Grafana: {str(e)}"

def check_grafana_datasource(grafana_url: str = "http://localhost:3000") -> Tuple[bool, str]:
    """Check if Grafana has Prometheus datasource configured."""
    try:
        response = requests.get(
            f"{grafana_url}/api/datasources",
            headers={"Authorization": "Bearer admin"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if any(ds.get("type") == "prometheus" for ds in data):
                return True, "✓ Prometheus datasource is configured in Grafana"
            return False, "✗ No Prometheus datasource found in Grafana"
        return False, f"✗ Grafana API returned status {response.status_code}"
    except Exception as e:
        return False, f"✗ Cannot check Grafana datasources: {str(e)}"

def generate_test_traffic(backend_url: str = "http://localhost:8000", requests_count: int = 10) -> Tuple[bool, str]:
    """Generate test traffic to populate metrics."""
    try:
        for i in range(requests_count):
            try:
                requests.get(f"{backend_url}/health", timeout=2)
            except:
                pass
        return True, f"✓ Generated {requests_count} test requests"
    except Exception as e:
        return False, f"✗ Error generating test traffic: {str(e)}"

def check_metrics_in_prometheus(prometheus_url: str = "http://localhost:9090") -> Tuple[bool, str]:
    """Check if metrics are being recorded in Prometheus."""
    try:
        response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": "luxline_requests_total"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("result"):
                return True, "✓ Metrics are being recorded in Prometheus"
            return False, "✗ No metrics found in Prometheus (may need to wait a few seconds)"
        return False, f"✗ Prometheus query failed with status {response.status_code}"
    except Exception as e:
        return False, f"✗ Cannot query Prometheus: {str(e)}"

def main():
    """Run all verification checks."""
    print("\n" + "="*60)
    print("LUXLINE MONITORING SYSTEM VERIFICATION")
    print("="*60 + "\n")
    
    checks = [
        ("Backend Metrics Endpoint", check_prometheus_metrics),
        ("Prometheus Server", check_prometheus_server),
        ("Prometheus Scraping Backend", check_prometheus_scraping),
        ("Grafana Server", check_grafana_server),
        ("Grafana Prometheus Datasource", check_grafana_datasource),
        ("Generating Test Traffic", lambda: generate_test_traffic(requests_count=5)),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"Checking: {check_name}...", end=" ")
        sys.stdout.flush()
        success, message = check_func()
        results.append((success, message))
        print(message)
        time.sleep(0.5)
    
    # Give Prometheus time to scrape
    print("\nWaiting for Prometheus to scrape metrics...")
    time.sleep(3)
    
    print(f"Checking: Metrics in Prometheus...", end=" ")
    sys.stdout.flush()
    success, message = check_metrics_in_prometheus()
    results.append((success, message))
    print(message)
    
    # Summary
    print("\n" + "="*60)
    passed = sum(1 for success, _ in results if success)
    total = len(results)
    print(f"VERIFICATION SUMMARY: {passed}/{total} checks passed")
    print("="*60 + "\n")
    
    if passed == total:
        print("✓ All checks passed! Monitoring system is working correctly.\n")
        print("Access the monitoring dashboards at:")
        print("  - Grafana: http://localhost:3000 (admin/admin)")
        print("  - Prometheus: http://localhost:9090")
        print("  - API Metrics: http://localhost:8000/metrics\n")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.\n")
        print("Troubleshooting tips:")
        print("  1. Ensure all Docker containers are running: docker-compose ps")
        print("  2. Check container logs: docker-compose logs <service>")
        print("  3. Verify ports are not in use: lsof -i :3000,9090,8000")
        print("  4. Wait a few seconds for services to fully start\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
