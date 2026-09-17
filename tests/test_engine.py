from scraper.discovery import DiscoveredPage, SearchRequest
from scraper.engine import FetchFailure, ScraperEngine
from scraper.database.run_metrics import RunMetricsRepository
from scraper.models import Lead
from scraper.fetcher import FetchedPage
from scraper.normalizer import LeadNormalizer
from scraper.parser import PageParser


from scraper.concurrency import ConcurrencyConfig
class FakeDiscovery:
    def discover(self, request):
        assert request.keyword == "doctor"
        assert request.location == "Shahjahanpur"
        return [
            DiscoveredPage(
                url="https://example.com/raj-1",
                title="Dr Raj Kumar",
                source_name="Directory A",
            ),
            DiscoveredPage(
                url="https://example.com/raj-2",
                title="Dr Raj Kumar",
                source_name="Directory B",
            ),
            DiscoveredPage(
                url="https://example.com/amit",
                title="Dr Amit Kumar",
                source_name="Directory A",
            ),
            DiscoveredPage(
                url="https://example.com/broken",
                title="Broken Page",
                source_name="Directory C",
            ),
        ]


class FakeRepository:
    def __init__(self):
        self.saved = []
        self.search_calls = []
        self.existing = []

    def save(self, lead):
        self.saved.append(lead)
        return lead

    def search(self, keyword='', location='', limit=50):
        self.search_calls.append(
            {
                'keyword': keyword,
                'location': location,
                'limit': limit,
            }
        )
        return list(self.existing)


class FakeFetcher:
    pages = {
        "https://example.com/raj-1": FetchedPage(
            url="https://example.com/raj-1",
            final_url="https://example.com/raj-1",
            status_code=200,
            content_type="text/html",
            html="""<html><head><title>Dr Raj Kumar</title></head>
<body><p>Dr Raj Kumar</p>
<p>+91 98765 43210</p>
<p>raj@example.com</p>
<address>Main Road, Shahjahanpur, Uttar Pradesh</address>
</body></html>""",
        ),
        "https://example.com/raj-2": FetchedPage(
            url="https://example.com/raj-2",
            final_url="https://example.com/raj-2",
            status_code=200,
            content_type="text/html",
            html="""<html><head><title>Dr Raj Kumar</title></head>
<body><p>Dr Raj Kumar</p>
<p>+91-98765-43210</p>
<p>raj@example.com</p>
<address>Main Road, Shahjahanpur, Uttar Pradesh</address>
</body></html>""",
        ),
        "https://example.com/amit": FetchedPage(
            url="https://example.com/amit",
            final_url="https://example.com/amit",
            status_code=200,
            content_type="text/html",
            html="""<html><head><title>Dr Amit Kumar</title></head>
<body><p>Dr Amit Kumar</p>
<p>+91 91234 56789</p>
<p>amit@example.com</p>
<address>Civil Lines, Shahjahanpur</address>
</body></html>""",
        ),
        "https://example.com/broken": FetchedPage(
            url="https://example.com/broken",
            status_code=500,
            content_type="text/html",
            error="HTTP 500",
        ),
    }

    def fetch(self, url):
        return self.pages[url]


class MetricsFakeProvider:
    def search(self, query, limit=20):
        return [
            DiscoveredPage(
                url="https://example.com/raj-1",
                title="Dr Raj Kumar",
                source_name="Directory A",
            )
        ][:limit]

def test_engine_integration():
    engine = ScraperEngine(
        discovery=FakeDiscovery(),
        fetcher=FakeFetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
    )

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )

    result = engine.run(request)

    assert len(result.discovered) == 4
    assert len(result.fetched) == 4
    assert len(result.fetch_failures) == 1
    assert len(result.parse_failures) == 0
    assert result.count == 2

    raj = next(lead for lead in result.leads if "Raj Kumar" in lead.name)
    amit = next(lead for lead in result.leads if "Amit Kumar" in lead.name)

    assert raj.phone == "+919876543210"
    assert raj.email == "raj@example.com"
    assert raj.location == "" or "Shahjahanpur" in raj.location
    assert amit.phone == "+919123456789"

    assert result.fetch_failures[0].url == "https://example.com/broken"
    assert result.fetch_failures[0].error == "HTTP 500"

class RelevanceAwareFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.fetched = []

    def fetch(self, url):
        self.fetched.append(url)
        return self.pages[url]


