# Google Maps OCR Adapter — Implementation Tracker

## Task Identity

- Task name: Google Maps OCR Adapter
- Adapter name: `google-maps-ocr`
- Status: PLANNED
- Scope: This is a completely separate task from the existing `google-maps` and `google-maps-browser` adapters.
- Primary goal: Acquire eligible road/Street View imagery through an appropriate Google-supported imagery/API flow, extract shop-board text using OCR, convert useful board information into validated `Lead` objects, and persist only genuinely new leads.
- Important: Do NOT merge this task into the current Google Maps Browser incremental-fetch task.

## Scope Separation — LOCKED

The following adapters remain conceptually independent:

- `google-maps` — existing Google Maps Places/API adapter.
- `google-maps-browser` — existing Google Maps browser/Playwright adapter.
- `google-maps-ocr` — NEW adapter for imagery-based OCR acquisition.

The OCR adapter may reuse generic infrastructure such as `SearchRequest`, `Lead`, normalization, quality validation, repositories, CLI plumbing, and common utilities where appropriate, but it must have its own adapter implementation and its own tests.

Do NOT add OCR logic directly into `google_maps.py` or `google_maps_browser.py`.

## Core Objective

The adapter should implement this conceptual pipeline:

```text
Road / area / route input
        ↓
Imagery availability / metadata lookup
        ↓
Eligible Street View imagery acquisition
        ↓
Image preprocessing
        ↓
Text detection / OCR
        ↓
Raw OCR text
        ↓
Phone / name / category / address extraction
        ↓
Candidate Lead
        ↓
Location validation
        ↓
Quality validation
        ↓
Normalization
        ↓
Existing DB identity check
        ↓
NEW lead → save
EXISTING lead → skip
````

## Critical Incremental-Collection Rule

The meaning of `--limit` for this adapter must be NEW valid leads, not the number of imagery frames processed and not the number of OCR candidates encountered.

Example:

```text
OCR candidate 1 → existing DB → SKIP
OCR candidate 2 → existing DB → SKIP
OCR candidate 3 → valid + new → SAVE #1
OCR candidate 4 → existing DB → SKIP
OCR candidate 5 → valid + new → SAVE #2
...
continue until 5 NEW valid leads are collected
or the searchable imagery/input is exhausted
```

If `--limit 5` is requested and the first five discovered shops already exist in the persistent database, the adapter must continue searching for additional candidates rather than returning those duplicates.

This is an OCR-adapter requirement and must not be implemented by modifying the existing Google Maps Browser adapter.

## Persistent Database Rule

The OCR adapter must use the existing repository architecture wherever possible.

Expected flow:

```text
Google Maps OCR adapter
        ↓
Lead normalization / quality
        ↓
Persistent LeadRepository
        ↓
