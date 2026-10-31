"""Run after starting the API: python scripts/smoke_test.py"""
import time
import requests

BASE = "http://127.0.0.1:8000"

def check(path, expected, **kwargs):
    response = requests.get(BASE + path, timeout=20, **kwargs)
    ok = response.status_code == expected
    print(f"{'PASS' if ok else 'FAIL'} {path}: expected {expected}, got {response.status_code}")
    return ok

results = []
results.append(check("/health", 200))
results.append(check("/users", 200))
results.append(check("/products", 200))
results.append(check("/protected", 401))
results.append(check("/protected", 200, headers={"Authorization": "Bearer demo-secret-token"}))
results.append(check("/simulate-error", 500))
start = time.perf_counter()
results.append(check("/simulate-timeout?delay=3.5", 200))
print(f"Timeout simulation latency: {time.perf_counter() - start:.2f}s (should exceed 3s)")
rate_codes = [requests.get(BASE + "/simulate-rate-limit", timeout=5).status_code for _ in range(7)]
rate_ok = 429 in rate_codes
print(f"{'PASS' if rate_ok else 'FAIL'} /simulate-rate-limit: statuses={rate_codes}")
results.append(rate_ok)
results.append(check("/metrics", 200))
raise SystemExit(0 if all(results) else 1)