class RelevanceDiscovery:
    def discover(self, request):
        return [
            DiscoveredPage(
                url='https://example.com/doctor',
                title='Dr Raj Kumar - Doctor',
                snippet='Doctor in Shahjahanpur',
            ),
            DiscoveredPage(
                url='https://example.com/weather',
                title='Shahjahanpur Weather Today',
                snippet='Latest weather forecast',
            ),
        ]


def test_engine_filters_irrelevant_candidates_before_fetch():
    fetcher = RelevanceAwareFetcher({
        'https://example.com/doctor': FetchedPage(
            url='https://example.com/doctor',
            final_url='https://example.com/doctor',
            status_code=200,
            content_type='text/html',
            html='<html><head><title>Dr Raj Kumar - Doctor</title></head><body>Doctor</body><address>Shahjahanpur</address></html>',
        ),
    })

    from scraper.relevance import KeywordRelevance, LocationRelevance

    engine = ScraperEngine(
        discovery=RelevanceDiscovery(),
        fetcher=fetcher,
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        relevance=KeywordRelevance('doctor'),
    )

    result = engine.run(
        SearchRequest(
            keyword='doctor',
            location='Shahjahanpur',
            limit=10,
        )
    )

    assert len(result.discovered) == 2
    assert fetcher.fetched == ['https://example.com/doctor']
    assert result.count == 1


class CombinedRelevanceDiscovery:
    def discover(self, request):
        return [
            DiscoveredPage(
                url='https://example.com/good',
                title='Dr Raj Kumar - Doctor Shahjahanpur',
                snippet='Doctor in Shahjahanpur',
            ),
            DiscoveredPage(
                url='https://example.com/wrong-location',
                title='Dr Amit Kumar - Doctor',
                snippet='Doctor in Lucknow',
            ),
            DiscoveredPage(
                url='https://example.com/wrong-keyword',
                title='Shahjahanpur Weather Today',
                snippet='Latest weather forecast in Shahjahanpur',
            ),
        ]


class CombinedRelevanceFetcher:
    def __init__(self):
        self.fetched = []

    def fetch(self, url):
        self.fetched.append(url)
        return FetchedPage(
            url=url,
            final_url=url,
            status_code=200,
            content_type='text/html',
            html='<html><head><title>Dr Raj Kumar - Doctor Shahjahanpur</title></head><body>Doctor Shahjahanpur</body><address>Shahjahanpur</address></html>',
        )


def make_combined_relevance_engine(fetcher):
    from scraper.relevance import KeywordRelevance, LocationRelevance

    return ScraperEngine(
        discovery=CombinedRelevanceDiscovery(),
        fetcher=fetcher,
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        relevance=KeywordRelevance('doctor'),
        location_relevance=LocationRelevance('Shahjahanpur'),
    )


def test_engine_reports_quality_measurement_separately_from_fetches():
    class QualityDiscovery:
        def discover(self, request):
            return [
                DiscoveredPage(url="https://example.com/valid"),
                DiscoveredPage(url="https://example.com/invalid"),
            ]

    class QualityFetcher:
        def fetch(self, url):
            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html="<html><body>content</body></html>",
            )

    class QualityParser:
        def parse(self, page, category=""):
            if page.url.endswith("/valid"):
                return Lead(
                    name="Valid Lead",
                    phone="9876543210",
                    location="Shahjahanpur",
                    source_url=page.url,
                )
            return Lead(
                    name="",
                    location="Shahjahanpur",
                    source_url=page.url,
                )

    engine = ScraperEngine(
        discovery=QualityDiscovery(),
        fetcher=QualityFetcher(),
        parser=QualityParser(),
        normalizer=LeadNormalizer(),
    )

    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    assert len(result.fetched) == 2
    assert result.quality_checked_count == 2
    assert result.quality_accepted_count == 1
    assert result.quality_rejected_count == 1
    assert result.count == 1