Existing database
```

The adapter must not create a fresh isolated database on every run when a persistent database path/repository is configured.

Preferred identity hierarchy:

1. Source place ID, when legitimately available.
2. Normalized phone number.
3. Normalized website.
4. Normalized name + location/address.
5. Geographic proximity combined with normalized business identity where appropriate.

The exact identity strategy must follow the existing repository/normalizer design rather than creating a second incompatible deduplication system.

## Phase 1 — Existing Architecture Audit

* [x] Inspect `SearchRequest` and `Lead` contracts.
* [x] Inspect existing source-adapter interface/protocol.
* [x] Inspect `google_maps.py`.
* [x] Inspect `google_maps_browser.py`.
* [x] Inspect repository implementation and persistence flow.
* [x] Inspect `LeadNormalizer` and existing identity/deduplication behavior.
* [x] Inspect `LeadQuality`.
* [x] Inspect location validation.
* [x] Inspect CLI source registration and argument parsing.
* [x] Inspect existing adapter tests and fixture conventions.
* [x] Confirm exact files that need modification before changing anything.

## Phase 2 — New Adapter Skeleton

* [x] Create `google_maps_ocr.py` in the existing source-adapter location.
* [x] Register source name `google-maps-ocr` without changing existing source names.
* [x] Implement the existing adapter contract.
* [x] Ensure `search(request)` returns the expected `list[Lead]` contract.
* [x] Keep imagery/OCR-specific logic inside the new adapter or dedicated OCR modules.
* [x] Do not copy/paste unrelated browser-adapter logic unnecessarily.

## Phase 3 — Input and Road Sampling

* [ ] Define the supported initial input: location/road/area.
* [ ] Determine how route/path input will be represented without breaking existing CLI behavior.
* [ ] Add bounded sampling of road positions rather than requesting imagery continuously at every meter.
* [ ] Define configurable sampling distance.
* [ ] Check imagery availability/metadata before requesting imagery where supported.
* [ ] Handle unavailable imagery gracefully.
* [ ] Prevent uncontrolled imagery requests.

## Phase 4 — Imagery Acquisition

* [ ] Implement imagery acquisition using an appropriate Google-supported Street View/API mechanism.
* [ ] Do not depend on scraping Google Maps web UI screenshots as the core imagery source.
* [ ] Use metadata/availability checks before imagery acquisition where applicable.
* [ ] Handle API errors, missing imagery, timeouts, and quota-related failures cleanly.
* [ ] Do not implement automatic proxy/IP rotation or anti-bot bypass behavior.
* [ ] Respect applicable Google Maps/Street View API terms, quotas, and imagery usage restrictions.
* [ ] Do not assume unlimited bulk downloading/storage/indexing of Street View imagery is permitted.

## Phase 5 — View / Heading Strategy

* [ ] Determine useful camera headings for each sampling point.
* [ ] Support the road-facing directions needed to observe roadside businesses.
* [ ] Avoid unnecessary duplicate imagery requests.
* [ ] Define configurable heading/FOV/pitch behavior where supported.
* [ ] Keep the design tunable for different road geometries.

## Phase 6 — Image Preprocessing

* [ ] Create an OCR preprocessing pipeline.
* [ ] Support resizing/cropping when beneficial.
* [ ] Improve readability of small shop boards where technically appropriate.
* [ ] Avoid transformations that create misleading OCR results.
* [ ] Keep preprocessing deterministic enough for automated tests.

## Phase 7 — OCR Engine

* [ ] Introduce a replaceable OCR interface.
* [ ] Start with one practical OCR engine.
* [ ] Keep the design open for Tesseract, EasyOCR, PaddleOCR, or another suitable engine.
* [ ] Capture OCR text and confidence information when available.
* [ ] Support Hindi/English or multilingual board text where the selected engine permits it.

## Phase 8 — Board / Text Extraction

* [ ] Detect useful text from OCR output.
* [ ] Extract phone numbers using context-aware rules.
* [ ] Prefer phone-like text near labels such as mobile/contact/tel when available.
* [ ] Avoid treating every arbitrary 10-digit number as a phone number.
* [ ] Extract business/shop names where sufficiently reliable.
* [ ] Extract category/type when board text provides useful evidence.
* [ ] Extract address/location text only when sufficiently reliable.
* [ ] Preserve useful OCR evidence for debugging where permitted.

## Phase 9 — Multiple Frames / Same Shop

A single shop may appear in multiple imagery frames.

Example:

```text
Frame 1 → SHARMA MOBILE
Frame 2 → SHARMA MOB...
Frame 3 → 9876543210
Frame 4 → SHARMA MOBILE + number
                ↓
        ONE business lead
