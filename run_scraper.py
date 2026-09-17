from __future__ import annotations

import argparse
import csv
import json

from scraper.database.duckdb import DuckDBLeadRepository
from scraper.discovery import SearchRequest, WebDiscovery
from scraper.engine import ScrapeResult, scrape
from scraper.browser_fetcher import BrowserFetcher
from scraper.providers.brave import BraveSearchProvider
from scraper.providers.firecrawl import FirecrawlProvider
from scraper.providers.scrape_do import ScrapeDoProvider
from scraper.providers.scrapingdog import ScrapingdogProvider
from scraper.providers.searxng import SearXNGProvider
from scraper.source_google_maps import GoogleMapsAdapter
from scraper.source_google_maps_browser import (
    GoogleMapsBrowserAdapter,
    default_browser_factory as google_maps_browser_factory,
)
from scraper.source_justdial_browser import (
    JustdialBrowserAdapter,
    default_browser_factory as justdial_browser_factory,
)


def positive_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc

    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    return limit


def non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError("value must be an integer") from exc

    if number < 0:
        raise ValueError("value must be greater than or equal to 0")

    return number


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError("value must be a number") from exc

    if number <= 0:
        raise ValueError("value must be greater than 0")

    return number


def non_empty(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("value must not be empty")

    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="General Scraper Engine — public-web lead discovery"
    )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

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
        "--category",
        default="",
        help="Optional lead category filter",
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

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    parser.add_argument(
        "--provider",
        choices=("brave", "searxng"),
        default="brave",
        help="Discovery provider (default: brave)",
    )

    parser.add_argument(
        "--source",
        choices=(
            "discovery",
            "google-maps",
            "google-maps-browser",
            "justdial-browser",
        ),
        default="discovery",
        help="Lead source (default: discovery)",
    )

    parser.add_argument(
        "--google-maps-api-key",
        default="",
        help="Google Maps Places API key; otherwise GOOGLE_MAPS_API_KEY is used",
    )

    parser.add_argument(
        "--source-timeout",
        type=positive_float,
        default=15.0,
        help="Timeout for Google Maps/Justdial source requests (default: 15)",
    )

    parser.add_argument(
        "--source-wait",
        type=non_negative_int,
        default=1,
        help="Browser wait after page load in seconds (default: 1)",
    )

    parser.add_argument(
        "--searxng-url",
        default="http://127.0.0.1:8080",
        help="SearXNG base URL (default: http://127.0.0.1:8080)",
    )

    # ------------------------------------------------------------------
    # Fetch / acquisition
    # ------------------------------------------------------------------

    parser.add_argument(
        "--fetcher",
        choices=(
            "default",
            "browser",
            "firecrawl",
            "scrape-do",
            "scrapingdog",
        ),
        default="default",
        help="Page acquisition strategy (default: default)",
    )

    parser.add_argument(
        "--browser-timeout",
        type=positive_float,
        default=15.0,
        help="Browser timeout in seconds (default: 15)",
    )

    parser.add_argument(
        "--browser-wait",
        type=non_negative_int,
        default=0,
        help="Wait after page load in seconds (default: 0)",
    )

    parser.add_argument(
        "--wait-for-selector",
        default="",
        help="Optional CSS selector to wait for in browser mode",
    )

    parser.add_argument(
        "--scroll-steps",
        type=non_negative_int,
        default=0,
        help="Number of browser scroll steps (default: 0)",
    )

    parser.add_argument(
        "--click-selector",
        default="",
        help="Optional CSS selector to click in browser mode",
    )

    parser.add_argument(
        "--max-concurrency",
        type=positive_limit,
        default=2,
        help="Browser fetch concurrency (default: 2)",
    )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

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


def build_fetcher(args: argparse.Namespace):
    fetcher_name = getattr(args, "fetcher", "default")

    if fetcher_name == "browser":
        return BrowserFetcher(
            timeout=getattr(args, "browser_timeout", 15.0),
            wait_for_timeout=getattr(args, "browser_wait", 0),
            wait_for_selector=(
                getattr(args, "wait_for_selector", "") or None
            ),
            scroll_steps=getattr(args, "scroll_steps", 0),
            click_selector=(
                getattr(args, "click_selector", "") or None
            ),
            max_concurrency=getattr(args, "max_concurrency", 2),
        )

    if fetcher_name == "firecrawl":
        return FirecrawlProvider()

    if fetcher_name == "scrape-do":
        return ScrapeDoProvider()

    if fetcher_name == "scrapingdog":
        return ScrapingdogProvider()

    return None


