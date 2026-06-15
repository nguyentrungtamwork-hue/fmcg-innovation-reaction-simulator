# DEPLOYMENT_CHECKLIST.md

_Practical step-by-step for a shareable demo. This is a local/internal MVP — keep it private.
See `docs/DEPLOYMENT_OPTIONS.md` for the overview and `scripts/check_deploy_config.py` to validate._

Run the config check first:
```bash
cd backend && python scripts/check_deploy_config.py
```

## A. Railway backend + Vercel frontend
1. Push the repo to GitHub.
2. Create a **Railway** project → "Deploy from repo" → service root `backend/` (uses `backend/Dockerfile`).
3. Set backend env vars:
   - `ENVIRONMENT=production`
   - `DEMO_MODE=true` (shows the Demo badge)
   - `FRONTEND_ORIGIN=https://<your-vercel-app>.vercel.app`
   - `DATABASE_URL=sqlite:////data/fmcg_sim.db` + attach a **persistent volume** at `/data` (or use Postgres — see Options doc)
   - `OPENAI_API_KEY=…` (optional; deterministic fallback works without it)
4. Deploy the backend; confirm it boots.
5. Copy the public backend URL (e.g. `https://xxx.up.railway.app`).
6. Create a **Vercel** project → root `frontend/` (framework: Vite).
7. Set `VITE_API_BASE_URL=https://xxx.up.railway.app/api/v1` (Build & Output env).
8. Deploy the frontend; copy its URL.
9. Ensure the Vercel URL is in the backend `FRONTEND_ORIGIN` (re-deploy backend if you set it after).
10. Seed demo data: `railway run python scripts/seed_demo.py --reset-demo` (or create a project + submit brief in the UI).
11. Test `GET https://xxx.up.railway.app/api/v1/system/status` → `{demo_mode:true, environment:"production", …}` (no secrets).
12. Open the frontend, run the full workflow (or open the seeded demo) and the Agent Studio.

## B. Render backend + Cloudflare Pages / Vercel frontend
Same shape as A:
1. Push to GitHub. 2. Render → New Web Service → `backend/` Dockerfile. 3. Set the same env vars + a persistent disk for SQLite. 4. Deploy → copy URL. 5. Cloudflare Pages / Vercel → build `frontend/` with `VITE_API_BASE_URL=https://<render-host>/api/v1`. 6. Add the frontend origin to `FRONTEND_ORIGIN`. 7. Seed + test `/system/status` + full workflow.

## C. VPS Docker (private demo)
1. SSH to the server.
2. Install Docker + Docker Compose.
3. `git clone <repo> && cd <repo>`.
4. (Optional) create a root `.env` with `OPENAI_API_KEY=…`; compose already sets `DEMO_MODE`, `ENVIRONMENT`, `FRONTEND_ORIGIN` defaults.
5. `docker compose up --build -d` → frontend on `:3000`, backend on `:8000`.
6. Put a reverse proxy (nginx/Caddy) with TLS in front; set `FRONTEND_ORIGIN` to the public URL and rebuild the frontend with the matching `VITE_API_BASE_URL`.
7. Seed: `docker compose exec backend python scripts/seed_demo.py --reset-demo`.
8. Back up the `backend_data` volume (the SQLite file) if you want persistence across redeploys.

## Caveats & when to graduate
- **SQLite** is fine for a single-user demo; for concurrent users or ephemeral disks, move to **Postgres** (`DATABASE_URL=postgresql://…`) and add migrations.
- **Background jobs:** add a task queue when simulations get large/slow (currently synchronous).
- **Auth:** add only when exposing beyond a trusted audience (not implemented by design).
- **Keep the demo private:** use an unlisted URL, basic proxy auth at the edge, or a VPN; do not index it.
- **No real data:** the simulator uses no real sales/social data — keep the exploratory-decision-support framing in any shared demo.
