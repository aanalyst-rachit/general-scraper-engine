# General Scraper Engine — V2 Tracker

## V2 Architecture Decision — Persistent Lead Database
- [x] Use PostgreSQL as the production database
- [x] Use Supabase Free PostgreSQL as the initial database provider
- [x] Target initial deployment cost: ₹0/month
- [x] Keep database access behind a `LeadRepository` abstraction
- [x] Design for later migration to another PostgreSQL provider without changing scraper core
- [x] Use DuckDB as the current persistent local development database
- [x] Keep PostgreSQL/Supabase as the production database target
- [x] Keep repository access behind the LeadRepository abstraction
- [x] Keep SQLite optional for local development/testing only

### V2 Lead Database Model
- [x] Persist discovered leads across searches
- [ ] Show existing matching leads before fresh discovery results
- [x] Append new unique leads to the database
- [x] Enrich existing leads when later crawls provide better fields
- [x] Prevent duplicate leads at database level and application level
- [x] Track first_seen_at and last_seen_at
- [x] Track source URLs/source information

### V2 Repository Architecture
```text
ScraperEngine
      ↓
LeadRepository
      ↓
DuckDBRepository        ← current development
      ↓
PostgreSQLRepository    ← future production
      ↓
Supabase PostgreSQL
```

### V2 Database Fields
- [x] General-purpose Lead identity fields
- [x] Professional / business fields
- [x] Contact fields
- [x] Address/location fields
- [x] Public profile fields
- [x] Source fields
- [x] Flexible extra and raw_data fields
- [x] first_seen_at / last_seen_at persistence
- [x] Separate lead identity-key table
- [ ] Source history / search history as needed

### V2 Current Development Implementation
- [x] Create general-purpose Lead model
- [x] Generalize normalization for all Lead fields
- [x] General-purpose identity-key generation
- [x] Implement DuckDB repository
- [x] Implement repository search by keyword/location
- [x] Implement duplicate detection and lead enrichment
- [x] Add DuckDB repository tests
- [x] Integrate repository reads into ScraperEngine
- [x] Integrate repository writes into ScraperEngine
- [x] Add real DuckDB engine integration test
- [x] Run full regression suite successfully

### V2 Deployment Decision
- [x] Render for application deployment
- [x] Supabase Free PostgreSQL for initial persistent storage
- [ ] Configure production `DATABASE_URL`
- [ ] Add PostgreSQL schema/migrations
- [ ] Add repository tests
- [ ] Verify persistence across application restarts/deployments
- [ ] Reassess database provider when free-tier limits are reached


db design

Lead
├── Identity
│   ├── name
│   ├── profession
│   ├── company_name
│   ├── category
│   └── subcategory
│
├── Professional / Business
│   ├── designation
│   ├── specialization
│   ├── services
│   └── description
│
├── Contact
│   ├── phone
│   ├── alternate_phone
│   ├── email
│   ├── alternate_email
│   └── website
│
├── Address
│   ├── address
│   ├── locality
│   ├── city
│   ├── district
│   ├── state
│   ├── country
│   └── pincode
│
├── Public Profiles
│   └── social / other profiles
│
├── Source
│   ├── source_url
│   ├── source_name
│   ├── source_id
│   └── search_context
│
└── Flexible
    ├── extra
    └── raw_data