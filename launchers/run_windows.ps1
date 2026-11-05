# ==============================================================================
# Dead as Disco - BPM & BeatSync Studio Windows Orchestrator
# Bilingual (Spanish/English) 4-step launcher
# ==============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$ReqFile = Join-Path $RepoRoot "requirements.txt"
$HashFile = Join-Path $VenvDir ".requirements.hash"
$AppFile = Join-Path $RepoRoot "app.py"

function Pause-Exit {
    param([int]$Code = 1)
    Write-Host ""
    Write-Host "Presione Enter para salir / Press Enter to exit..." -ForegroundColor Yellow
    try {
        if (-not [Console]::IsInputRedirected -and [Environment]::UserInteractive) {
            $null = [Console]::ReadLine()
        }
    } catch {
        # Fallback in non-standard console environments
    }
    exit $Code
}

# ------------------------------------------------------------------------------
# [1/4] Comprobando requisitos / Checking prerequisites...
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[1/4] Comprobando requisitos / Checking prerequisites..." -ForegroundColor Cyan

$candidates = @(
    @{ Cmd = "py"; Args = @("-3") },
    @{ Cmd = "python3"; Args = @() },
    @{ Cmd = "python"; Args = @() }
)

$selectedCandidate = $null
$foundVersion = $null
$outdatedVersion = $null

foreach ($c in $candidates) {
    if (Get-Command $c.Cmd -ErrorAction SilentlyContinue) {
        try {
            $ver = & $c.Cmd $c.Args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ver) {
                $ver = $ver.Trim()
                & $c.Cmd $c.Args -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $selectedCandidate = $c
                    $foundVersion = $ver
                    break
                } elseif (-not $outdatedVersion) {
                    $outdatedVersion = $ver
                }
            }
        } catch {
            # Continue checking remaining candidates
        }
    }
}

if (-not $selectedCandidate -and (Test-Path $VenvPython)) {
    try {
        $ver = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
            $ver = $ver.Trim()
            & $VenvPython -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $foundVersion = $ver
            }
        }
    } catch {
        # Ignore and proceed to validation check below
    }
}

if (-not $foundVersion) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "  [ERROR] Python 3.10+ no encontrado / Python 3.10+ not found" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
    if ($outdatedVersion) {
        Write-Host "  Se detecto Python $outdatedVersion, pero se requiere version 3.10 o superior." -ForegroundColor Yellow
        Write-Host "  Detected Python $outdatedVersion, but version 3.10 or higher is required." -ForegroundColor Yellow
    } else {
        Write-Host "  No se detecto ninguna instalacion valida de Python 3.10+ en el sistema." -ForegroundColor Yellow
        Write-Host "  No valid Python 3.10+ installation was detected on your system." -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  Descargue e instale Python 3.10 o superior desde / Please download and install from:" -ForegroundColor White
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  IMPORTANTE: Durante la instalacion, active la casilla 'Add python.exe to PATH'." -ForegroundColor Yellow
    Write-Host "  IMPORTANT: During setup, make sure to check 'Add python.exe to PATH'." -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Red
    Pause-Exit 1
}

Write-Host "      Requisitos / Requirements: Python $foundVersion compatible detectado / detected." -ForegroundColor Green

# ------------------------------------------------------------------------------
# [2/4] Configurando entorno virtual / Setting up virtual environment...
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Configurando entorno virtual / Setting up virtual environment..." -ForegroundColor Cyan

if (-not (Test-Path $VenvPython)) {
    Write-Host "      Creando entorno virtual en .venv / Creating virtual environment in .venv..." -ForegroundColor Gray
    try {
        if ($selectedCandidate) {
            & $selectedCandidate.Cmd $selectedCandidate.Args -m venv $VenvDir
        } else {
            & python -m venv $VenvDir
        }
    } catch {
        # Catch command invocation exceptions
    }

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Write-Host ""
        Write-Host "[ERROR] No se pudo crear el entorno virtual / Failed to create virtual environment (.venv)." -ForegroundColor Red
        Write-Host "Verifique los permisos de escritura en la carpeta / Check directory write permissions." -ForegroundColor Yellow
        Pause-Exit 2
    }
    Write-Host "      Entorno virtual .venv creado exitosamente / Virtual environment created successfully." -ForegroundColor Green
} else {
    Write-Host "      Entorno Virtual / Virtual Environment: .venv listo / ready." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# [3/4] Instalando dependencias / Installing dependencies...
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Instalando dependencias / Installing dependencies..." -ForegroundColor Cyan

if (-not (Test-Path $ReqFile)) {
    Write-Host "      [ADVERTENCIA] No se encontro requirements.txt / requirements.txt not found." -ForegroundColor Yellow
} else {
    $currentHash = (Get-FileHash -Path $ReqFile -Algorithm SHA256).Hash.ToLower()
    $savedHash = ""
    if (Test-Path $HashFile) {
        $savedHash = (Get-Content -Path $HashFile -Raw -ErrorAction SilentlyContinue)
        if ($savedHash) { $savedHash = $savedHash.Trim().ToLower() }
    }

    if ($savedHash -eq $currentHash) {
        Write-Host "      Dependencias / Dependencies: Dependencias al dia (Cache valida) / Dependencies up to date (Cache hit)." -ForegroundColor Green
    } else {
        Write-Host "      Instalando o actualizando dependencias / Installing or updating dependencies..." -ForegroundColor Gray
        & $VenvPython -m pip install --disable-pip-version-check -r $ReqFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "[ERROR] Fallo la instalacion de dependencias con pip / pip install failed." -ForegroundColor Red
            Pause-Exit 3
        }
        Set-Content -Path $HashFile -Value $currentHash -Encoding utf8 -NoNewline
        Write-Host "      Dependencias / Dependencies: Sincronizadas exitosamente / Dependencies synced successfully." -ForegroundColor Green
    }
}

# ------------------------------------------------------------------------------
# [4/4] Iniciando DaD BPM Studio / Starting DaD BPM Studio...
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Iniciando DaD BPM Studio / Starting DaD BPM Studio..." -ForegroundColor Cyan
Write-Host "      Iniciando App / Starting Studio: Abriendo interfaz en navegador / Opening studio interface..." -ForegroundColor Green
Write-Host "      URL: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

& $VenvPython -m streamlit run $AppFile $args
$appExitCode = $LASTEXITCODE

if ($appExitCode -ne 0) {
    Write-Host ""
    Write-Host "[!] La aplicacion se cerro con codigo / Studio exited with code: $appExitCode" -ForegroundColor Yellow
    Pause-Exit $appExitCode
}

exit 0
