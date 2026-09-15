from __future__ import annotations

import argparse
import csv
import json

from scraper.database.duckdb import DuckDBLeadRepository
from scraper.discovery import SearchRequest, WebDiscovery
from scraper.engine import ScrapeResult, scrape
from scraper.providers.brave import BraveSearchProvider
from scraper.providers.searxng import SearXNGProvider


def positive_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    if limit <= 0:
        raise ValueError("limit must be greater than 0")
    return limit


def non_empty(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("value must not be empty")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="General Scraper Engine — public-web lead discovery"
    )
    parser.add_argument(
        "--keyword",
        required=True,
        type=non_empty,
        help="What to search for, e.g. doctor, dentist, restaurant",
    )
    parser.add_argument(
        "--location",
        default="",
        help="Target location, e.g. Shahjahanpur, Uttar Pradesh",
    )
    parser.add_argument(
        "--requirements",
        default="",
        help="Optional additional requirements, e.g. homeopathy or emergency",
    )
    parser.add_argument(
        "--limit",
        type=positive_limit,
        default=50,
        help="Maximum number of discovered pages to process (default: 50)",
    )
    parser.add_argument(
        "--provider",
        choices=("brave", "searxng"),
        default="brave",
        help="Discovery provider (default: brave)",
    )
    parser.add_argument(
        "--searxng-url",
        default="http://127.0.0.1:8080",
        help="SearXNG base URL (default: http://127.0.0.1:8080)",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default="",
        help="Write structured lead results to a JSON file",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default="",
        help="Write structured lead results to a CSV file",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Persist scraped leads to DuckDB",
    )
    parser.add_argument(
        "--db-path",
        default="data/leads.duckdb",
        help="DuckDB database path (default: data/leads.duckdb)",
    )
    return parser


def format_result(result: ScrapeResult) -> str:
    lines = [
        f"Found: {result.count} leads",
        "",
    ]

    for index, lead in enumerate(result.leads, start=1):
        lines.extend(
            [
                f"{index}. {lead.name}",
                f"   Category     : {lead.category}",
                f"   Location     : {lead.location}",
                f"   Address      : {lead.address}",
                f"   Phone        : {lead.phone}",
                f"   Email        : {lead.email}",
                f"   Website      : {lead.website}",
                f"   Source Name  : {lead.source_name}",
                f"   Source URL   : {lead.source_url}",
                "",
            ]
        )

    lines.extend(
        [
            "----- Summary -----",
            f"Discovered     : {len(result.discovered)}",
            f"Fetched        : {len(result.fetched)}",
            f"Fetch failures : {len(result.fetch_failures)}",
            f"Parse failures : {len(result.parse_failures)}",
        ]
    )

    return "\n".join(lines).rstrip()


def write_json(result: ScrapeResult, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(
            [lead.to_dict() for lead in result.leads],
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")


def write_csv(result: ScrapeResult, path: str) -> None:
    fieldnames = list(result.leads[0].to_dict().keys()) if result.leads else []

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for lead in result.leads:
            row = lead.to_dict()

            for field in ("social_profiles", "extra", "raw_data"):
                row[field] = json.dumps(
                    row[field],
                    ensure_ascii=False,
                )

            writer.writerow(row)


def run(args: argparse.Namespace) -> ScrapeResult:
    request = SearchRequest(
        keyword=args.keyword,
        location=args.location,
        requirements=args.requirements,
        limit=args.limit,
    )

    provider_name = getattr(args, "provider", "brave")
    searxng_url = getattr(args, "searxng_url", "http://127.0.0.1:8080")
    save_db = getattr(args, "save_db", False)
    db_path = getattr(args, "db_path", "data/leads.duckdb")

    if provider_name == "searxng":
        provider = SearXNGProvider(base_url=searxng_url)
    else:
        provider = BraveSearchProvider()

    discovery = WebDiscovery(providers=[provider])
    repository = DuckDBLeadRepository(db_path) if save_db else None

    try:
        if repository is not None:
            return scrape(
                request=request,
                discovery=discovery,
                repository=repository,
            )

        return scrape(
            request=request,
            discovery=discovery,
        )
    finally:
        provider.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run(args)
    except Exception as exc:
        parser.error(str(exc))

    print(format_result(result))

    if args.json_path:
        write_json(result, args.json_path)

    if args.csv_path:
        write_csv(result, args.csv_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
