from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from scraper.models import Lead
from scraper.normalizer import LeadNormalizer


class DuckDBLeadRepository:
    def __init__(
        self,
        database_path: str | Path = "data/leads.duckdb",
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.normalizer = LeadNormalizer()
        self._initialize()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.database_path))

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR,
                    profession VARCHAR,
                    company_name VARCHAR,
                    category VARCHAR,
                    subcategory VARCHAR,
                    designation VARCHAR,
                    specialization VARCHAR,
                    services VARCHAR,
                    description VARCHAR,
                    phone VARCHAR,
                    alternate_phone VARCHAR,
                    email VARCHAR,
                    alternate_email VARCHAR,
                    website VARCHAR,
                    address VARCHAR,
                    location VARCHAR,
                    locality VARCHAR,
                    city VARCHAR,
                    district VARCHAR,
                    state VARCHAR,
                    country VARCHAR,
                    pincode VARCHAR,
                    social_profiles JSON,
                    source_url VARCHAR,
                    source_name VARCHAR,
                    source_id VARCHAR,
                    search_context VARCHAR,
                    first_seen_at TIMESTAMP NOT NULL,
                    last_seen_at TIMESTAMP NOT NULL,
                    extra JSON,
                    raw_data JSON
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS lead_identity_keys (
                    identity_key VARCHAR PRIMARY KEY,
                    lead_id BIGINT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                )
                """
            )

    def save(self, lead: Lead) -> Lead:
        lead = self.normalizer.normalize_lead(lead)
        keys = self.normalizer.lead_identity_keys(lead)
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        with self._connect() as connection:
            lead_id = self._find_existing_id(connection, keys)

            if lead_id is None:
                lead_id = self._next_id(connection)

                connection.execute(
                    """
                    INSERT INTO leads (
                        id,
                        name,
                        profession,
                        company_name,
                        category,
                        subcategory,
                        designation,
                        specialization,
                        services,
                        description,
                        phone,
                        alternate_phone,
                        email,
                        alternate_email,
                        website,
                        address,
                        location,
                        locality,
                        city,
                        district,
                        state,
                        country,
                        pincode,
                        social_profiles,
                        source_url,
                        source_name,
                        source_id,
                        search_context,
                        first_seen_at,
                        last_seen_at,
                        extra,
                        raw_data
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                    """,
                    self._lead_values(
                        lead_id,
                        lead,
                        now,
                        now,
                    ),
                )

                self._store_identity_keys(
                    connection,
                    lead_id,
                    keys,
                    now,
                )

                return lead

            existing_row = self._fetch_lead_row(
                connection,
                lead_id,
            )
            existing = self._row_to_lead(existing_row)

            merged = self.normalizer.merge_leads(
                existing,
                lead,
            )

            connection.execute(
                """
                UPDATE leads
                SET
                    name = ?,
                    profession = ?,
                    company_name = ?,
                    category = ?,
                    subcategory = ?,
                    designation = ?,
                    specialization = ?,
                    services = ?,
                    description = ?,
                    phone = ?,
                    alternate_phone = ?,
                    email = ?,
                    alternate_email = ?,
                    website = ?,
                    address = ?,
                    location = ?,
                    locality = ?,
                    city = ?,
                    district = ?,
                    state = ?,
                    country = ?,
                    pincode = ?,
                    social_profiles = ?,
                    source_url = ?,
                    source_name = ?,
                    source_id = ?,
                    search_context = ?,
                    last_seen_at = ?,
                    extra = ?,
                    raw_data = ?
                WHERE id = ?
                """,
                [
                    merged.name,
                    merged.profession,
                    merged.company_name,
                    merged.category,
                    merged.subcategory,
                    merged.designation,
                    merged.specialization,
                    merged.services,
                    merged.description,
                    merged.phone,
                    merged.alternate_phone,
                    merged.email,
                    merged.alternate_email,
                    merged.website,
                    merged.address,
                    merged.location,
                    merged.locality,
                    merged.city,
                    merged.district,
                    merged.state,
                    merged.country,
                    merged.pincode,
                    json.dumps(merged.social_profiles),
                    merged.source_url,
                    merged.source_name,
                    merged.source_id,
                    merged.search_context,
                    now,
                    json.dumps(merged.extra),
                    json.dumps(merged.raw_data),
                    lead_id,
                ],
            )

            merged_keys = self.normalizer.lead_identity_keys(merged)

            self._store_identity_keys(
                connection,
                lead_id,
                merged_keys,
                now,
            )

            return merged

    def _lead_values(
        self,
        lead_id: int,
        lead: Lead,
        first_seen_at: datetime,
        last_seen_at: datetime,
    ) -> list[object]:
        return [
            lead_id,
            lead.name,
            lead.profession,
            lead.company_name,
            lead.category,
            lead.subcategory,
            lead.designation,
            lead.specialization,
            lead.services,
            lead.description,
            lead.phone,
            lead.alternate_phone,
            lead.email,
            lead.alternate_email,
            lead.website,
            lead.address,
            lead.location,
            lead.locality,
            lead.city,
            lead.district,
            lead.state,
            lead.country,
            lead.pincode,
            json.dumps(lead.social_profiles),
            lead.source_url,
            lead.source_name,
            lead.source_id,
            lead.search_context,
            first_seen_at,
            last_seen_at,
            json.dumps(lead.extra),
            json.dumps(lead.raw_data),
        ]

    def _next_id(
        self,
        connection: duckdb.DuckDBPyConnection,
    ) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM leads"
        ).fetchone()

        return int(row[0])

    def _find_existing_id(
        self,
        connection: duckdb.DuckDBPyConnection,
        keys: list[str],
    ) -> int | None:
        if not keys:
            return None

        row = connection.execute(
            """
            SELECT lead_id
            FROM lead_identity_keys
            WHERE identity_key IN (
                SELECT * FROM UNNEST(?)
            )
            ORDER BY lead_id
            LIMIT 1
            """,
            [keys],
        ).fetchone()

        if row is None:
            return None

        return int(row[0])

    def _store_identity_keys(
        self,
        connection: duckdb.DuckDBPyConnection,
        lead_id: int,
        keys: list[str],
        created_at: datetime,
    ) -> None:
        for key in keys:
            try:
                connection.execute(
                    """
                    INSERT INTO lead_identity_keys (
                        identity_key,
                        lead_id,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT (identity_key) DO NOTHING
                    """,
                    [
                        key,
                        lead_id,
                        created_at,
                    ],
                )
            except duckdb.ConstraintException:
                # An identity key already belongs to another lead.
                # Never steal another lead's identity key.
                continue

    def _fetch_lead_row(
        self,
        connection: duckdb.DuckDBPyConnection,
        lead_id: int,
    ):
        row = connection.execute(
            """
            SELECT *
            FROM leads
            WHERE id = ?
            """,
            [lead_id],
        ).fetchone()

        if row is None:
            raise RuntimeError(
                f"Lead {lead_id} disappeared during repository operation"
            )

        return row

    def _row_to_lead(self, row) -> Lead:
        social_profiles = self._json_dict(row[23])
        extra = self._json_dict(row[30])
        raw_data = self._json_dict(row[31])

        return Lead(
            name=row[1] or "",
            profession=row[2] or "",
            company_name=row[3] or "",
            category=row[4] or "",
            subcategory=row[5] or "",
            designation=row[6] or "",
            specialization=row[7] or "",
            services=row[8] or "",
            description=row[9] or "",
            phone=row[10] or "",
            alternate_phone=row[11] or "",
            email=row[12] or "",
            alternate_email=row[13] or "",
            website=row[14] or "",
            address=row[15] or "",
            location=row[16] or "",
            locality=row[17] or "",
            city=row[18] or "",
            district=row[19] or "",
            state=row[20] or "",
            country=row[21] or "",
            pincode=row[22] or "",
            social_profiles=social_profiles,
            source_url=row[24] or "",
            source_name=row[25] or "",
            source_id=row[26] or "",
            search_context=row[27] or "",
            extra=extra,
            raw_data=raw_data,
        )

    def _json_dict(self, value) -> dict:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                return {}

        return value if isinstance(value, dict) else {}

    def search(
        self,
        keyword: str = "",
        location: str = "",
        limit: int = 50,
    ) -> list[Lead]:
        keyword = keyword.strip()
        location = location.strip()

        if limit <= 0:
            return []

        keyword_columns = [
            "name",
            "profession",
            "company_name",
            "category",
            "subcategory",
            "designation",
            "specialization",
            "services",
            "description",
        ]

        location_columns = [
            "address",
            "location",
            "locality",
            "city",
            "district",
            "state",
            "country",
            "pincode",
        ]

        conditions: list[str] = []
        parameters: list[object] = []

        if keyword:
            keyword_conditions = [
                f"LOWER(COALESCE({column}, '')) LIKE LOWER(?)"
                for column in keyword_columns
            ]
            conditions.append("(" + " OR ".join(keyword_conditions) + ")")
            keyword_pattern = f"%{keyword}%"
            parameters.extend([keyword_pattern] * len(keyword_columns))

        if location:
            location_conditions = [
                f"LOWER(COALESCE({column}, '')) LIKE LOWER(?)"
                for column in location_columns
            ]
            conditions.append("(" + " OR ".join(location_conditions) + ")")
            location_pattern = f"%{location}%"
            parameters.extend([location_pattern] * len(location_columns))

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT *
            FROM leads
            {where_clause}
            ORDER BY id ASC
            LIMIT ?
        """

        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return [self._row_to_lead(row) for row in rows]

    def count(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM leads"
                ).fetchone()[0]
            )

    def all(self) -> list[Lead]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM leads ORDER BY id"
            ).fetchall()

        return [self._row_to_lead(row) for row in rows]

    def close(self) -> None:
        return None
