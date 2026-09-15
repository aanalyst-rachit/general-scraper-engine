from scraper.discovery import DiscoveredPage, SearchRequest
from scraper.engine import ScraperEngine
from scraper.models import Lead
from scraper.fetcher import FetchedPage
from scraper.normalizer import LeadNormalizer
from scraper.parser import PageParser


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
