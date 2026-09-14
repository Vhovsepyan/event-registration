# Task 0024 prompt evidence

Source: the user's instruction on 2026-09-14 to also fix the two remaining P2 observations from the ChatGPT Astra 6 review, create tasks for them, add them to `docs/IMPLEMENTATION_PLAN.md`, and follow the established task rules; executed with Claude Code (Claude Opus 5).

Release the SSE route's preliminary session before streaming so no pooled PostgreSQL connection is pinned for the stream lifetime, keep the 404 pre-check and per-snapshot short-lived sessions, and prove pool release against PostgreSQL.
