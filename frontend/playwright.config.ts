import { defineConfig, devices } from "@playwright/test";

/**
 * Opt-in E2E smoke (Phase 21). Not part of `npm test` / default CI.
 *
 * Run against an already-running frontend:
 *   1. backend:  cd backend && python -m uvicorn app.main:app --port 8000
 *   2. seed:     cd backend && python scripts/seed_demo.py --reset-demo   (optional)
 *   3. frontend: cd frontend && npm run dev        (or `npm run build && npm run preview`)
 *   4. e2e:      cd frontend && npm run test:e2e
 *
 * Override the target with E2E_BASE_URL (e.g. http://localhost:4173 for `vite preview`).
 */
const baseURL = process.env.E2E_BASE_URL || "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
