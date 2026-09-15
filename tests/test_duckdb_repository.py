from __future__ import annotations

import time

from scraper.database.duckdb import DuckDBLeadRepository
from scraper.database.repository import LeadRepository
from scraper.models import Lead


def make_repository(tmp_path):
    return DuckDBLeadRepository(tmp_path / "leads.duckdb")


def test_repository_starts_empty(tmp_path):
    repository = make_repository(tmp_path)

    assert repository.count() == 0
    assert repository.all() == []


def test_save_new_lead(tmp_path):
    repository = make_repository(tmp_path)

    lead = Lead(
        name="ABC Clinic",
        category="doctor",
        location="Shahjahanpur",
        address="Main Road, Shahjahanpur",
        phone="+919876543210",
        website="https://abc.example.com",
        source_url="https://directory.example.com/abc",
        source_name="directory",
    )

    saved = repository.save(lead)

    assert saved.name == "ABC Clinic"
    assert repository.count() == 1

    stored = repository.all()[0]
    assert stored.name == "ABC Clinic"
    assert stored.phone == "+919876543210"
    assert stored.location == "Shahjahanpur"


def test_duplicate_lead_is_not_inserted_twice(tmp_path):
    repository = make_repository(tmp_path)

    first = Lead(
        name="ABC Clinic",
        category="doctor",
        location="Shahjahanpur",
        phone="+91 98765 43210",
        source_url="https://example.com/abc",
    )

    second = Lead(
        name="ABC Clinic",
        category="doctor",
        location="Shahjahanpur",
        phone="+919876543210",
        source_url="https://another-source.example.com/abc",
    )

    repository.save(first)
    repository.save(second)

    assert repository.count() == 1


def test_existing_lead_is_enriched_without_losing_existing_data(tmp_path):
    repository = make_repository(tmp_path)

    first = Lead(
        name="ABC Clinic",
        category="doctor",
        location="Shahjahanpur",
        phone="+919876543210",
        source_url="https://example.com/abc",
    )

    second = Lead(
        name="ABC Clinic",
        category="doctor",
        location="Shahjahanpur",
        phone="+919876543210",
        email="abc@example.com",
        address="Civil Lines, Shahjahanpur",
        website="https://abc-clinic.example.com",
        source_url="https://directory.example.com/abc",
    )

    repository.save(first)
    repository.save(second)

    assert repository.count() == 1

    stored = repository.all()[0]

    assert stored.name == "ABC Clinic"
    assert stored.phone == "+919876543210"
    assert stored.email == "abc@example.com"
    assert stored.address == "Civil Lines, Shahjahanpur"
    assert stored.website == "https://abc-clinic.example.com"


def test_first_seen_is_preserved_and_last_seen_changes(tmp_path):
    repository = make_repository(tmp_path)

    first = Lead(
        name="ABC Clinic",
        location="Shahjahanpur",
        phone="9876543210",
        source_url="https://example.com/abc",
    )

    repository.save(first)

    with repository._connect() as connection:
        first_seen_before = connection.execute(
            "SELECT first_seen_at FROM leads WHERE id = 1"
        ).fetchone()[0]
        last_seen_before = connection.execute(
            "SELECT last_seen_at FROM leads WHERE id = 1"
        ).fetchone()[0]

    time.sleep(0.01)

    repository.save(first)

    with repository._connect() as connection:
        first_seen_after = connection.execute(
            "SELECT first_seen_at FROM leads WHERE id = 1"
        ).fetchone()[0]
        last_seen_after = connection.execute(
            "SELECT last_seen_at FROM leads WHERE id = 1"
        ).fetchone()[0]

    assert first_seen_after == first_seen_before
    assert last_seen_after >= last_seen_before


def test_distinct_leads_are_stored_separately(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="ABC Clinic",
            location="Shahjahanpur",
            phone="9876543210",
            source_url="https://example.com/abc",
        )
    )

    repository.save(
        Lead(
            name="XYZ Hospital",
            location="Shahjahanpur",
            phone="9876543211",
            source_url="https://example.com/xyz",
        )
    )

    assert repository.count() == 2

    names = {lead.name for lead in repository.all()}
    assert names == {"ABC Clinic", "XYZ Hospital"}


