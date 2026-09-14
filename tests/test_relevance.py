from scraper.discovery import DiscoveredPage
from scraper.relevance import KeywordRelevance, LocationRelevance


def test_keyword_relevance_scores_title_match():
    scorer = KeywordRelevance("doctor")
    page = DiscoveredPage(
        url="https://example.com/profile", 
        title="Dr Raj Kumar - Doctor", 
    )

    assert scorer.score(page) == 3
    assert scorer.is_relevant(page)


def test_keyword_relevance_scores_snippet_match():
    scorer = KeywordRelevance("doctor")
    page = DiscoveredPage(
        url="https://example.com/profile", 
        title="Raj Kumar", 
        snippet="Experienced doctor in Shahjahanpur", 
    )

    assert scorer.score(page) == 2
    assert scorer.is_relevant(page)


def test_keyword_relevance_scores_url_match():
    scorer = KeywordRelevance("doctor")
    page = DiscoveredPage(
        url="https://example.com/doctors/raj-kumar", 
        title="Raj Kumar", 
    )

    assert scorer.score(page) == 1
    assert scorer.is_relevant(page)


def test_keyword_relevance_rejects_irrelevant_page():
    scorer = KeywordRelevance("doctor")
    page = DiscoveredPage(
        url="https://example.com/weather", 
        title="Shahjahanpur Weather Today", 
        snippet="Latest weather forecast", 
    )

    assert scorer.score(page) == 0
    assert not scorer.is_relevant(page)


def test_keyword_relevance_is_case_insensitive():
    scorer = KeywordRelevance("Doctor")
    page = DiscoveredPage(
        url="https://example.com/DOCTOR/raj", 
        title="GENERAL DOCTOR", 
    )

    assert scorer.is_relevant(page)


def test_keyword_relevance_supports_multi_word_keyword():
    scorer = KeywordRelevance("general physician")
    page = DiscoveredPage(
        url="https://example.com/profile", 
        title="General Physician Raj Kumar", 
    )

    assert scorer.score(page) == 3
    assert scorer.is_relevant(page)


def test_keyword_relevance_rejects_empty_keyword():
    try:
        KeywordRelevance("")
    except ValueError as exc:
        assert str(exc) == "keyword must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_keyword_relevance_matches_plural_form():
    scorer = KeywordRelevance("doctor")
    page = DiscoveredPage(
        url="https://example.com/doctors/raj-kumar",
        title="Raj Kumar",
    )

    assert scorer.score(page) == 1
    assert scorer.is_relevant(page)

def test_location_relevance_scores_title_match():
    scorer = LocationRelevance("Shahjahanpur")
    page = DiscoveredPage(
        url="https://example.com/profile",
        title="Doctor Shahjahanpur",
    )

    assert scorer.score(page) == 3
    assert scorer.is_relevant(page)


def test_location_relevance_scores_snippet_match():
    scorer = LocationRelevance("Shahjahanpur")
    page = DiscoveredPage(
        url="https://example.com/profile",
        title="Dr Raj Kumar",
        snippet="Doctor in Shahjahanpur",
    )

    assert scorer.score(page) == 2
    assert scorer.is_relevant(page)


def test_location_relevance_scores_url_match():
    scorer = LocationRelevance("Shahjahanpur")
    page = DiscoveredPage(
        url="https://example.com/shahjahanpur/doctor",
        title="Dr Raj Kumar",
    )

    assert scorer.score(page) == 1
    assert scorer.is_relevant(page)


def test_location_relevance_rejects_wrong_location():
    scorer = LocationRelevance("Shahjahanpur")
    page = DiscoveredPage(
        url="https://example.com/lucknow/doctor",
        title="Doctor in Lucknow",
        snippet="Best doctor in Lucknow",
    )

    assert scorer.score(page) == 0
    assert not scorer.is_relevant(page)


def test_location_relevance_is_case_insensitive():
    scorer = LocationRelevance("Shahjahanpur")
    page = DiscoveredPage(
        url="https://example.com/profile",
        title="SHAHJAHANPUR Doctor",
    )

    assert scorer.is_relevant(page)


def test_location_relevance_rejects_empty_location():
    try:
        LocationRelevance("")
    except ValueError as exc:
        assert str(exc) == "location must not be empty"
    else:
        raise AssertionError("expected ValueError")



def test_category_relevance_matches_title():
    from scraper.discovery import DiscoveredPage
    from scraper.relevance import CategoryRelevance

    relevance = CategoryRelevance("dentist")
    page = DiscoveredPage(url="https://example.com", title="Best Dentist in City")
    assert relevance.is_relevant(page)


def test_category_relevance_rejects_wrong_category():
    from scraper.discovery import DiscoveredPage
    from scraper.relevance import CategoryRelevance

    relevance = CategoryRelevance("dentist")
    page = DiscoveredPage(url="https://example.com", title="Best Restaurant in City")
    assert not relevance.is_relevant(page)


def test_category_relevance_empty_category_rejected():
    from scraper.relevance import CategoryRelevance

    import pytest

    with pytest.raises(ValueError, match="category must not be empty"):
        CategoryRelevance(" ")


def test_requirements_relevance_requires_all_terms():
    from scraper.discovery import DiscoveredPage
    from scraper.relevance import RequirementsRelevance

    relevance = RequirementsRelevance("female dermatologist")
    matching = DiscoveredPage(
        url="https://example.com/female-dermatologist",
        title="Female Dermatologist",
    )
    partial = DiscoveredPage(
        url="https://example.com/dermatologist",
        title="Dermatologist",
    )

    assert relevance.is_relevant(matching)
    assert not relevance.is_relevant(partial)


def test_requirements_relevance_is_case_insensitive():
    from scraper.discovery import DiscoveredPage
    from scraper.relevance import RequirementsRelevance

    relevance = RequirementsRelevance("Open 24 Hours")
    page = DiscoveredPage(
        url="https://example.com",
        title="OPEN 24 HOURS clinic",
    )

    assert relevance.is_relevant(page)


def test_requirements_relevance_empty_requirements_rejected():
    from scraper.relevance import RequirementsRelevance

    import pytest

    with pytest.raises(ValueError, match="requirements must not be empty"):
        RequirementsRelevance(" ")
