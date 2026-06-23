# API Load Testing

Run these tests against local or staging environments. Avoid production unless the team has approved the load window.

## Health Check Load

```powershell
python load_tests/api_load_test.py --base-url http://localhost:8001 --scenario health --users 25 --duration 60 --ramp-up 10
```

## Authenticated CRM Read Load

Set a valid FastAPI bearer token first:

```powershell
$env:LOAD_TEST_TOKEN="your-access-token"
python load_tests/api_load_test.py --base-url http://localhost:8001 --scenario crm-read --users 50 --duration 120 --ramp-up 20
```

## Authenticated Reports Load

```powershell
$env:LOAD_TEST_TOKEN="your-access-token"
python load_tests/api_load_test.py --base-url http://localhost:8001 --scenario reports --users 30 --duration 120 --ramp-up 15 --fail-p95-ms 750
```

The runner prints request count, requests per second, status-code distribution, error rate, and latency min/avg/p50/p95/p99/max.