def build_discovery(args: argparse.Namespace):
    provider_name = getattr(args, "provider", "brave")

    if provider_name == "searxng":
        provider = SearXNGProvider(
            base_url=getattr(
                args,
                "searxng_url",
                "http://127.0.0.1:8080",
            )
        )
    else:
        provider = BraveSearchProvider()

    return provider, WebDiscovery(providers=[provider])


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
    fieldnames = (
        list(result.leads[0].to_dict().keys())
        if result.leads
        else []
    )

    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for lead in result.leads:
            row = lead.to_dict()

            for field in (
                "social_profiles",
                "extra",
                "raw_data",
            ):
                if field in row:
                    row[field] = json.dumps(
                        row[field],
                        ensure_ascii=False,
                    )

            writer.writerow(row)


def run_direct_source(args: argparse.Namespace):
    request = SearchRequest(
        keyword=args.keyword,
        location=args.location,
        requirements=args.requirements,
        limit=args.limit,
        category=getattr(args, "category", ""),
    )

    source = getattr(args, "source", "discovery")
    adapter = None

    if source == "google-maps":
        adapter = GoogleMapsAdapter(
            api_key=getattr(args, "google_maps_api_key", "") or None,
            timeout=getattr(args, "source_timeout", 15.0),
        )

    elif source == "google-maps-browser":
        adapter = GoogleMapsBrowserAdapter(
            google_maps_browser_factory,
            timeout=getattr(args, "source_timeout", 15.0),
            wait_for_timeout=getattr(args, "source_wait", 1),
        )

    elif source == "justdial-browser":
        adapter = JustdialBrowserAdapter(
            justdial_browser_factory,
            timeout=getattr(args, "source_timeout", 15.0),
            wait_for_timeout=getattr(args, "source_wait", 1),
        )

    else:
        return None

    repository = None

    if getattr(args, "save_db", False):
        repository = DuckDBLeadRepository(
            getattr(args, "db_path", "data/leads.duckdb")
        )

    try:
        leads = adapter.search(request)

        # Apply the same existing Lead-level safeguards used by the engine.
        from scraper.location import LocationValidator
        from scraper.normalizer import LeadNormalizer
        from scraper.quality import LeadQuality

        location_validator = LocationValidator(request.location)
        quality = LeadQuality()
        normalizer = LeadNormalizer()

        filtered_leads = []

        for lead in leads:
            if not location_validator.is_relevant(lead):
                continue

            if not quality.is_valid(lead):
                continue

            filtered_leads.append(lead)

        leads = normalizer.deduplicate_leads(filtered_leads)

        category = request.category.strip().casefold()

        if category:
            leads = [
                lead
                for lead in leads
                if lead.category.strip().casefold() == category
            ]

        if repository is not None:
            for lead in leads:
                repository.save(lead)

        return argparse.Namespace(
            count=len(leads),
            leads=leads,
            discovered=[],
            fetched=[],
            fetch_failures=[],
            parse_failures=[],
        )
    finally:
        close = getattr(adapter, "close", None)
        if close is not None:
            close()

        if repository is not None:
            repository.close()


def run(args: argparse.Namespace) -> ScrapeResult:
    if getattr(args, "source", "discovery") != "discovery":
        return run_direct_source(args)

    request = SearchRequest(
        keyword=args.keyword,
        location=args.location,
        requirements=args.requirements,
        limit=args.limit,
        category=getattr(args, "category", ""),
    )

    provider, discovery = build_discovery(args)
    fetcher = build_fetcher(args)

    save_db = getattr(args, "save_db", False)
    db_path = getattr(
        args,
        "db_path",
        "data/leads.duckdb",
    )

    repository = (
        DuckDBLeadRepository(db_path)
        if save_db
        else None
    )

    try:
        scrape_kwargs = {
            "request": request,
            "discovery": discovery,
        }

        if fetcher is not None:
            scrape_kwargs["fetcher"] = fetcher

        if repository is not None:
            scrape_kwargs["repository"] = repository

        return scrape(**scrape_kwargs)

    finally:
        close = getattr(provider, "close", None)

        if close is not None:
            close()

        if fetcher is not None:
            fetcher_close = getattr(fetcher, "close", None)

            if fetcher_close is not None:
                fetcher_close()


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
