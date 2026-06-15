# FMCG Innovation Reaction Simulator — dev shortcuts (macOS/Linux).
# Windows users: use scripts\dev.ps1 and the npm/python commands directly.

.PHONY: install backend frontend dev test test-backend test-frontend build backup reset-demo prune-logs

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	bash scripts/dev.sh

test-backend:
	cd backend && python -m pytest -q

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

build:
	cd frontend && npm run build

backup:
	cd backend && python scripts/backup_sqlite.py

reset-demo:
	cd backend && python scripts/reset_demo_data.py

prune-logs:
	cd backend && python scripts/prune_app_logs.py
