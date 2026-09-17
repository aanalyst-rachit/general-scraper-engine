from __future__ import annotations

from scraper.database.run_metrics import RunMetrics, RunMetricsRepository


def make_repository(tmp_path):
    return RunMetricsRepository(tmp_path / "metrics.duckdb")


def test_run_metrics_persists_core_run_data(tmp_path):
    repository = make_repository(tmp_path)

    metrics = RunMetrics(
        run_id="run-001",
        started_at="2026-09-16T10:00:00+00:00",
        finished_at="2026-09-16T10:00:01+00:00",
        duration_ms=1000.0,
        discovered_count=10,
        candidate_count=8,
        fetched_count=8,
        fetch_failure_count=1,
        parse_failure_count=1,
        lead_count=5,
        existing_lead_count=2,
        quality_checked_count=6,
        quality_accepted_count=5,
        quality_rejected_count=1,
    )

    repository.save(metrics)

    stored = repository.get("run-001")

    assert stored is not None
    assert stored.run_id == "run-001"
    assert stored.duration_ms == 1000.0
    assert stored.discovered_count == 10
    assert stored.candidate_count == 8
    assert stored.fetched_count == 8
    assert stored.fetch_failure_count == 1
    assert stored.parse_failure_count == 1
    assert stored.lead_count == 5
    assert stored.existing_lead_count == 2
    assert stored.quality_checked_count == 6
    assert stored.quality_accepted_count == 5
    assert stored.quality_rejected_count == 1


def test_run_metrics_persists_operational_metadata(tmp_path):
    repository = make_repository(tmp_path)

    metrics = RunMetrics(
        run_id="run-002",
        started_at="2026-09-16T10:00:00+00:00",
        finished_at="2026-09-16T10:00:02+00:00",
        duration_ms=2000.0,
        failure_categories={"timeout": 2, "rate-limit": 1},
        browser_fallback_count=3,
        external_fallback_count=1,
        cache_hits=7,
        cache_misses=4,
        provider="brave",
        provider_config={"country": "IN"},
    )

    repository.save(metrics)

    stored = repository.get("run-002")

    assert stored is not None
    assert stored.failure_categories == {"timeout": 2, "rate-limit": 1}
    assert stored.browser_fallback_count == 3
    assert stored.external_fallback_count == 1
    assert stored.cache_hits == 7
    assert stored.cache_misses == 4
    assert stored.provider == "brave"
    assert stored.provider_config == {"country": "IN"}


def test_run_metrics_returns_historical_runs_in_start_order(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        RunMetrics(
            run_id="run-later",
            started_at="2026-09-16T11:00:00+00:00",
            duration_ms=250.0,
            lead_count=8,
        )
    )
    repository.save(
        RunMetrics(
            run_id="run-earlier",
            started_at="2026-09-16T10:00:00+00:00",
            duration_ms=150.0,
            lead_count=5,
        )
    )

    history = repository.all()

    assert [metrics.run_id for metrics in history] == [
        "run-earlier",
        "run-later",
    ]
    assert [metrics.duration_ms for metrics in history] == [150.0, 250.0]
    assert [metrics.lead_count for metrics in history] == [5, 8]


def test_run_metrics_starts_empty(tmp_path):
    repository = make_repository(tmp_path)

    assert repository.get("missing") is None
    assert repository.all() == []
