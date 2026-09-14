Read `docs/IMPLEMENTATION_PLAN.md` carefully and treat it as the source of truth for this project.

Inspect the current repository first. Some foundation work has already been completed, so preserve correct existing work instead of recreating it.

Work through the implementation plan incrementally in the defined task order.

For each task:

1. Create a detailed specification under `docs/tasks/` if it does not already exist.
2. Add a timestamped entry to `docs/agent/development-log.md`.
3. Implement only that task.
4. Run relevant tests.
5. Diagnose and fix compile, dependency, configuration, migration, runtime, and test failures autonomously.
6. Run the existing full test suite.
7. Self-review the task against its acceptance criteria and the overall implementation plan.
8. Fix all Critical and Important findings.
9. Rerun tests/build after fixes.
10. Commit the completed task with a focused commit message.
11. Continue to the next task only after the current task is green.

Important rules:

- Do not ask me to relay ordinary errors or test failures. Diagnose and fix them yourself.
- Stop only for a genuine external blocker that cannot be solved from the repository or machine environment.
- Do not silently change architecture decisions from `docs/IMPLEMENTATION_PLAN.md`.
- If an architectural change is genuinely necessary, document the reason in `docs/decisions/` before changing it.
- Preserve prompts/decision/development evidence required by the assignment.
- Keep backend and frontend separate applications communicating over the network.
- Do not hide AI-assisted development.
- Do not weaken tests or acceptance criteria to make the project green.
- Maintain incremental commits and timestamps throughout development.

Start by inspecting the existing repository and determine which parts of task 0001 are already complete.

Then proceed autonomously.