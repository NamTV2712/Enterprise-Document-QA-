param(
    [switch]$KeepDockerDesktop
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $env:TEMP "enterprise-document-qa-ngrok.pid"

function Test-DockerAvailable {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        docker info *> $null
        return $LASTEXITCODE -eq 0
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        $process = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq "ngrok") {
            Stop-Process -Id $process.Id -Force
        }
    }
    Remove-Item -LiteralPath $pidFile -Force
}

if (Test-DockerAvailable) {
    docker compose --project-directory $projectRoot down
    if (-not $KeepDockerDesktop) {
        docker desktop stop
    }
}

"Local demo services stopped."