def test_engine_rejects_lead_with_wrong_extracted_location():
    class LocationDiscovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url="https://example.com/location-mismatch",
                    title="Doctor Shahjahanpur",
                    snippet="Doctor in Shahjahanpur",
                )
            ]

    class LocationFetcher:
        def fetch(self, url):
            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html="<html><body>doctor</body></html>",
            )

    class LocationMismatchParser:
        def parse(self, page, category=""):
            return Lead(
                name="Dr. Wrong Location",
                phone="9876543210",
                city="Lucknow",
                source_url=page.final_url or page.url,
            )

    engine = ScraperEngine(
        discovery=LocationDiscovery(),
        fetcher=LocationFetcher(),
        parser=LocationMismatchParser(),
        normalizer=LeadNormalizer(),
    )

    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    assert result.count == 0
    assert len(result.fetched) == 1


def test_engine_rejects_quality_valid_lead_from_irrelevant_location():
    class GeographicDiscovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url="https://example.com/lucknow-doctor",
                    title="Doctor in Lucknow",
                    snippet="Dr. Raj Kumar, Lucknow",
                )
            ]

    class GeographicFetcher:
        def fetch(self, url):
            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html="<html><body>doctor</body></html>",
            )

    class GeographicParser:
        def parse(self, page, category=""):
            return Lead(
                name="Dr. Raj Kumar",
                phone="9876543210",
                source_url=page.url,
                city="Lucknow",
                state="Uttar Pradesh",
            )

    engine = ScraperEngine(
        discovery=GeographicDiscovery(),
        fetcher=GeographicFetcher(),
        parser=GeographicParser(),
        normalizer=LeadNormalizer(),
    )

    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    assert result.count == 0
    assert result.quality_checked_count == 0
    assert result.quality_accepted_count == 0
    assert result.quality_rejected_count == 0
    assert len(result.fetched) == 1


def test_engine_requires_keyword_and_location_relevance():
    fetcher = CombinedRelevanceFetcher()
    engine = make_combined_relevance_engine(fetcher)

    result = engine.run(
        SearchRequest(
            keyword='doctor',
            location='Shahjahanpur',
            limit=10,
        )
    )

    assert fetcher.fetched == ['https://example.com/good']
    assert result.count == 1


def test_engine_skips_keyword_match_with_wrong_location():
    fetcher = CombinedRelevanceFetcher()
    engine = make_combined_relevance_engine(fetcher)

    result = engine.run(
        SearchRequest(
            keyword='doctor',
            location='Shahjahanpur',
            limit=10,
        )
    )

    assert 'https://example.com/wrong-location' not in fetcher.fetched
    assert result.count == 1


def test_engine_skips_location_match_without_keyword():
    fetcher = CombinedRelevanceFetcher()
    engine = make_combined_relevance_engine(fetcher)

    result = engine.run(
        SearchRequest(
            keyword='doctor',
            location='Shahjahanpur',
            limit=10,
        )
    )

    assert 'https://example.com/wrong-keyword' not in fetcher.fetched
    assert result.count == 1


class FilterDiscovery:
    def __init__(self, pages):
        self.pages = pages

    def discover(self, request):
        return self.pages

class FilterFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.fetched = []

    def fetch(self, url):
        self.fetched.append(url)
        return self.pages[url]

class FilterParser:
    def parse(self, page, category=""):
        from scraper.models import Lead
        return Lead(
            name=page.url.rsplit("/", 1)[-1],
            location="Shahjahanpur",
            category=category,
            source_url=page.final_url or page.url,
        )

def test_engine_applies_category_filter_before_fetch():
    from scraper.relevance import CategoryRelevance
    pages = [
        DiscoveredPage(url="https://example.com/dentist", title="Dentist Shahjahanpur", snippet="Dental clinic"),
        DiscoveredPage(url="https://example.com/restaurant", title="Restaurant Shahjahanpur", snippet="Food and dining"),
    ]
    fetch_pages = {
        page.url: FetchedPage(url=page.url, final_url=page.url, status_code=200, content_type="text/html", html="<html><body>ok</body></html>")
        for page in pages
    }
    fetcher = FilterFetcher(fetch_pages)
    engine = ScraperEngine(
        discovery=FilterDiscovery(pages),
        fetcher=fetcher,
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        category_relevance=CategoryRelevance("dentist"),
    )
    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))
    assert result.count == 1
    assert fetcher.fetched == ["https://example.com/dentist"]

