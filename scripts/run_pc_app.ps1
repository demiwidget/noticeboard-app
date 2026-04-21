param(
    [switch]$CheckOnly,
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms

function Show-NoticeboardMessage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [string]$Title = "Noticeboard Manager",

        [System.Windows.Forms.MessageBoxIcon]$Icon = [System.Windows.Forms.MessageBoxIcon]::Information
    )

    [void][System.Windows.Forms.MessageBox]::Show(
        $Message,
        $Title,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        $Icon
    )
}

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

function Invoke-QuietCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $output = & $FilePath @Arguments 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    return ($output | Out-String).Trim()
}

function Test-GitRepoCanAutoUpdate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GitExe,

        [Parameter(Mandatory = $true)]
        [string]$ProjectDir
    )

    if (-not (Test-Path (Join-Path $ProjectDir ".git"))) {
        return $false
    }

    $upstream = Invoke-QuietCommand $GitExe @("-C", $ProjectDir, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if (-not $upstream) {
        return $false
    }

    $changes = Invoke-QuietCommand $GitExe @("-C", $ProjectDir, "status", "--porcelain", "--untracked-files=no")
    if ($changes) {
        return $false
    }

    return $true
}

function Update-RepoIfNeeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$GitExe,

        [Parameter(Mandatory = $true)]
        [string]$ProjectDir
    )

    if (-not (Test-GitRepoCanAutoUpdate -GitExe $GitExe -ProjectDir $ProjectDir)) {
        return $false
    }

    & $GitExe -C $ProjectDir fetch --quiet origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }

    $behind = Invoke-QuietCommand $GitExe @("-C", $ProjectDir, "rev-list", "--count", "HEAD..@{u}")
    if (-not $behind -or [int]$behind -le 0) {
        return $false
    }

    Invoke-CheckedCommand $GitExe @("-C", $ProjectDir, "pull", "--ff-only")
    return $true
}

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = Split-Path -Parent $ScriptDir
    $VenvDir = Join-Path $ProjectDir ".venv"
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    $VenvPythonGui = Join-Path $VenvDir "Scripts\pythonw.exe"
    $AppPath = Join-Path $ProjectDir "pc_app\main.py"

    if (-not (Test-Path $AppPath)) {
        throw "Could not find the PC app at: $AppPath"
    }

    Set-Location $ProjectDir

    if (-not $SkipUpdate) {
        $Git = Get-Command git -ErrorAction SilentlyContinue
        if ($Git) {
            [void](Update-RepoIfNeeded -GitExe $Git.Source -ProjectDir $ProjectDir)
        }
    }

    if (-not (Test-Path $VenvPython)) {
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
        Invoke-CheckedCommand $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-CheckedCommand $VenvPython @("-m", "pip", "install", "PyQt6", "requests", "qtawesome")
    }

    if ($CheckOnly) {
        Write-Host "[noticeboard] PC launcher check passed."
        exit 0
    }

    if (-not (Test-Path $VenvPythonGui)) {
        $VenvPythonGui = $VenvPython
    }

    & $VenvPythonGui $AppPath
    exit $LASTEXITCODE
} catch {
    $message = $_.Exception.Message
    if (-not $message) {
        $message = $_ | Out-String
    }

    Show-NoticeboardMessage -Message $message -Title "Noticeboard Manager Startup Error" -Icon ([System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}
