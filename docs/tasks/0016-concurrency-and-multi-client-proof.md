# Task 0016 — Concurrency and multi-client proof

## Objective

Provide repeatable evidence that database concurrency invariants hold and that two independent browser clients observe a check-in through the organizer SSE dashboard without refresh.

## Scope

- Preserve and explicitly run the forced-overlap last-seat and one-time check-in tests.
- Add Playwright using an installed browser channel, without bundling a browser binary into the repository.
- Automate event creation, participant registration, ticket check-in, and live organizer statistic propagation across two isolated browser contexts.
- Add a concise manual equivalent and exact prerequisites for repeatable local verification.

## Out of scope

- Load/performance testing, cross-browser matrix testing, hosted CI infrastructure, or changes to concurrency architecture.

## Acceptance criteria

1. The PostgreSQL capacity test genuinely overlaps two transactions and yields one confirmed plus one waitlisted registration.
2. The PostgreSQL check-in test genuinely overlaps two requests and yields exactly one success.
3. The browser test uses two isolated contexts concurrently.
4. A check-in performed in browser B changes browser A's checked-in count from zero to one without reload.
5. The scenario and commands are documented.
6. Full backend/frontend suites and builds remain green.

## Verification

- `uv run pytest tests/registration/test_capacity_waitlist.py tests/ticket/test_check_in.py`
- `npm run test:e2e`
- Full backend lint/migration/test verification
- Full frontend lint/unit/build verification
- Compose and Git whitespace checks