```

* [ ] Group/merge evidence from multiple frames where appropriate.
* [ ] Combine name and phone evidence only when there is sufficient evidence they belong to the same business.
* [ ] Prevent one physical shop from becoming multiple leads merely because it appears in multiple frames.

## Phase 10 — Lead Construction and Validation

* [ ] Convert reliable OCR evidence into the existing `Lead` model.
* [ ] Reuse existing location validation where applicable.
* [ ] Reuse existing `LeadQuality` where applicable.
* [ ] Reuse existing normalization behavior where applicable.
* [ ] Do not create a parallel incompatible Lead schema.
* [ ] Reject obviously unusable OCR fragments such as generic words with no meaningful business/contact evidence.

## Phase 11 — Existing DB Skip and Incremental Search

* [ ] Check persistent database/repository identity before accepting a candidate as new.
* [ ] Existing lead → skip.
* [ ] New valid lead → accept/save.
* [ ] Continue scanning candidates after duplicates.
* [ ] Stop when the requested NEW-lead limit is reached or searchable imagery/input is exhausted.
* [ ] Ensure repeated runs against the same persistent DB discover subsequent new leads.
* [ ] Do not rely only on final-output deduplication; duplicates must be skipped during collection so additional candidates can be discovered.

## Phase 12 — CLI

Initial source:

```text
--source google-maps-ocr
```

Potential OCR-specific options:

```text
--ocr-engine
--ocr-confidence
--sample-distance
--source-timeout
```

Reuse existing options where appropriate:

```text
--limit
--db-path
--save-db
--json
--csv
```

Route-specific options should only be added after the actual supported route/input design is finalized.

## Phase 13 — Testing

* [ ] Add adapter contract tests.
* [ ] Add OCR text extraction tests.
* [ ] Add phone extraction tests.
* [ ] Add Hindi/English OCR parsing fixtures where available.
* [ ] Add multiple-frame merge tests.
* [ ] Add existing-database duplicate tests.
* [ ] Add incremental `--limit` behavior tests.
* [ ] Add imagery-unavailable tests.
* [ ] Add API/timeout/error handling tests.
* [ ] Keep normal unit tests independent of live Google services.
* [ ] Add controlled integration/real-world tests separately.

## Phase 14 — Real-World Validation

* [ ] Select a small controlled road/area.
* [ ] Verify imagery availability.
* [ ] Run OCR on a bounded number of sampling points.
* [ ] Inspect OCR accuracy for visible shop boards.
* [ ] Verify phone extraction.
* [ ] Verify shop-name extraction.
* [ ] Verify duplicate merging across frames.
* [ ] Verify persistent DB insertion.
* [ ] Run the same search again with the same DB.
* [ ] Confirm existing leads are skipped and subsequent new leads are searched.
* [ ] Confirm `--limit N` produces up to N genuinely new valid leads.

## Phase 15 — Documentation

* [ ] Document `google-maps-ocr` in CLI documentation.
* [ ] Document API/configuration prerequisites.
* [ ] Document OCR engine setup.
* [ ] Document sampling behavior.
* [ ] Document incremental/persistent DB behavior.
* [ ] Document known OCR limitations.
* [ ] Document imagery/API usage restrictions and relevant Google requirements.
* [ ] Add usage examples only after implementation is verified.

## Phase 16 — Release Readiness

* [ ] All new adapter tests pass.
* [ ] Existing Google Maps API tests pass.
* [ ] Existing Google Maps Browser tests pass.
* [ ] Full test suite passes.
* [ ] `python -m compileall scraper run_scraper.py` passes.
* [ ] `git diff --check` passes.
* [ ] Documentation build passes when documentation is changed.
* [ ] Real-world validation completed separately from deterministic tests.
* [ ] Release notes/tracker updated only after implementation is actually complete.

## Explicit Non-Goals

* Do NOT modify `google-maps` behavior merely to implement OCR.
* Do NOT modify `google-maps-browser` behavior merely to implement OCR.
* Do NOT merge OCR into the current Google Maps Browser incremental-search implementation.
* Do NOT create a second incompatible Lead model.
* Do NOT use final-output deduplication as a substitute for incremental candidate skipping.
* Do NOT implement blind proxy/IP rotation to bypass anti-bot or access controls.
* Do NOT blindly scrape Google Maps web UI screenshots as the core imagery source.
* Do NOT assume unlimited bulk downloading/storage/indexing of Street View imagery is permitted.
* Do NOT mark a phase complete without actually implementing and testing it.

## Current Progress

### Completed

* [x] Task separated from the existing Google Maps Browser incremental-fetch task.
* [x] New adapter name fixed as `google-maps-ocr`.
* [x] Persistent DB + incremental NEW-lead behavior defined.
* [x] Phase-by-phase implementation roadmap defined.

### In Progress

* [ ] Phase 3 — Input and Road Sampling

### Next Action

* [ ] Define the initial location/road/area input and bounded road-sampling design.

## Important Working Rule

Work incrementally: inspect first, modify one logical file at a time, run the relevant test after each meaningful change, inspect the diff, and only then continue to the next file. Do not perform broad unrelated refactors.
