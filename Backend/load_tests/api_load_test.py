from __future__ import annotations

import argparse
import asyncio
import os
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    auth_required: bool = True
    json_body: dict[str, Any] | None = None
    params: dict[str, Any] | None = None


SCENARIOS: dict[str, list[Endpoint]] = {
    "health": [
        Endpoint("GET", "/health", auth_required=False),
    ],
    "reports": [
        Endpoint("GET", "/api/v1/reports/dashboard"),
        Endpoint("GET", "/api/v1/reports/pipeline-summary"),
        Endpoint("GET", "/api/v1/reports/lead-funnel"),
        Endpoint(
            "POST",
            "/api/v1/reports/custom",
            json_body={
                "entity": "deals",
                "fields": ["title", "value", "status"],
                "sort_by": "created_at",
                "sort_dir": "desc",
            },
        ),
    ],
    "crm-read": [
        Endpoint("GET", "/api/v1/leads/", params={"page": 1, "page_size": 25}),
        Endpoint("GET", "/api/v1/contacts/", params={"page": 1, "page_size": 25}),
        Endpoint("GET", "/api/v1/accounts/", params={"page": 1, "page_size": 25}),
        Endpoint("GET", "/api/v1/deals/", params={"page": 1, "page_size": 25}),
        Endpoint("GET", "/api/v1/tasks/", params={"page": 1, "page_size": 25}),
        Endpoint("GET", "/api/v1/reports/dashboard"),
    ],
}


class Recorder:
    def __init__(self) -> None:
        self.latencies_ms: list[float] = []
        self.statuses: Counter[int] = Counter()
        self.errors: Counter[str] = Counter()
        self.total_requests = 0
        self._lock = asyncio.Lock()

    async def record(self, *, latency_ms: float, status_code: int | None = None, error: str | None = None) -> None:
        async with self._lock:
            self.total_requests += 1
            self.latencies_ms.append(latency_ms)
            if status_code is not None:
                self.statuses[status_code] += 1
            if error:
                self.errors[error] += 1


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = (len(ordered) - 1) * percent
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


async def run_request(client: httpx.AsyncClient, endpoint: Endpoint, headers: dict[str, str], recorder: Recorder) -> None:
    start = time.perf_counter()
    try:
        response = await client.request(
            endpoint.method,
            endpoint.path,
            headers=headers if endpoint.auth_required else None,
            json=endpoint.json_body,
            params=endpoint.params,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        await recorder.record(latency_ms=latency_ms, status_code=response.status_code)
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        await recorder.record(latency_ms=latency_ms, error=exc.__class__.__name__)


async def worker(
    worker_id: int,
    *,
    client: httpx.AsyncClient,
    duration_seconds: float,
    endpoints: list[Endpoint],
    headers: dict[str, str],
    ramp_up_seconds: float,
    recorder: Recorder,
    worker_count: int,
) -> None:
    if ramp_up_seconds > 0:
        await asyncio.sleep((worker_id / max(worker_count, 1)) * min(ramp_up_seconds, duration_seconds))

    deadline = time.monotonic() + duration_seconds
    while time.monotonic() < deadline:
        await run_request(client, random.choice(endpoints), headers, recorder)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run async load tests against the Doxa CRM API.")
    parser.add_argument("--base-url", default=os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8001"))
    parser.add_argument("--token", default=os.getenv("LOAD_TEST_TOKEN"), help="Bearer token for protected API routes.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="health")
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--ramp-up", type=float, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--fail-error-rate", type=float, default=0.05)
    parser.add_argument("--fail-p95-ms", type=float, default=0, help="Fail when p95 exceeds this value. Disabled at 0.")
    return parser


def validate_args(args: argparse.Namespace, endpoints: list[Endpoint]) -> None:
    if args.users < 1:
        raise SystemExit("--users must be at least 1")
    if args.duration <= 0:
        raise SystemExit("--duration must be greater than 0")
    if args.ramp_up < 0:
        raise SystemExit("--ramp-up cannot be negative")
    if any(endpoint.auth_required for endpoint in endpoints) and not args.token:
        raise SystemExit("This scenario hits protected endpoints. Set --token or LOAD_TEST_TOKEN.")


def print_summary(args: argparse.Namespace, recorder: Recorder, elapsed_seconds: float) -> int:
    latencies = recorder.latencies_ms
    status_errors = sum(count for status, count in recorder.statuses.items() if status >= 400)
    exception_errors = sum(recorder.errors.values())
    failed = status_errors + exception_errors
    error_rate = failed / recorder.total_requests if recorder.total_requests else 0.0
    p95 = percentile(latencies, 0.95)

    print("\nDoxa CRM load test")
    print(f"scenario: {args.scenario}")
    print(f"base_url: {args.base_url.rstrip('/')}")
    print(f"users: {args.users}")
    print(f"duration_seconds: {elapsed_seconds:.1f}")
    print(f"requests: {recorder.total_requests}")
    print(f"requests_per_second: {(recorder.total_requests / elapsed_seconds) if elapsed_seconds else 0:.2f}")
    print(f"error_rate: {error_rate:.2%}")
    print(f"status_codes: {dict(sorted(recorder.statuses.items()))}")
    if recorder.errors:
        print(f"exceptions: {dict(recorder.errors)}")
    print(f"latency_min_ms: {min(latencies) if latencies else 0:.2f}")
    print(f"latency_avg_ms: {statistics.fmean(latencies) if latencies else 0:.2f}")
    print(f"latency_p50_ms: {percentile(latencies, 0.50):.2f}")
    print(f"latency_p95_ms: {p95:.2f}")
    print(f"latency_p99_ms: {percentile(latencies, 0.99):.2f}")
    print(f"latency_max_ms: {max(latencies) if latencies else 0:.2f}")

    failed_threshold = error_rate > args.fail_error_rate
    failed_latency = args.fail_p95_ms > 0 and p95 > args.fail_p95_ms
    return 1 if failed_threshold or failed_latency else 0


async def async_main() -> int:
    args = build_parser().parse_args()
    endpoints = SCENARIOS[args.scenario]
    validate_args(args, endpoints)

    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    recorder = Recorder()
    started_at = time.perf_counter()

    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=args.timeout) as client:
        await asyncio.gather(
            *[
                worker(
                    worker_id,
                    client=client,
                    duration_seconds=args.duration,
                    endpoints=endpoints,
                    headers=headers,
                    ramp_up_seconds=args.ramp_up,
                    recorder=recorder,
                    worker_count=args.users,
                )
                for worker_id in range(args.users)
            ]
        )

    elapsed_seconds = time.perf_counter() - started_at
    return print_summary(args, recorder, elapsed_seconds)


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
