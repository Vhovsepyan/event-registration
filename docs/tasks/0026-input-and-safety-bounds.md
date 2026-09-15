# Task 0026 — Input and safety bounds

- Status: DONE (2026-09-15, task 0026 commit)
- Created: 2026-09-15
- Source: second external review round (GPT 5.6 ultra finding 4, secondary 2, 3, 6; Copilot Opus 5 finding 3), verified on 2026-09-15

## Problems and evidence

1. `EventCreate.capacity` is only `gt=0`; `capacity: 2147483648` passes validation and overflows PostgreSQL `integer`, producing HTTP 500 (reproduced against the running API).
2. `ck_events_title_not_blank` uses `length(trim(title)) > 0`; `trim` strips spaces only, so a tab-only title is accepted at the database level (the API rejects it via `str.strip()`), reproduced with a direct insert.
3. `tests/conftest.py` runs `Base.metadata.drop_all` against whatever `TEST_DATABASE_URL` points at, checking only that the dialect is PostgreSQL. A misconfigured URL erases a real database.
4. Migration `20260914_0005` downgrade re-adds `CONFIRMED => waitlist_order IS NULL`, but promoted registrations keep their historical `waitlist_order` by design (task 0007), so the downgrade fails on ordinary data.
5. The SQLAlchemy engine uses default pooling (5 + 10 overflow) with no configuration; many concurrent SSE streams plus API traffic can contend for it. (`/health` does not use the database, so the review's "15 tabs takes down /health" claim was not reproduced; the pool limit itself is real.)

## Acceptance criteria

1. Capacity is bounded at the API (`le` = a documented maximum within PostgreSQL `integer`) and returns 422, with a test.
2. The database title constraint rejects titles that are blank after removing spaces, tabs, carriage returns, and newlines; a migration updates the constraint; a test proves a tab-only insert fails.
3. The test fixture refuses to run unless the database name ends with `_test` (or an explicit override variable is set), with a test for the guard.
4. Migration 0005's downgrade either normalises promoted rows explicitly and documents the data loss, or fails fast with a clear message before touching data; verified by a downgrade run with a promoted registration present.
5. Pool size and overflow are configurable through settings with sensible defaults, documented in README alongside the SSE per-client cost.
6. Full verification is green.

## Resolution

- `EventCreate.capacity` is `gt=0, le=MAX_CAPACITY` (1,000,000); 1,000,001, 2,147,483,648 and 10^12 return 422 with a `capacity` error, and the maximum itself is accepted.
- `ck_events_title_not_blank` is now `length(btrim(title, E' \t\r\n')) > 0` in the model and migration `20260914_0012`; tab-only and CR/LF-only titles fail at the database.
- `tests/conftest.py` calls `assert_safe_test_database`, which requires PostgreSQL and a database name ending in `_test` unless `ALLOW_UNSAFE_TEST_DATABASE=1` is set; tested for accepted, refused, non-PostgreSQL, and override cases.
- Migration `20260914_0005` downgrade counts confirmed rows with a historical `waitlist_order` and fails with the explicit normalising statement before touching data; verified against a seeded promoted registration (refused, then succeeded after the documented `UPDATE`).
- `Settings.database_pool_size` (5) and `database_max_overflow` (10) feed `build_engine`; README documents the per-request/per-poll pool cost.
