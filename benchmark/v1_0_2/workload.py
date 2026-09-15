from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    path: str
    expected_status: int
    expected_success: bool


def build_workload(base_url: str = "http://127.0.0.1:8766") -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            name="static_valid",
            path=f"{base_url}/static",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="structured_jsonld",
            path=f"{base_url}/structured",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="thin_content",
            path=f"{base_url}/thin",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="http_error",
            path=f"{base_url}/error",
            expected_status=500,
            expected_success=False,
        ),
        BenchmarkCase(
            name="slow_response",
            path=f"{base_url}/slow",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="repeated_url",
            path=f"{base_url}/static",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="multi_1",
            path=f"{base_url}/multi/1",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="multi_2",
            path=f"{base_url}/multi/2",
            expected_status=200,
            expected_success=True,
        ),
        BenchmarkCase(
            name="multi_3",
            path=f"{base_url}/multi/3",
            expected_status=200,
            expected_success=True,
        ),
        *[
            BenchmarkCase(
                name=f"batch_{index}",
                path=f"{base_url}/multi/{index}",
                expected_status=200,
                expected_success=True,
            )
            for index in range(4, 21)
        ],
    ]
