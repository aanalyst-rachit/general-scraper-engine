from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class RunMetrics:
    run_id: str
    started_at: str
    finished_at: str | None = None
    duration_ms: float | None = None
    discovered_count: int = 0
    candidate_count: int = 0
    fetched_count: int = 0
    fetch_failure_count: int = 0
    parse_failure_count: int = 0
    lead_count: int = 0
    existing_lead_count: int = 0
    quality_checked_count: int = 0
    quality_accepted_count: int = 0
    quality_rejected_count: int = 0
    failure_categories: dict[str, int] = field(default_factory=dict)
    browser_fallback_count: int = 0
    external_fallback_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    provider: str | None = None
    provider_config: dict[str, Any] = field(default_factory=dict)


class RunMetricsRepository:
    def __init__(self, database_path: str | Path = "data/run_metrics.duckdb"):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return duckdb.connect(self.database_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS run_metrics (
                    run_id VARCHAR PRIMARY KEY,
                    started_at VARCHAR NOT NULL,
                    finished_at VARCHAR,
                    duration_ms DOUBLE,
                    discovered_count INTEGER NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    fetched_count INTEGER NOT NULL,
                    fetch_failure_count INTEGER NOT NULL,
                    parse_failure_count INTEGER NOT NULL,
                    lead_count INTEGER NOT NULL,
                    existing_lead_count INTEGER NOT NULL,
                    quality_checked_count INTEGER NOT NULL,
                    quality_accepted_count INTEGER NOT NULL,
                    quality_rejected_count INTEGER NOT NULL,
                    failure_categories JSON NOT NULL,
                    browser_fallback_count INTEGER NOT NULL,
                    external_fallback_count INTEGER NOT NULL,
                    cache_hits INTEGER NOT NULL,
                    cache_misses INTEGER NOT NULL,
                    provider VARCHAR,
                    provider_config JSON NOT NULL
                )
            """)

    def save(self, metrics: RunMetrics) -> RunMetrics:
        values = asdict(metrics)

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO run_metrics (
                    run_id, started_at, finished_at, duration_ms,
                    discovered_count, candidate_count, fetched_count,
                    fetch_failure_count, parse_failure_count, lead_count,
                    existing_lead_count, quality_checked_count,
                    quality_accepted_count, quality_rejected_count,
                    failure_categories, browser_fallback_count,
                    external_fallback_count, cache_hits, cache_misses,
                    provider, provider_config
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    values["run_id"],
                    values["started_at"],
                    values["finished_at"],
                    values["duration_ms"],
                    values["discovered_count"],
                    values["candidate_count"],
                    values["fetched_count"],
                    values["fetch_failure_count"],
                    values["parse_failure_count"],
                    values["lead_count"],
                    values["existing_lead_count"],
                    values["quality_checked_count"],
                    values["quality_accepted_count"],
                    values["quality_rejected_count"],
                    json.dumps(values["failure_categories"]),
                    values["browser_fallback_count"],
                    values["external_fallback_count"],
                    values["cache_hits"],
                    values["cache_misses"],
                    values["provider"],
                    json.dumps(values["provider_config"]),
                ],
            )

        return metrics

    def get(self, run_id: str) -> RunMetrics | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, started_at, finished_at, duration_ms,
                       discovered_count, candidate_count, fetched_count,
                       fetch_failure_count, parse_failure_count, lead_count,
                       existing_lead_count, quality_checked_count,
                       quality_accepted_count, quality_rejected_count,
                       failure_categories, browser_fallback_count,
                       external_fallback_count, cache_hits, cache_misses,
                       provider, provider_config
                FROM run_metrics
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()

        return None if row is None else self._row_to_metrics(row)

    def all(self) -> list[RunMetrics]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, started_at, finished_at, duration_ms,
                       discovered_count, candidate_count, fetched_count,
                       fetch_failure_count, parse_failure_count, lead_count,
                       existing_lead_count, quality_checked_count,
                       quality_accepted_count, quality_rejected_count,
                       failure_categories, browser_fallback_count,
                       external_fallback_count, cache_hits, cache_misses,
                       provider, provider_config
                FROM run_metrics
                ORDER BY started_at ASC, run_id ASC
                """
            ).fetchall()

        return [self._row_to_metrics(row) for row in rows]

    @staticmethod
    def _decode_json(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, str):
            return json.loads(value)
        return dict(value)

    @classmethod
    def _row_to_metrics(cls, row: tuple[Any, ...]) -> RunMetrics:
        return RunMetrics(
            run_id=row[0],
            started_at=row[1],
            finished_at=row[2],
            duration_ms=row[3],
            discovered_count=row[4],
            candidate_count=row[5],
            fetched_count=row[6],
            fetch_failure_count=row[7],
            parse_failure_count=row[8],
            lead_count=row[9],
            existing_lead_count=row[10],
            quality_checked_count=row[11],
            quality_accepted_count=row[12],
            quality_rejected_count=row[13],
            failure_categories=cls._decode_json(row[14]),
            browser_fallback_count=row[15],
            external_fallback_count=row[16],
            cache_hits=row[17],
            cache_misses=row[18],
            provider=row[19],
            provider_config=cls._decode_json(row[20]),
        )

    def close(self) -> None:
        return None