def test_engine_applies_requirements_filter_before_fetch():
    from scraper.relevance import RequirementsRelevance
    pages = [
        DiscoveredPage(url="https://example.com/qualified", title="Female Dermatologist Shahjahanpur", snippet="Skin specialist"),
        DiscoveredPage(url="https://example.com/unqualified", title="Male General Physician Shahjahanpur", snippet="General medicine"),
    ]
    fetch_pages = {
        page.url: FetchedPage(url=page.url, final_url=page.url, status_code=200, content_type="text/html", html="<html><body>ok</body></html>")
        for page in pages
    }
    fetcher = FilterFetcher(fetch_pages)
    engine = ScraperEngine(
        discovery=FilterDiscovery(pages),
        fetcher=fetcher,
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        requirements_relevance=RequirementsRelevance("female dermatologist"),
    )
    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))
    assert result.count == 1
    assert fetcher.fetched == ["https://example.com/qualified"]

def test_scrape_builds_category_and_requirements_filters_from_request():
    from scraper.engine import scrape
    pages = [
        DiscoveredPage(url="https://example.com/qualified", title="Female Dentist Shahjahanpur", snippet="Dental clinic"),
        DiscoveredPage(url="https://example.com/wrong", title="Male Dentist Shahjahanpur", snippet="Dental clinic"),
        DiscoveredPage(url="https://example.com/restaurant", title="Female Restaurant Shahjahanpur", snippet="Food and dining"),
    ]
    fetch_pages = {
        page.url: FetchedPage(url=page.url, final_url=page.url, status_code=200, content_type="text/html", html="<html><body>ok</body></html>")
        for page in pages
    }
    fetcher = FilterFetcher(fetch_pages)
    result = scrape(
        SearchRequest(keyword="doctor", location="Shahjahanpur", requirements="female dentist", category="dentist"),
        discovery=FilterDiscovery(pages),
        fetcher=fetcher,
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
    )
    assert result.count == 1
    assert fetcher.fetched == ["https://example.com/qualified"]

def test_engine_saves_deduplicated_leads_to_repository():
    repository = FakeRepository()
    engine = ScraperEngine(
        discovery=FakeDiscovery(),
        fetcher=FakeFetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        repository=repository,
    )

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )

    result = engine.run(request)

    assert result.count == 2
    assert len(repository.saved) == 2
    assert {lead.name for lead in repository.saved} == {
        lead.name for lead in result.leads
    }


def test_engine_reads_and_accumulates_real_duckdb_repository(tmp_path):
    from scraper.database.duckdb import DuckDBLeadRepository

    repository = DuckDBLeadRepository(tmp_path / "leads.duckdb")

    class IntegrationDiscovery:
        def __init__(self, pages):
            self.pages = pages

        def discover(self, request):
            return list(self.pages)

    class IntegrationFetcher:
        def __init__(self, pages):
            self.pages = pages

        def fetch(self, url):
            return self.pages[url]

    raj_page = DiscoveredPage(
        url="https://integration.example.com/raj",
        title="Dr Raj Kumar",
        source_name="Integration Directory",
    )
    amit_page = DiscoveredPage(
        url="https://integration.example.com/amit",
        title="Dr Amit Kumar",
        source_name="Integration Directory",
    )

    pages = {
        raj_page.url: FetchedPage(
            url=raj_page.url,
            final_url=raj_page.url,
            status_code=200,
            content_type="text/html",
            html="""<html><head><title>Dr Raj Kumar</title></head>
            <body><p>Dr Raj Kumar</p>
            <p>+91 98765 43210</p>
            <p>raj@example.com</p>
            <address>Main Road, Shahjahanpur, Uttar Pradesh</address>
            </body></html>""",
        ),
        amit_page.url: FetchedPage(
            url=amit_page.url,
            final_url=amit_page.url,
            status_code=200,
            content_type="text/html",
            html="""<html><head><title>Dr Amit Kumar</title></head>
            <body><p>Dr Amit Kumar</p>
            <p>+91 91234 56789</p>
            <p>amit@example.com</p>
            <address>Civil Lines, Shahjahanpur</address>
            </body></html>""",
        ),
    }

    request = SearchRequest(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )

    first_engine = ScraperEngine(
        discovery=IntegrationDiscovery([raj_page]),
        fetcher=IntegrationFetcher(pages),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        repository=repository,
    )

    first_result = first_engine.run(request)

    assert first_result.count == 1
    assert first_result.leads[0].category == "doctor"
    assert first_result.leads[0].location == "Main Road, Shahjahanpur, Uttar Pradesh"
    assert repository.count() == 1
    assert repository.all()[0].name == "Dr Raj Kumar"
    assert repository.all()[0].category == "doctor"
    assert repository.all()[0].location == "Main Road, Shahjahanpur, Uttar Pradesh"

    existing_from_repository = repository.search(
        keyword="doctor",
        location="Shahjahanpur",
        limit=10,
    )

    assert [lead.name for lead in existing_from_repository] == [
        "Dr Raj Kumar",
    ]

    second_engine = ScraperEngine(
        discovery=IntegrationDiscovery([raj_page, amit_page]),
        fetcher=IntegrationFetcher(pages),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        repository=repository,
    )

    second_result = second_engine.run(request)

    assert [lead.name for lead in second_result.existing_leads] == [
        "Dr Raj Kumar",
    ]
    assert second_result.count == 2
    assert repository.count() == 2
    assert {lead.name for lead in repository.all()} == {
        "Dr Raj Kumar",
        "Dr Amit Kumar",
    }

