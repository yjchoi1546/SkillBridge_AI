param()
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $appRoot
$uv = (Get-Command uv -ErrorAction Stop).Source
$env:UV_CACHE_DIR = Join-Path $appRoot '.cache/uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $appRoot '.tools/python'
$env:UV_PROJECT_ENVIRONMENT = Join-Path $appRoot '.tools/ai-venv'

Push-Location $repositoryRoot
try {
    # Keep the interpreter, packages and cache inside app; never rewrite the shared lockfile.
    & $uv python install 3.12 --no-bin --no-registry
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
    $python = & $uv python find --managed-python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Could not locate the project Python interpreter.' }
    & $uv sync --locked --python $python
    if ($LASTEXITCODE -ne 0) { throw 'AI dependency installation failed.' }
    & $uv run --frozen --no-sync python -c 'import http.cookiejar; import ai.src.api'
    if ($LASTEXITCODE -ne 0) { throw 'AI public API import failed.' }
    Write-Host 'AI environment ready. The backend uses LLM_PROVIDER=fake by default.'
} finally { Pop-Location }
