ChatGPT Astra 6 review

Reviewed commit: `75581e6` (`fix: support cancellation and re-registration`). Review evidence recorded on 2026-09-14 at 17:27:36 +04:00. Tool: OpenAI Codex. Scope: the original assignment, every existing file in `docs/`, README, backend domain and worker code, migrations, React flows, and test coverage.

**Result: no P0 identified; four reproduced P1 issues.** The primary registration/check-in journeys work, but notification behavior does not yet meet the assignment across schedule changes and worker failures. Four OPEN tasks were added to the repository's existing `docs/tasks/` tracker. No application fixes were made in this review.

P0 means a critical, broadly blocking failure requiring immediate intervention. P1 means a reproducible failure of required behavior that should be corrected before submission. Severity below includes the conditions needed to trigger each issue; it does not assume production scale or treat intentionally omitted authentication as a defect.

| Priority | Finding | Open task |
| --- | --- | --- |
| P1 | Reusing a scheduled date silently suppresses a required reschedule email | [0019](../tasks/0019-reschedule-notification-revisions.md) |
| P1 | Queued reminders survive cancellation and postponement | [0020](../tasks/0020-suppress-obsolete-reminders.md) |
| P1 | One permanently failing batch blocks newer email indefinitely | [0021](../tasks/0021-outbox-retry-fairness.md) |
| P1 | Healthy workers resend reminders when a batch outlives its claim | [0022](../tasks/0022-outbox-claim-ownership.md) |

**1. Reschedule identity describes a destination, not an actual change.** In `backend/app/notification/service.py:140`, the key is `event-rescheduled:{event_id}:{registration_id}:{new_value}`. Three real changes A → B → A → B produced only two outbox rows for one active participant. The last PATCH succeeds, but its notification conflicts with the first visit to B and is dropped. This fails the requirement that all active participants receive mail when the organizer moves the event. Use a durable change revision while retaining no-op PATCH idempotency. Task 0014 and decision 0014 currently prescribe the defective key, so they also need correction.

**2. Reminder eligibility is checked at generation but never reconsidered before sending.** `backend/app/notification/service.py:148` selects eligible registrations; `backend/app/notification/worker.py:62` later sends their snapshotted payloads unconditionally. I generated a reminder for an event in 23 hours, postponed it seven days, and ran the worker: the old-date reminder was delivered. A separate cancellation case delivered the reminder containing the now-invalid ticket. These are ordinary sequential actions, with no race required. Add auditable suppression of obsolete intent and coordinate it with concurrent generation. Mail already handed to SMTP remains a separate boundary that cannot be recalled.

**3. Permanent failures can starve all subsequent mail.** `_claim()` selects the oldest pending batch (`backend/app/notification/worker.py:78`); `_mark_failed()` immediately returns failures to the same queue (`:109`). There is no next-attempt date or permanent-failure state. The API accepts an event title with an embedded newline, which the email templates copy into Subject. Python's real `EmailMessage` then raises `Header values may not contain linefeed or carriage return characters`. Twenty such registrations occupy the default batch forever. After three cycles, all twenty had three attempts and a later valid event's confirmation had zero attempts. Introduce fair retries and permanent-failure handling, and validate/render header content safely. Fixing only title validation leaves the general starvation problem and existing bad rows unresolved.

**4. Batch leases expire while the owning worker is still sending.** All batch rows share one initial claim time (`backend/app/notification/worker.py:91`), but delivery is sequential. Under the default batch size 20 and timeout 60 seconds, four-second sends let another worker reclaim the unsent tail. The original worker continues using its detached list. In a PostgreSQL reproduction with two workers and a simulated clock, twenty reminder recipients received twenty-five recording-mailer deliveries. No worker crashed and no send failed. In addition, completion/failure updates check only row ID (`:100`, `:109`), allowing an expired owner to overwrite a newer claim. Use ownership-aware updates and an effective lease strategy. This avoidable overlap is distinct from the README's documented SMTP acceptance/commit crash window.

The complete task files contain the proposed scope and acceptance criteria. They deliberately leave the architecture as a PostgreSQL-backed modular monolith with an asynchronous outbox.

**Other observations, below P1:**

- The initial organizer HTTP snapshot can overwrite a newer SSE snapshot. `frontend/src/pages/OrganizerPage.tsx:18` starts HTTP requests and EventSource concurrently; both callbacks call `setStats`. If HTTP finishes last with older counts, change-only SSE may not repair them until another mutation or reconnect. This is a source-derived P2 race; add a delayed-response component test and prevent older snapshots from replacing newer ones.
- The SSE route's preliminary `get_stats` call opens a transaction on the request dependency (`backend/app/organizer/routes.py:29`). The installed FastAPI implementation retains yield dependencies at request scope by default, so that connection remains checked out until the stream closes even though polling uses separate short sessions. This contradicts task 0010's no-lifetime-transaction criterion and limits connection headroom. The two-client proof passes; higher-client pool exhaustion was not load-tested here. Release the preliminary session before streaming.
- The submission asks for the model and any template/generator provenance. README honestly identifies Codex but says the implementation model is unknown; task 0002 mentions Vite template defaults without a consolidated provenance statement. These are evidence gaps to clarify from actual records, not reasons to invent a model or claim undocumented originality.