def test_engine_reads_existing_leads_from_repository():
    repository = FakeRepository()

    existing = Lead(
        name='Existing Doctor',
        profession='Doctor',
        city='Shahjahanpur',
        phone='9876543210',
    )

    repository.existing = [existing]

    engine = ScraperEngine(
        discovery=FakeDiscovery(),
        fetcher=FakeFetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        repository=repository,
    )

    request = SearchRequest(
        keyword='doctor',
        location='Shahjahanpur',
        limit=10,
    )

    result = engine.run(request)

    assert repository.search_calls == [
        {
            'keyword': 'doctor',
            'location': 'Shahjahanpur',
            'limit': 10,
        }
    ]
    assert result.existing_leads == [existing]


def test_engine_continues_after_individual_fetch_failure():
    failed_url = "https://example.com/failed"
    first_good_url = "https://example.com/good-1"
    second_good_url = "https://example.com/good-2"

    class MixedDiscovery:
        def discover(self, request):
            return [
                DiscoveredPage(url=failed_url, title="Failed"),
                DiscoveredPage(url=first_good_url, title="First Doctor"),
                DiscoveredPage(url=second_good_url, title="Second Doctor"),
            ]

    class MixedFetcher:
        def __init__(self):
            self.fetched = []

        def fetch(self, url):
            self.fetched.append(url)

            if url == failed_url:
                return FetchedPage(
                    url=url,
                    final_url=url,
                    status_code=500,
                    content_type="text/html",
                    error="HTTP 500",
                )

            name = (
                "First Doctor"
                if url == first_good_url
                else "Second Doctor"
            )

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    f"<html><head><title>{name}</title></head>"
                    f"<body><p>{name}</p>"
                    f"<p>{"+91 98765 43210" if url == first_good_url else "+91 98765 43211"}</p>"
                    f"<p>{name.lower().replace(' ', '.')}@example.com</p>"
                    f"<address>Main Road, Shahjahanpur, Uttar Pradesh</address>"
                    f"</body></html>"
                ),
            )

    fetcher = MixedFetcher()

    result = ScraperEngine(
        discovery=MixedDiscovery(),
        fetcher=fetcher,
        parser=PageParser(),
        normalizer=LeadNormalizer(),
    ).run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=10,
        )
    )

    assert fetcher.fetched == [
        failed_url,
        first_good_url,
        second_good_url,
    ]
    assert len(result.fetched) == 3
    assert len(result.fetch_failures) == 1
    assert result.fetch_failures[0].url == failed_url
    assert result.fetch_failures[0].error == "HTTP 500"
    assert result.count == 2

