# Task 0002: React Frontend Foundation

## Objective

Create an independently runnable React and TypeScript frontend using Vite and React Router, with a reliable test/build/lint foundation and no event-registration business functionality.

## Existing work to preserve

- The backend created by task 0001 remains unchanged and independently runnable.
- `frontend/` exists only as a placeholder containing `.gitkeep`.
- Root ignore rules already cover `node_modules/` and `dist/`.

## Scope

- Initialize a Vite React TypeScript application under `frontend/`.
- Add React Router and a top-level application router.
- Provide a neutral application-shell landing route and not-found route.
- Add a typed Vite environment declaration and example API base URL configuration.
- Configure Oxlint for React and TypeScript using the current Vite template defaults.
- Configure Vitest, jsdom, and Testing Library.
- Add focused smoke tests for routing and application-shell rendering.
- Add accessible, responsive baseline styling without implementing product screens.
- Document the frontend commands and the React architecture decision.

## Out of scope

- Event creation or viewing.
- Registration, ticket, check-in, organizer, SSE, and notification UI.
- Backend API calls or business-state management.
- End-to-end browser tests.

## Acceptance criteria

1. `npm install` succeeds from `frontend/` using the committed lockfile.
2. `npm run lint` succeeds.
3. `npm test -- --run` succeeds and verifies the root and not-found routes.
4. `npm run build` produces a production bundle with no TypeScript errors.
5. `npm run dev` starts an independently runnable frontend.
6. React Router owns top-level routing.
7. No task 0003 or later product behavior is implemented.

## Verification

Run from `frontend/`:

```powershell
npm ci
npm run lint
npm test -- --run
npm run build
npm run dev
```