def test_extra_data_is_preserved(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="ABC Clinic",
            location="Shahjahanpur",
            phone="9876543210",
            source_url="https://example.com/abc",
            extra={
                "title": "ABC Clinic",
                "source_urls": "https://example.com/abc",
            },
        )
    )

    stored = repository.all()[0]

    assert stored.extra["title"] == "ABC Clinic"
    assert stored.extra["source_urls"] == "https://example.com/abc"



def test_general_lead_fields_are_persisted(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="Dr. ABC",
            profession="Doctor",
            company_name="ABC Healthcare",
            category="healthcare",
            subcategory="clinic",
            designation="Senior Physician",
            specialization="General Medicine",
            services="Consultation, Diagnostics",
            description="General healthcare provider",
            phone="9876543210",
            alternate_phone="9876543211",
            email="abc@example.com",
            alternate_email="contact@example.com",
            website="https://abc.example.com",
            address="Main Road",
            location="Shahjahanpur",
            locality="Civil Lines",
            city="Shahjahanpur",
            district="Shahjahanpur",
            state="Uttar Pradesh",
            country="India",
            pincode="242001",
            social_profiles={
                "linkedin": "https://linkedin.com/in/abc",
                "facebook": "https://facebook.com/abc",
            },
            source_url="https://example.com/abc",
            source_name="example",
            source_id="abc-123",
            search_context="doctor Shahjahanpur",
            extra={
                "rating": "4.8",
                "review_count": "120",
            },
            raw_data={
                "rating": 4.8,
                "review_count": 120,
                "verified": True,
            },
        )
    )

    stored = repository.all()[0]

    assert stored.name == "Dr. ABC"
    assert stored.profession == "Doctor"
    assert stored.company_name == "ABC Healthcare"
    assert stored.category == "healthcare"
    assert stored.subcategory == "clinic"
    assert stored.designation == "Senior Physician"
    assert stored.specialization == "General Medicine"
    assert stored.services == "Consultation, Diagnostics"
    assert stored.description == "General healthcare provider"

    assert stored.phone == "9876543210"
    assert stored.alternate_phone == "9876543211"
    assert stored.email == "abc@example.com"
    assert stored.alternate_email == "contact@example.com"
    assert stored.website == "https://abc.example.com"

    assert stored.address == "Main Road"
    assert stored.location == "Shahjahanpur"
    assert stored.locality == "Civil Lines"
    assert stored.city == "Shahjahanpur"
    assert stored.district == "Shahjahanpur"
    assert stored.state == "Uttar Pradesh"
    assert stored.country == "India"
    assert stored.pincode == "242001"

    assert stored.social_profiles["linkedin"] == "https://linkedin.com/in/abc"
    assert stored.social_profiles["facebook"] == "https://facebook.com/abc"

    assert stored.source_url == "https://example.com/abc"
    assert stored.source_name == "example"
    assert stored.source_id == "abc-123"
    assert stored.search_context == "doctor Shahjahanpur"

    assert stored.extra["rating"] == "4.8"
    assert stored.raw_data["rating"] == 4.8
    assert stored.raw_data["verified"] is True


def test_identity_keys_are_stored_separately(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="ABC Clinic",
            profession="Doctor",
            location="Shahjahanpur",
            phone="9876543210",
            email="abc@example.com",
            source_url="https://example.com/abc",
        )
    )

    with repository._connect() as connection:
        rows = connection.execute(
            """
            SELECT identity_key, lead_id
            FROM lead_identity_keys
            ORDER BY identity_key
            """
        ).fetchall()

    assert rows
    assert all(lead_id == 1 for _, lead_id in rows)

    identity_keys = {key for key, _ in rows}

    assert "phone:9876543210" in identity_keys
    assert "email:abc@example.com" in identity_keys


def test_existing_lead_is_enriched_with_general_fields(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="ABC Clinic",
            profession="Doctor",
            location="Shahjahanpur",
            phone="9876543210",
        )
    )

    repository.save(
        Lead(
            name="ABC Clinic",
            profession="Doctor",
            company_name="ABC Healthcare",
            designation="Senior Physician",
            specialization="Cardiology",
            city="Shahjahanpur",
            district="Shahjahanpur",
            state="Uttar Pradesh",
            email="abc@example.com",
            social_profiles={
                "linkedin": "https://linkedin.com/in/abc",
            },
            raw_data={
                "rating": 4.9,
            },
            phone="9876543210",
        )
    )

    assert repository.count() == 1

    stored = repository.all()[0]

    assert stored.name == "ABC Clinic"
    assert stored.profession == "Doctor"
    assert stored.company_name == "ABC Healthcare"
    assert stored.designation == "Senior Physician"
    assert stored.specialization == "Cardiology"
    assert stored.city == "Shahjahanpur"
    assert stored.district == "Shahjahanpur"
    assert stored.state == "Uttar Pradesh"
    assert stored.email == "abc@example.com"
    assert stored.social_profiles["linkedin"] == "https://linkedin.com/in/abc"
    assert stored.raw_data["rating"] == 4.9