def test_engine_uses_auto_acquisition_when_fetcher_is_not_supplied(monkeypatch):
    from scraper import engine as engine_module

    url = 'https://example.com/auto'

    class AutoDouble:
        instances = []

        def __init__(self):
            self.calls = []
            self.__class__.instances.append(self)

        def fetch(self, request):
            self.calls.append(request.url)
            return FetchedPage(
                url=request.url,
                final_url=request.url,
                status_code=200,
                content_type='text/html',
                html=(
                    '<html><head><title>Auto Doctor</title></head>'
                    '<body>'
                    '<p>Auto Doctor</p>'
                    '<p>+91 98765 43210</p>'
                    '<p>auto.doctor@example.com</p>'
                    '<address>Main Road, Shahjahanpur, Uttar Pradesh</address>'
                    '</body></html>'
                ),
            )

    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=url,
                    title='Auto Doctor',
                    source_name='Directory',
                )
            ]

    monkeypatch.setattr(engine_module, 'AutoFetcher', AutoDouble)

    result = ScraperEngine(
        discovery=Discovery(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
    ).run(
        SearchRequest(
            keyword='doctor',
            location='Shahjahanpur',
            limit=10,
        )
    )

    assert len(AutoDouble.instances) == 1
    assert AutoDouble.instances[0].calls == [url]
    assert result.count == 1
    assert result.fetch_failures == []


def test_engine_bounds_concurrent_fetches():
    import threading
    import time

    active = 0
    maximum = 0
    lock = threading.Lock()

    class ConcurrentDiscovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=f"https://example.com/page-{index}",
                    title=f"Doctor {index}",
                    source_name="Directory",
                )
                for index in range(8)
            ]

    class ConcurrentFetcher:
        def fetch(self, url):
            nonlocal active, maximum

            with lock:
                active += 1
                maximum = max(maximum, active)

            time.sleep(0.04)

            with lock:
                active -= 1

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><head><title>Doctor</title></head>"
                    "<body><p>Doctor</p>"
                    "<p>+91 98765 43210</p>"
                    "<p>doctor@example.com</p>"
                    "<address>Shahjahanpur</address></body></html>"
                ),
            )

    engine = ScraperEngine(
        discovery=ConcurrentDiscovery(),
        fetcher=ConcurrentFetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        max_concurrency=3,
    )

    result = engine.run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=8,
        )
    )

    assert maximum <= 3
    assert maximum == 3
    assert len(result.fetched) == 8
    assert result.fetch_failures == []


def test_engine_isolates_unexpected_fetch_exceptions():
    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url="https://example.com/crash",
                    title="Crash",
                ),
                DiscoveredPage(
                    url="https://example.com/good",
                    title="Good Doctor",
                ),
            ]

    class Fetcher:
        def fetch(self, url):
            if url.endswith("/crash"):
                raise RuntimeError("connection exploded")

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><head><title>Good Doctor</title></head>"
                    "<body><p>Good Doctor</p>"
                    "<p>+91 98765 43210</p>"
                    "<p>good@example.com</p>"
                    "<address>Shahjahanpur</address></body></html>"
                ),
            )

    result = ScraperEngine(
        discovery=Discovery(),
        fetcher=Fetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        max_concurrency=2,
    ).run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=10,
        )
    )

    assert len(result.fetched) == 2
    assert len(result.fetch_failures) == 1
    assert result.fetch_failures[0].url == "https://example.com/crash"
    assert "connection exploded" in result.fetch_failures[0].error
    assert result.count == 1

def test_engine_uses_concurrency_config_global_limit():
    import threading
    import time

    active = 0
    maximum = 0
    lock = threading.Lock()

    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=f"https://example.com/config-page-{index}",
                    title=f"Doctor {index}",
                )
                for index in range(6)
            ]

    class Fetcher:
        def fetch(self, url):
            nonlocal active, maximum

            with lock:
                active += 1
                maximum = max(maximum, active)

            time.sleep(0.03)

            with lock:
                active -= 1

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><head><title>Doctor</title></head>"
                    "<body><p>Doctor</p>"
                    "<p>+91 98765 43210</p>"
                    "<p>doctor@example.com</p>"
                    "<address>Shahjahanpur</address></body></html>"
                ),
            )

    engine = ScraperEngine(
        discovery=Discovery(),
        fetcher=Fetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        max_concurrency=ConcurrencyConfig(global_limit=2),
    )

    result = engine.run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=6,
        )
    )

    assert maximum <= 2
    assert maximum == 2
    assert len(result.fetched) == 6
    assert result.fetch_failures == []



