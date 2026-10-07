$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $preparedDependencies = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'work\python-deps'
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if ((Test-Path -LiteralPath $bundledPython) -and (Test-Path -LiteralPath (Join-Path $preparedDependencies 'fastapi'))) {
        $taskPython = $bundledPython
        $env:PYTHONPATH = $preparedDependencies
    } else {
        Write-Host 'First follow the Python and Ollama setup in README.md.'
        Write-Host 'python -m venv .venv'
        Write-Host '.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt'
        exit 1
    }
}
Write-Host 'Open http://127.0.0.1:8000 in your browser. Press Ctrl+C to stop.'
& $taskPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
