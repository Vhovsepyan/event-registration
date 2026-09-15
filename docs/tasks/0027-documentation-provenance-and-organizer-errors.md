# Task 0027 — Documentation, provenance, and organizer error isolation

- Status: DONE (2026-09-15, task 0027 commit)
- Created: 2026-09-15
- Source: second external review round (GPT 5.6 ultra findings 3, 5, 6, 7 and secondary 4), verified on 2026-09-15

## Problems and evidence

1. README's "Tests and quality checks" starts only `postgres-test` on 5434, then runs `uv run alembic check`, which reads `DATABASE_URL` (default port 5432). The documented sequence fails on a machine without the development database running.
2. Locked `vitest@5.0.0` requires Node `^22.12 || ^24`; README says only "Node.js" and `frontend/package.json` declares no `engines`. Node 18 fails at startup.
3. README's AI-assisted development section names only OpenAI Codex and says no model identifier is evidenced, while the development log records Claude Code (Claude Opus 5) for tasks 0019–0024. The two must agree.
4. Reviewers of a zip archive cannot see the incremental history; README should state the repository URL where the commit history lives.
5. `OrganizerPage` loads event details and statistics with `Promise.all`; one failed request discards the other's successful response.

## Acceptance criteria

1. The documented test recipe runs as written from a clean shell with only the test service started (the migration/drift check is pointed at the test database or moved under the development-database section).
2. `frontend/package.json` declares `engines.node` matching the locked toolchain and README states the minimum Node version.
3. README's provenance section accurately attributes tasks 0001–0018 to OpenAI Codex and tasks 0019 onward to Claude Code (Claude Opus 5), consistent with the development log, and links the repository.
4. The organizer page renders whichever of event details or statistics succeeded and reports the failed one; a component test proves it.
5. Frontend lint/tests/build and the browser proof remain green.

## Resolution

- README's test section sets `DATABASE_URL` to the test service before `alembic upgrade head` and `alembic check`; the test fixture now also drops `alembic_version`, so the migration checks and the suite work in either order (verified: suite, then 12 upgrades from base and a clean drift check).
- `frontend/package.json` declares `engines.node: ">=22.12.0"`; README prerequisites state Node 22.12+ (24 LTS recommended).
- README's AI-assisted development section attributes tasks 0001-0018 and the Astra 6 review to OpenAI Codex and tasks 0019-0027 to Claude Code with Claude Opus 5, matching the development log, and links the GitHub repository for the commit history.
- `OrganizerPage` issues the event and statistics requests independently; a failure in one surfaces as the error alert while the other still renders. Two component tests cover both directions.