def test_engine_bounds_concurrent_fetches_per_domain():
    import threading
    import time

    active = 0
    maximum = 0
    lock = threading.Lock()

    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=f"https://example.com/domain-page-{index}",
                    title=f"Doctor {index}",
                )
                for index in range(6)
            ]

    class Fetcher:
        def fetch(self, url):
            nonlocal active, maximum

            with lock:
                active += 1
                maximum = max(maximum, active)

            time.sleep(0.04)

            with lock:
                active -= 1

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><head><title>Doctor</title></head>"
                    "<body><p>Doctor</p>"
                    "<p>+91 98765 43210</p>"
                    "<p>doctor@example.com</p>"
                    "<address>Shahjahanpur</address></body></html>"
                ),
            )

    engine = ScraperEngine(
        discovery=Discovery(),
        fetcher=Fetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        max_concurrency=ConcurrencyConfig(
            global_limit=4,
            per_domain_limit=2,
        ),
    )

    result = engine.run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=6,
        )
    )

    assert maximum <= 2
    assert maximum == 2
    assert len(result.fetched) == 6
    assert result.fetch_failures == []


def test_engine_allows_independent_domains_to_run_concurrently():
    import threading
    import time
    from urllib.parse import urlparse

    active_by_domain = {}
    maximum_by_domain = {}
    lock = threading.Lock()

    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=f"https://one.example/page-{index}",
                    title=f"Doctor One {index}",
                )
                for index in range(2)
            ] + [
                DiscoveredPage(
                    url=f"https://two.example/page-{index}",
                    title=f"Doctor Two {index}",
                )
                for index in range(2)
            ]

    class Fetcher:
        def fetch(self, url):
            domain = urlparse(url).netloc

            with lock:
                active_by_domain[domain] = active_by_domain.get(domain, 0) + 1
                maximum_by_domain[domain] = max(
                    maximum_by_domain.get(domain, 0),
                    active_by_domain[domain],
                )

            time.sleep(0.05)

            with lock:
                active_by_domain[domain] -= 1

            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                html=(
                    "<html><head><title>Doctor</title></head>"
                    "<body><p>Doctor</p>"
                    "<p>+91 98765 43210</p>"
                    "<p>doctor@example.com</p>"
                    "<address>Shahjahanpur</address></body></html>"
                ),
            )

    engine = ScraperEngine(
        discovery=Discovery(),
        fetcher=Fetcher(),
        parser=PageParser(),
        normalizer=LeadNormalizer(),
        max_concurrency=ConcurrencyConfig(
            global_limit=4,
            per_domain_limit=2,
        ),
    )

    result = engine.run(
        SearchRequest(
            keyword="doctor",
            location="Shahjahanpur",
            limit=4,
        )
    )

    assert maximum_by_domain["one.example"] == 2
    assert maximum_by_domain["two.example"] == 2
    assert len(result.fetched) == 4
    assert result.fetch_failures == []


def test_engine_uses_fetch_cache_for_repeated_url(tmp_path):
    from scraper.cache.fetch import FetchCache

    url = "https://example.com/cached"

    class Discovery:
        def discover(self, request):
            return [
                DiscoveredPage(
                    url=url,
                    title="Cached Doctor",
                    source_name="Directory",
                )
            ]

    class Fetcher:
        def __init__(self):
            self.calls = []

        def fetch(self, requested_url):
            self.calls.append(requested_url)
            return FetchedPage(
                url=requested_url,
                final_url=requested_url,
                status_code=200,
                content_type="text/html",
                html="""<html><head><title>Dr Cached Doctor</title></head>
<body><p>Dr Cached Doctor</p>
<p>+91 91234 56789</p>
<p>cached@example.com</p>
<address>Civil Lines, Shahjahanpur</address>
</body></html>""",
            )

    fetcher = Fetcher()

    with FetchCache(tmp_path / "fetch.duckdb") as cache:
        engine = ScraperEngine(
            discovery=Discovery(),
            fetcher=fetcher,
            fetch_cache=cache,
            parser=PageParser(),
            normalizer=LeadNormalizer(),
        )

        first = engine.run(
            SearchRequest(
                keyword="doctor",
                location="Shahjahanpur",
                limit=10,
            )
        )
        second = engine.run(
            SearchRequest(
                keyword="doctor",
                location="Shahjahanpur",
                limit=10,
            )
        )

    assert first.count == 1
    assert second.count == 1
    assert fetcher.calls == [url]


def test_engine_classifies_fetch_failure_categories():
    cases = {
        "request timeout": "timeout",
        "blocked by robots.txt": "policy",
        "per-domain request limit reached": "request-limit",
        "HTTP 401": "auth",
        "HTTP 403": "access-blocked",
        "HTTP 429": "rate-limit",
        "HTTP 500": "server-error",
        "HTTP error: connection reset": "invalid-response",
        "fetch error: connection exploded": "invalid-response",
    }

    for error, expected in cases.items():
        failure = FetchFailure(
            url="https://example.com/test",
            error=error,
        )
        assert ScraperEngine._fetch_failure_category(failure) == expected


