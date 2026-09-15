import argparse
import csv
import json

import run_scraper
from scraper.models import Lead


def test_parser_requires_keyword():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor"])

    assert args.keyword == "doctor"
    assert args.location == ""
    assert args.requirements == ""


def test_parser_accepts_keyword_location_and_requirements():
    parser = run_scraper.build_parser()

    args = parser.parse_args(
        [
            "--keyword",
            "doctor",
            "--location",
            "Shahjahanpur",
            "--requirements",
            "general physician",
        ]
    )

    assert args.keyword == "doctor"
    assert args.location == "Shahjahanpur"
    assert args.requirements == "general physician"


def test_run_builds_search_request(monkeypatch):
    captured = {}

    class FakeProvider:
        def close(self):
            captured["closed"] = True

    def fake_scrape(*, request, discovery):
        captured["request"] = request
        captured["discovery"] = discovery
        return argparse.Namespace(count=0, leads=[])

    monkeypatch.setattr(run_scraper, "BraveSearchProvider", lambda: FakeProvider())
    monkeypatch.setattr(run_scraper, "scrape", fake_scrape)

    args = argparse.Namespace(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="general physician",
        limit=50,
    )

    result = run_scraper.run(args)

    assert result.count == 0
    assert captured["request"].keyword == "doctor"
    assert captured["request"].location == "Shahjahanpur"
    assert captured["request"].requirements == "general physician"
    assert len(captured["discovery"].providers) == 1
    assert captured["closed"] is True


def test_format_result():
    result = argparse.Namespace(
        count=1,
        leads=[
            Lead(
                name="Dr. Raj Kumar",
                category="doctor",
                location="Shahjahanpur",
                address="Civil Lines",
                phone="+91 98765 43210",
                email="doctor@example.com",
                website="https://example.com",
                source_url="https://source.example.com/doctor",
                source_name="example",
            )
        ],
        discovered=[],
        fetched=[],
        fetch_failures=[],
        parse_failures=[],
    )

    output = run_scraper.format_result(result)

    assert "Found: 1 leads" in output
    assert "1. Dr. Raj Kumar" in output
    assert "Category     : doctor" in output
    assert "Location     : Shahjahanpur" in output
    assert "Phone        : +91 98765 43210" in output
    assert "Website      : https://example.com" in output
    assert "Source Name  : example" in output
    assert "Source URL   : https://source.example.com/doctor" in output
    assert "----- Summary -----" in output
    assert "Discovered     : 0" in output
    assert "Fetched        : 0" in output
    assert "Fetch failures : 0" in output
    assert "Parse failures : 0" in output

def test_parser_default_limit():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor"])

    assert args.limit == 50


def test_parser_accepts_explicit_limit():
    parser = run_scraper.build_parser()

    args = parser.parse_args(
        [
            "--keyword",
            "doctor",
            "--limit",
            "25",
        ]
    )

    assert args.limit == 25


def test_run_passes_limit_to_search_request(monkeypatch):
    captured = {}

    class FakeProvider:
        def close(self):
            captured["closed"] = True

    def fake_scrape(*, request, discovery):
        captured["request"] = request
        captured["discovery"] = discovery
        return argparse.Namespace(count=0, leads=[])

    monkeypatch.setattr(run_scraper, "BraveSearchProvider", lambda: FakeProvider())
    monkeypatch.setattr(run_scraper, "scrape", fake_scrape)

    args = argparse.Namespace(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="general physician",
        limit=25,
    )

    result = run_scraper.run(args)

    assert result.count == 0
    assert captured["request"].limit == 25
    assert captured["closed"] is True


def test_parser_rejects_blank_keyword():
    parser = run_scraper.build_parser()

    try:
        parser.parse_args(["--keyword", "   "])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("blank keyword should be rejected")