| Assignment area | Assessment and evidence |
| --- | --- |
| Separate backend/frontend and relational storage | Implemented: FastAPI, React/TypeScript and PostgreSQL, network HTTP/SSE boundaries, independent processes. |
| Event description, future date/time and capacity | Implemented with API validation and relevant database constraints; clean migration passed. |
| Email registration and duplicate-seat prevention | Implemented with normalization, Event row locks and an active-registration partial unique index. |
| Cancellation and FIFO promotion | Implemented transactionally, with ticket invalidation and promotion notification intent; re-registration preserves history and creates a fresh attempt. |
| Two requests for the last seat | Existing PostgreSQL synchronized-request tests pass; allocation decisions run under the same Event lock. |
| Ticket and one-time check-in | Implemented with random codes and conditional UPDATE; sequential and concurrent tests pass. |
| Organizer counts and two clients | Authoritative aggregate counts and real two-context SSE browser proof pass; see the P2 observations above. |
| Confirmation/promotion email | Intent is transactional and basic retry tests pass; task 0021 can prevent actual delivery globally. |
| Exactly one reminder about 24 hours before | Window selection and outbox dedupe are implemented, but tasks 0020/0022 fail lifecycle/delivery behavior. README correctly states transport is at-least-once, which is still weaker than literal exactly-once receipt. |
| Reschedule email to all participants | Confirmed and waitlisted recipients are intentionally included; cancelled recipients excluded at generation. Task 0019 loses a later valid change. |
| Local setup and external emulation | Documented Compose/PostgreSQL/Mailpit and separate API/worker/frontend commands. Clean database migration and browser startup reverified. |
| AI decisions, chronology, status and next steps | Task, prompt, decision and timestamp logs exist; incremental commits were inspected. README states limitations and next steps. Model/provenance gaps remain as described above. |

No-login behavior is explicitly permitted by the assignment and documented as local-demo scope. It was not classified as P0/P1. Waitlist exclusion from reminders follows the recorded product interpretation. Likewise, cancellation history replacing lifetime email uniqueness is explicitly specified by task 0018 and still enforces one active seat per email.

**Verification performed during this review:**

- Full backend PostgreSQL suite: **46 passed**. One sandbox warning prevented pytest cache creation; test execution completed successfully.
- Frontend Vitest: **11 passed**. TypeScript/Vite build and Oxlint passed.
- Backend Ruff lint and format: passed, 60 files.
- Empty test-database Alembic upgrade: base through `20260914_0007`; `alembic check`: no drift.
- Playwright: **2 passed**, including two-browser live check-in and cancellation/re-registration with old-ticket rejection. The first attempt was blocked by sandbox access to uv's cache; the approved rerun passed against the migrated isolated test database on port 5434.
- Five diagnostic cases against fresh random PostgreSQL schemas: all reproduced the four P1 findings. The script removes only the schemas it creates. The lease test simulates elapsed time and records sends; it is not a real slow-SMTP experiment. The poison case uses real email header construction and blocks network sends.

Run the review diagnostics from `backend/` with the isolated test service running:

```powershell
./.venv/Scripts/python.exe ../docs/reviews/astra6-reproduce.py
```

Observed results:

```text
reschedule_revisit: 3 actual changes, 2 notifications
stale_reminder_after_reschedule: 1 old-date reminder delivered
stale_reminder_after_cancel: 1 reminder delivered after cancellation
poison_starvation: 3 cycles, 20 bad rows retried, healthy row attempts = 0
slow_batch_duplicate: 20 participants, 25 reminder deliveries, 5 duplicates
```

Follow-up 2026-09-14: tasks 0019–0022 were implemented (see their task files and decisions 0019–0022); the script's assertions were updated case by case and all five cases now report the corrected behavior. The original text follows.

[The diagnostic script](astra6-reproduce.py) asserts the observed bugs, not the desired acceptance behavior. Its successful exit confirms reproduction; it does not mean those features are correct. Convert these scenarios to normal regression tests when implementing the tasks. This review did not rerun a clean dependency installation, backend distribution build, real Mailpit delivery, or production/load tests; earlier evidence for those checks remains historical. Existing green suites alone do not cover the failures identified here.
