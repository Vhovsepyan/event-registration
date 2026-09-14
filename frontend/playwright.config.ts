import { defineConfig } from '@playwright/test'

const databaseUrl =
  process.env.DATABASE_URL ??
  'postgresql+psycopg://event_registration:event_registration@localhost:5433/event_registration'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: 'http://localhost:5173',
    channel: process.env.PLAYWRIGHT_CHANNEL ?? 'msedge',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: '../backend',
      env: { DATABASE_URL: databaseUrl, SSE_POLL_INTERVAL_SECONDS: '0.1' },
      url: 'http://127.0.0.1:8000/health',
      timeout: 30_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      cwd: '.',
      url: 'http://127.0.0.1:5173',
      timeout: 30_000,
      reuseExistingServer: false,
    },
  ],
})
