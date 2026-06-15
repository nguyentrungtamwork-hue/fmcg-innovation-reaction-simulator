# Phase 9 — one-command local dev (Windows PowerShell).
# Starts the FastAPI backend (:8000) and the Vite frontend (:5173) in two windows.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
#
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\backend'; python -m uvicorn app.main:app --reload --port 8000"
)

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\frontend'; if (-not (Test-Path node_modules)) { npm install }; npm run dev"
)

Write-Host "Both processes launched. Open http://localhost:5173" -ForegroundColor Green
