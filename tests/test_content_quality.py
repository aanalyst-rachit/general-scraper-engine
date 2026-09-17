from scraper.content_quality import ContentQuality, ContentQualityClassifier
from scraper.fetcher import FetchedPage


classifier = ContentQualityClassifier()


def page(html, status_code=200):
    return FetchedPage(
        url="https://example.com/page",
        final_url="https://example.com/page",
        status_code=status_code,
        content_type="text/html",
        html=html,
    )


def test_static_content_is_valid():
    result = classifier.classify(
        page(
            "<html><head><title>Coaching Institute</title></head>"
            "<body><h1>Coaching Institute</h1>"
            "<p>Contact us for admissions and course information.</p>"
            "<p>Phone: +91-9876543210</p></body></html>"
        )
    )

    assert result.category is ContentQuality.VALID_CONTENT
    assert not result.needs_browser_fallback


def test_structured_json_ld_is_valid_even_when_html_is_small():
    result = classifier.classify(
        page(
            '<html><head><script type="application/ld+json">'
            '{"@type":"EducationalOrganization","name":"Amit Coaching Academy"}'
            "</script></head><body><h1>Amit Coaching Academy</h1></body></html>"
        )
    )

    assert result.category is ContentQuality.VALID_CONTENT
    assert not result.needs_browser_fallback


def test_empty_content_needs_browser_fallback():
    result = classifier.classify(
        page("<html><head><title>Loading...</title></head><body></body></html>")
    )

    assert result.category is ContentQuality.EMPTY_CONTENT
    assert result.needs_browser_fallback


def test_js_shell_needs_browser_fallback():
    result = classifier.classify(
        page(
            "<html><head><title>Coaching Institute</title></head>"
            '<body><div id="root"></div><script src="/static/app.js"></script></body></html>'
        )
    )

    assert result.category is ContentQuality.JS_SHELL
    assert result.needs_browser_fallback


def test_http_error_is_not_browser_fallback():
    result = classifier.classify(
        page(
            "<html><body><h1>Internal Server Error</h1></body></html>",
            status_code=500,
        )
    )

    assert result.category is ContentQuality.ERROR_PAGE
    assert not result.needs_browser_fallback


def test_block_page_is_not_browser_fallback():
    result = classifier.classify(
        page(
            "<html><head><title>Access Denied</title></head>"
            "<body><h1>Access Denied</h1><p>Verify you are human.</p></body></html>"
        )
    )

    assert result.category is ContentQuality.BLOCK_PAGE
    assert not result.needs_browser_fallback


def test_short_non_shell_content_is_thin():
    result = classifier.classify(
        page("<html><body><p>Welcome</p></body></html>")
    )

    assert result.category is ContentQuality.THIN_CONTENT
    assert result.needs_browser_fallback


def test_sufficient_body_content_is_valid():
    result = classifier.classify(
        page(
            "<html><body><h1>Coaching Institute</h1>"
            "<p>We provide classroom and online coaching programs "
            "for students preparing for competitive examinations.</p></body></html>"
        )
    )

    assert result.category is ContentQuality.VALID_CONTENT
    assert not result.needs_browser_fallback


def test_normal_page_mentioning_server_error_is_not_error_page():
    result = classifier.classify(
        page(
            "<html><body><h1>Coaching Institute</h1>"
            "<p>Our support team can help with server error troubleshooting "
            "and technical issues.</p>"
            "<p>Call +91-9876543210 for assistance.</p></body></html>"
        )
    )

    assert result.category is ContentQuality.VALID_CONTENT


def test_non_entity_json_ld_is_not_automatically_valid():
    result = classifier.classify(
        page(
            '<html><head><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Thing","name":"Generic Thing"}'
            "</script></head><body></body></html>"
        )
    )

    assert result.category is not ContentQuality.VALID_CONTENT


def test_inline_script_does_not_make_normal_thin_page_js_shell():
    result = classifier.classify(
        page(
            "<html><body><h1>Welcome</h1>"
            "<script>console.log('hello')</script></body></html>"
        )
    )

    assert result.category is ContentQuality.THIN_CONTENT
    assert result.needs_browser_fallback


def test_http_403_is_access_blocked():
    result = classifier.classify(page("<html><body>Access denied</body></html>", status_code=403))

    assert result.category is ContentQuality.ACCESS_BLOCKED
    assert not result.needs_browser_fallback


def test_http_429_is_rate_limited():
    result = classifier.classify(page("<html><body>Too many requests</body></html>", status_code=429))

    assert result.category is ContentQuality.RATE_LIMITED
    assert not result.needs_browser_fallback


def test_http_401_is_auth_required():
    result = classifier.classify(page("<html><body>Authentication required</body></html>", status_code=401))

    assert result.category is ContentQuality.AUTH_REQUIRED
    assert not result.needs_browser_fallback