def test_different_general_leads_with_same_name_are_not_merged(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name="ABC",
            profession="Doctor",
            location="Shahjahanpur",
            phone="9876543210",
        )
    )

    repository.save(
        Lead(
            name="ABC",
            profession="CA",
            location="Shahjahanpur",
            phone="9876543211",
        )
    )

    assert repository.count() == 2

    stored = repository.all()

    assert {lead.profession for lead in stored} == {"Doctor", "CA"}

def test_duckdb_repository_implements_lead_repository(tmp_path):
    repository = make_repository(tmp_path)

    assert isinstance(repository, LeadRepository)

def test_search_matches_keyword_and_location(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='Dr. Raj Kumar',
            profession='Doctor',
            company_name='Raj Clinic',
            category='healthcare',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    repository.save(
        Lead(
            name='ABC Restaurant',
            profession='Restaurant Owner',
            category='restaurant',
            city='Shahjahanpur',
            phone='9876543211',
        )
    )

    repository.save(
        Lead(
            name='Dr. Amit Kumar',
            profession='Doctor',
            category='healthcare',
            city='Lucknow',
            phone='9876543212',
        )
    )

    results = repository.search(
        keyword='doctor',
        location='Shahjahanpur',
    )

    assert len(results) == 1
    assert results[0].name == 'Dr. Raj Kumar'


def test_search_keyword_can_match_general_lead_fields(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='ABC Healthcare',
            company_name='ABC Healthcare',
            specialization='Cardiology',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    results = repository.search(
        keyword='cardiology',
        location='Shahjahanpur',
    )

    assert len(results) == 1
    assert results[0].name == 'ABC Healthcare'


def test_search_location_can_match_address_fields(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='ABC Clinic',
            profession='Doctor',
            address='Civil Lines, Shahjahanpur, Uttar Pradesh',
            phone='9876543210',
        )
    )

    results = repository.search(
        keyword='doctor',
        location='Shahjahanpur',
    )

    assert len(results) == 1
    assert results[0].name == 'ABC Clinic'


def test_search_returns_empty_for_no_match(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='ABC Clinic',
            profession='Doctor',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    results = repository.search(
        keyword='dentist',
        location='Shahjahanpur',
    )

    assert results == []


def test_search_respects_limit(tmp_path):
    repository = make_repository(tmp_path)

    for index in range(5):
        repository.save(
            Lead(
                name=f'Doctor {index}',
                profession='Doctor',
                city='Shahjahanpur',
                phone=f'987654321{index}',
            )
        )

    results = repository.search(
        keyword='doctor',
        location='Shahjahanpur',
        limit=2,
    )

    assert len(results) == 2


def test_search_without_filters_returns_leads(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='ABC Clinic',
            profession='Doctor',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    repository.save(
        Lead(
            name='XYZ Restaurant',
            profession='Restaurant Owner',
            city='Lucknow',
            phone='9876543211',
        )
    )

    results = repository.search()

    assert len(results) == 2

def test_search_with_keyword_only(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='Dr. Raj Kumar',
            profession='Doctor',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    repository.save(
        Lead(
            name='Dr. Amit Kumar',
            profession='Doctor',
            city='Lucknow',
            phone='9876543211',
        )
    )

    results = repository.search(keyword='doctor')

    assert len(results) == 2
    assert {lead.name for lead in results} == {
        'Dr. Raj Kumar',
        'Dr. Amit Kumar',
    }


def test_search_with_location_only(tmp_path):
    repository = make_repository(tmp_path)

    repository.save(
        Lead(
            name='Dr. Raj Kumar',
            profession='Doctor',
            city='Shahjahanpur',
            phone='9876543210',
        )
    )

    repository.save(
        Lead(
            name='Dr. Amit Kumar',
            profession='Doctor',
            city='Lucknow',
            phone='9876543211',
        )
    )

    results = repository.search(location='Shahjahanpur')

    assert len(results) == 1
    assert results[0].name == 'Dr. Raj Kumar'
