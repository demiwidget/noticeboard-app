param(
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$AppPath = Join-Path $ProjectDir "pc_app\main.py"

if (-not (Test-Path $AppPath)) {
    throw "Could not find the PC app at: $AppPath"
}

Set-Location $ProjectDir

if (-not (Test-Path $VenvPython)) {
    Write-Host "[noticeboard] First run setup: creating Python virtual environment..."

    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        Invoke-CheckedCommand $PyLauncher.Source @("-3", "-m", "venv", $VenvDir)
    } else {
        $Python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $Python) {
            throw "Python was not found. Install Python from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'."
        }

        Invoke-CheckedCommand $Python.Source @("-m", "venv", $VenvDir)
    }
}

& $VenvPython -c "import PyQt6, requests, qtawesome" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[noticeboard] Installing PC app dependencies..."
    Invoke-CheckedCommand $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-CheckedCommand $VenvPython @("-m", "pip", "install", "PyQt6", "requests", "qtawesome")
}

if ($CheckOnly) {
    Write-Host "[noticeboard] PC launcher check passed."
    exit 0
}

Write-Host "[noticeboard] Starting Noticeboard Manager..."
Invoke-CheckedCommand $VenvPython @($AppPath)