def test_engine_persists_fetch_failure_categories(tmp_path):
    metrics_repository = RunMetricsRepository(tmp_path / "metrics.duckdb")

    engine = ScraperEngine(
        discovery=FakeDiscovery(),
        fetcher=FakeFetcher(),
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        run_metrics_repository=metrics_repository,
    )

    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    metrics = metrics_repository.all()

    assert len(metrics) == 1
    assert len(result.fetch_failures) == 1
    assert metrics[0].failure_categories == {"server-error": 1}


def test_engine_persists_discovery_provider_metadata(tmp_path):
    from scraper.discovery import WebDiscovery
    metrics_repository = RunMetricsRepository(tmp_path / "metrics.duckdb")
    provider = MetricsFakeProvider()
    discovery = WebDiscovery(primary_provider=provider)

    engine = ScraperEngine(
        discovery=discovery,
        fetcher=FakeFetcher(),
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        run_metrics_repository=metrics_repository,
    )

    engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    stored = metrics_repository.all()
    assert len(stored) == 1
    assert stored[0].provider == "test_engine.MetricsFakeProvider"
    assert stored[0].provider_config == {}

def test_engine_persists_discovery_cache_metrics(tmp_path):
    from scraper.cache.discovery import DiscoveryCache
    from scraper.discovery import WebDiscovery

    metrics_repository = RunMetricsRepository(tmp_path / "metrics.duckdb")
    discovery = WebDiscovery(
        providers=[MetricsFakeProvider()],
        cache=DiscoveryCache(tmp_path / "discovery.duckdb"),
    )

    engine = ScraperEngine(
        discovery=discovery,
        fetcher=FakeFetcher(),
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        run_metrics_repository=metrics_repository,
    )

    request = SearchRequest(keyword="doctor", location="Shahjahanpur")

    engine.run(request)
    engine.run(request)

    metrics = metrics_repository.all()

    assert len(metrics) == 2
    assert metrics[0].cache_hits == 0
    assert metrics[0].cache_misses == 6
    assert metrics[1].cache_hits == 6
    assert metrics[1].cache_misses == 0

def test_engine_persists_run_metrics(tmp_path):
    metrics_repository = RunMetricsRepository(tmp_path / "metrics.duckdb")

    engine = ScraperEngine(
        discovery=FakeDiscovery(),
        fetcher=FakeFetcher(),
        parser=FilterParser(),
        normalizer=LeadNormalizer(),
        run_metrics_repository=metrics_repository,
    )

    engine.acquisition.cache_hits = 7
    engine.acquisition.cache_misses = 4
    engine.acquisition.browser_fallback_count = 3

    result = engine.run(SearchRequest(keyword="doctor", location="Shahjahanpur"))

    metrics = metrics_repository.all()

    assert len(metrics) == 1
    stored = metrics[0]
    assert stored.run_id
    assert stored.started_at
    assert stored.finished_at
    assert stored.duration_ms is not None
    assert stored.duration_ms >= 0
    assert stored.discovered_count == len(result.discovered)
    assert stored.candidate_count == len(result.discovered)
    assert stored.fetched_count == len(result.fetched)
    assert stored.fetch_failure_count == len(result.fetch_failures)
    assert stored.parse_failure_count == len(result.parse_failures)
    assert stored.lead_count == result.count
    assert stored.existing_lead_count == len(result.existing_leads)
    assert stored.quality_checked_count == result.quality_checked_count
    assert stored.quality_accepted_count == result.quality_accepted_count
    assert stored.quality_rejected_count == result.quality_rejected_count
    assert stored.browser_fallback_count == 3
    assert stored.cache_hits == 7
    assert stored.cache_misses == 4


def test_engine_collects_nested_acquisition_metrics():
    class Inner:
        browser_fallback_count = 3

    class Outer:
        cache_hits = 7
        cache_misses = 4
        acquisition = Inner()

    metrics = ScraperEngine._acquisition_metrics(Outer())

    assert metrics == {
        "browser_fallback_count": 3,
        "cache_hits": 7,
        "cache_misses": 4,
    }
