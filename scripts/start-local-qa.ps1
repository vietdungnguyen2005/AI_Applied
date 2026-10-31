param(
    [ValidateSet('qwen3.5:4b-q4_K_M','qwen3.5:9b-q4_K_M')]
    [string]$Model = 'qwen3.5:4b-q4_K_M',
    [ValidateRange(1024,65535)]
    [int]$Port = 8091
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$localValues = @{
    UV_PROJECT_ENVIRONMENT = Join-Path $repoRoot '.local/p05-env'
    AI_PROVIDER_MODE = 'local'
    AI_LIVE_ENABLED = 'false'
    AI_QA_ENABLED = 'true'
    AI_QA_EMBEDDING_MODE = 'local'
    AI_QA_MODEL_BUNDLE = Join-Path $repoRoot '.local/models/multilingual-e5-small'
    AI_OLLAMA_MODEL = $Model
    AI_OLLAMA_CONTEXT = '4096'
    AI_REQUEST_DEADLINE_SECONDS = '30'
    AI_OLLAMA_TIMEOUT_SECONDS = '25'
    AI_BIND_HOST = '127.0.0.1'
    AI_PRIVATE_CONTAINER = 'false'
    AI_PORT = [string]$Port
}
if (-not $env:AI_DATABASE_URL) {
    $localValues.AI_DATABASE_URL = 'postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai'
}
$savedValues = @{}
foreach ($key in $localValues.Keys) {
    $savedValues[$key] = [Environment]::GetEnvironmentVariable($key,'Process')
}
Push-Location -LiteralPath $repoRoot
try {
    foreach ($key in $localValues.Keys) {
        [Environment]::SetEnvironmentVariable($key,$localValues[$key],'Process')
    }
    # Packages and model artifacts must be installed beforehand; no runtime cloud fallback/pull.
    python -m uv run --frozen --offline --extra local-embeddings vmarket-ai serve
    if ($LASTEXITCODE -ne 0) { throw 'Local QA startup failed; inspect safe diagnostics.' }
}
finally {
    foreach ($key in $savedValues.Keys) {
        [Environment]::SetEnvironmentVariable($key,$savedValues[$key],'Process')
    }
    Pop-Location
}
