<#
.SYNOPSIS
    PersonalAI daily launcher.
    Starts Docker Desktop (for web search), ensures the SearXNG container is up,
    checks that Ollama is reachable, then launches the chat UI.

.DESCRIPTION
    Run it from the repo root:   .\start.ps1
    Web search is optional: if Docker isn't installed/available the script still
    starts the UI (notes-only answers keep working).

.PARAMETER NoWeb
    Skip Docker / SearXNG entirely (notes-only session).

.PARAMETER Check
    Run the environment check (scripts/check_env.py) instead of launching the UI.

.PARAMETER Cli
    Start the interactive CLI (scripts/query.py --interactive) instead of the web UI.

.EXAMPLE
    .\start.ps1
.EXAMPLE
    .\start.ps1 -NoWeb
.EXAMPLE
    .\start.ps1 -Check
#>
[CmdletBinding()]
param(
    [switch]$NoWeb,
    [switch]$Check,
    [switch]$Cli
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=== PersonalAI launcher ===" -ForegroundColor Cyan

# --- 1. Locate the virtual-environment Python --------------------------------
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $venvPy = Join-Path $PSScriptRoot ".venv\bin\python.exe"   # non-standard layout
}
if (-not (Test-Path $venvPy)) {
    Write-Error "Virtual environment not found. Create it first:  python -m venv .venv"
    exit 1
}

# --- 2. Start Docker + SearXNG (optional, for web search) --------------------
if (-not $NoWeb) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            $dockerDesktop = Join-Path $Env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
            if (Test-Path $dockerDesktop) {
                Write-Host "Starting Docker Desktop (waiting for the engine)..." -ForegroundColor Yellow
                Start-Process $dockerDesktop | Out-Null
                for ($i = 0; $i -lt 45; $i++) {   # wait up to ~90s
                    Start-Sleep -Seconds 2
                    docker info *> $null
                    if ($LASTEXITCODE -eq 0) { break }
                }
            }
            else {
                Write-Host "Docker Desktop not found - skipping web search." -ForegroundColor DarkYellow
            }
        }

        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Ensuring SearXNG container is up..." -ForegroundColor Yellow
            docker compose -f (Join-Path $PSScriptRoot "searxng\docker-compose.yml") up -d | Out-Null
            Write-Host "SearXNG: running on http://localhost:8888" -ForegroundColor Green
        }
        else {
            Write-Host "Docker engine not ready - continuing without web search." -ForegroundColor DarkYellow
        }
    }
    else {
        Write-Host "Docker not installed - continuing without web search." -ForegroundColor DarkYellow
    }
}

# --- 3. Check Ollama ----------------------------------------------------------
try {
    $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
    Write-Host "Ollama: reachable." -ForegroundColor Green
}
catch {
    Write-Host "Ollama not reachable on 127.0.0.1:11434 - start the Ollama service/app, then retry." -ForegroundColor Red
}

# --- 4. Launch ----------------------------------------------------------------
if ($Check) {
    & $venvPy "scripts\check_env.py"
    exit $LASTEXITCODE
}

if ($Cli) {
    & $venvPy "scripts\query.py" --interactive
    exit $LASTEXITCODE
}

Write-Host "Launching the chat UI at http://localhost:8501 (press Ctrl+C to stop)..." -ForegroundColor Cyan
& $venvPy -m streamlit run "app\streamlit_app.py"
