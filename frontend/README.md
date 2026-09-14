# Event Registration Frontend

Independent React and TypeScript application built with Vite.

## Commands

```powershell
npm install
npm run dev
npm run lint
npm test -- --run
npm run build
```

By default the application calls `http://localhost:8000`. Copy `.env.example` to `.env` and change `VITE_API_BASE_URL` when the API is hosted elsewhere.

The product routes cover event creation, participant registration, ticket display, staff check-in, and a live organizer dashboard. The dashboard uses native Server-Sent Events and requires the backend to be running.
