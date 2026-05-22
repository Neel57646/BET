param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $AgentArgs
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $RepoRoot "src"

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCommand -and $PythonCommand.Source -notmatch "WindowsApps") {
    & $PythonCommand.Source -m evbetting_agent @AgentArgs
    exit $LASTEXITCODE
}

$CodexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $CodexPython) {
    & $CodexPython -m evbetting_agent @AgentArgs
    exit $LASTEXITCODE
}

throw "Python was not found. Install Python 3.10+ or run with a configured Codex Python runtime."