def test_parser_rejects_zero_limit():
    parser = run_scraper.build_parser()

    try:
        parser.parse_args(["--keyword", "doctor", "--limit", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("zero limit should be rejected")


def test_parser_rejects_non_integer_limit():
    parser = run_scraper.build_parser()

    try:
        parser.parse_args(["--keyword", "doctor", "--limit", "abc"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("non-integer limit should be rejected")

def test_parser_accepts_json_output():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor", "--json", "results.json"])

    assert args.json_path == "results.json"


def test_parser_accepts_csv_output():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor", "--csv", "results.csv"])

    assert args.csv_path == "results.csv"


def test_write_json(tmp_path):
    result = argparse.Namespace(
        leads=[
            Lead(
                name="Dr. Raj Kumar",
                category="doctor",
                location="Shahjahanpur",
                phone="+91 98765 43210",
                source_url="https://source.example.com/doctor",
                source_name="example",
                extra={"specialty": "general medicine"},
            )
        ],
    )

    path = tmp_path / "results.json"

    run_scraper.write_json(result, str(path))

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload[0]["name"] == "Dr. Raj Kumar"
    assert payload[0]["phone"] == "+91 98765 43210"
    assert payload[0]["source_name"] == "example"
    assert payload[0]["extra"]["specialty"] == "general medicine"


def test_write_csv(tmp_path):
    result = argparse.Namespace(
        leads=[
            Lead(
                name="Dr. Raj Kumar",
                category="doctor",
                location="Shahjahanpur",
                phone="+91 98765 43210",
                source_url="https://source.example.com/doctor",
                source_name="example",
                extra={"specialty": "general medicine"},
            )
        ],
    )

    path = tmp_path / "results.csv"

    run_scraper.write_csv(result, str(path))

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows[0]["name"] == "Dr. Raj Kumar"
    assert rows[0]["phone"] == "+91 98765 43210"
    assert rows[0]["source_name"] == "example"
    assert json.loads(rows[0]["extra"])["specialty"] == "general medicine"

def test_parser_defaults_to_brave_provider():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor"])

    assert args.provider == "brave"
    assert args.searxng_url == "http://127.0.0.1:8080"


def test_parser_accepts_searxng_provider():
    parser = run_scraper.build_parser()

    args = parser.parse_args([
        "--keyword", "doctor",
        "--provider", "searxng",
        "--searxng-url", "http://localhost:9090",
    ])

    assert args.provider == "searxng"
    assert args.searxng_url == "http://localhost:9090"


def test_run_uses_searxng_provider(monkeypatch):
    captured = {}

    class FakeProvider:
        def __init__(self, base_url):
            captured["base_url"] = base_url

        def close(self):
            captured["closed"] = True

    def fake_scrape(*, request, discovery):
        captured["request"] = request
        captured["discovery"] = discovery
        return argparse.Namespace(count=0, leads=[])

    monkeypatch.setattr(run_scraper, "SearXNGProvider", FakeProvider)
    monkeypatch.setattr(run_scraper, "scrape", fake_scrape)

    args = argparse.Namespace(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="",
        limit=50,
        provider="searxng",
        searxng_url="http://127.0.0.1:8080",
    )

    result = run_scraper.run(args)

    assert result.count == 0
    assert captured["base_url"] == "http://127.0.0.1:8080"
    assert len(captured["discovery"].providers) == 1
    assert captured["closed"] is True

def test_parser_defaults_to_no_db_save():
    parser = run_scraper.build_parser()

    args = parser.parse_args(["--keyword", "doctor"])

    assert args.save_db is False
    assert args.db_path == "data/leads.duckdb"


def test_parser_accepts_db_options():
    parser = run_scraper.build_parser()

    args = parser.parse_args([
        "--keyword", "doctor",
        "--save-db",
        "--db-path", "tmp/test.duckdb",
    ])

    assert args.save_db is True
    assert args.db_path == "tmp/test.duckdb"


def test_run_passes_duckdb_repository(monkeypatch, tmp_path):
    captured = {}

    class FakeProvider:
        def close(self):
            captured["closed"] = True

    class FakeRepository:
        def __init__(self, path):
            captured["db_path"] = path

    def fake_scrape(*, request, discovery, repository):
        captured["request"] = request
        captured["discovery"] = discovery
        captured["repository"] = repository
        return argparse.Namespace(count=0, leads=[])

    monkeypatch.setattr(run_scraper, "BraveSearchProvider", lambda: FakeProvider())
    monkeypatch.setattr(run_scraper, "DuckDBLeadRepository", FakeRepository)
    monkeypatch.setattr(run_scraper, "scrape", fake_scrape)

    db_path = tmp_path / "leads.duckdb"
    args = argparse.Namespace(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="",
        limit=20,
        provider="brave",
        searxng_url="http://127.0.0.1:8080",
        save_db=True,
        db_path=str(db_path),
    )

    result = run_scraper.run(args)

    assert result.count == 0
    assert captured["db_path"] == str(db_path)
    assert captured["repository"] is not None
    assert captured["closed"] is True


def test_run_without_db_save_passes_no_repository(monkeypatch):
    captured = {}

    class FakeProvider:
        def close(self):
            captured["closed"] = True

    def fake_scrape(*, request, discovery, repository=None):
        captured["repository"] = repository
        return argparse.Namespace(count=0, leads=[])

    monkeypatch.setattr(run_scraper, "BraveSearchProvider", lambda: FakeProvider())
    monkeypatch.setattr(run_scraper, "scrape", fake_scrape)

    args = argparse.Namespace(
        keyword="doctor",
        location="Shahjahanpur",
        requirements="",
        limit=20,
        provider="brave",
        searxng_url="http://127.0.0.1:8080",
        save_db=False,
        db_path="data/leads.duckdb",
    )

    run_scraper.run(args)

    assert captured["repository"] is None
    assert captured["closed"] is True
