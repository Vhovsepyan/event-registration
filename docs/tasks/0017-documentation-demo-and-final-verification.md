# Task 0017 — Documentation, decision log, demo, and final verification

## Objective

Finish the developer/operator handoff and execute the implementation plan's complete proof from infrastructure and empty-schema migration through tests, runtime, email, and the two-browser scenario.

## Scope

- Replace foundation-era README text with exact local setup, run, test, worker, email, and browser-proof commands.
- Add a coherent product demo script.
- Audit required architecture decisions, prompt evidence, task specifications, and the development log.
- Recreate the ephemeral test PostgreSQL service and migrate its empty database from Alembic base to head.
- Verify backend/frontend startup and health/content over HTTP.
- Deliver a real notification through the worker into Mailpit and inspect it through Mailpit's API/UI.
- Run the complete backend, frontend, concurrency, reminder, migration, build, Compose, and Playwright proof matrix.

## Out of scope

- New product features, deployment infrastructure, authentication, or architecture changes.

## Acceptance criteria

1. README commands are complete, ordered, and match the repository.
2. A new developer can start PostgreSQL, Mailpit, backend, worker, and frontend as independent processes.
3. The decision log contains every minimum decision required by the plan.
4. Migrations succeed against a newly recreated empty PostgreSQL test service and reach head.
5. Backend and frontend start and respond.
6. A real registration email reaches Mailpit.
7. All automated suites, focused invariant tests, builds, and the two-client browser proof pass.
8. Repository evidence is timestamped and the working tree is clean after the focused task commit.

## Verification

See `docs/demo/final-verification.md` for the exact commands and recorded outcome.
