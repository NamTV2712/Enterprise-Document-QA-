param(
    [string]$NgrokUrl = "https://blog-making-bloated.ngrok-free.dev",
    [string]$FrontendOrigin = "https://frontend-one-gamma-f9jf11u8ec.vercel.app"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $env:TEMP "enterprise-document-qa-ngrok.pid"
$stdoutLog = Join-Path $env:TEMP "enterprise-document-qa-ngrok.stdout.log"
$stderrLog = Join-Path $env:TEMP "enterprise-document-qa-ngrok.stderr.log"

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$FailureMessage
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            if (& $Condition) {
                return
            }
        } catch {
            # The service may reject requests while it is still starting.
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    throw $FailureMessage
}

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

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not installed or not available on PATH."
}
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    throw "ngrok is not installed or not available on PATH."
}

if (-not (Test-DockerAvailable)) {
    docker desktop start
    Wait-Until -TimeoutSeconds 120 -FailureMessage "Docker Desktop did not start in time." -Condition {
        return Test-DockerAvailable
    }
}

$previousOrigins = $env:ALLOWED_ORIGINS
if ($FrontendOrigin) {
    $env:ALLOWED_ORIGINS = "$FrontendOrigin,http://localhost:3000,http://localhost:5173"
}

try {
    docker compose --project-directory $projectRoot up -d
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed to start the backend."
    }
} finally {
    if ($null -eq $previousOrigins) {
        Remove-Item Env:ALLOWED_ORIGINS -ErrorAction SilentlyContinue
    } else {
        $env:ALLOWED_ORIGINS = $previousOrigins
    }
}

Wait-Until -TimeoutSeconds 180 -FailureMessage "The backend did not become ready in time." -Condition {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -TimeoutSec 5
    return $response.pipeline_ready -eq $true
}

$ngrokProcess = $null
if (Test-Path -LiteralPath $pidFile) {
    $savedPid = Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue
    if ($savedPid) {
        $ngrokProcess = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
    }
}

if (-not $ngrokProcess) {
    $ngrokCommand = (Get-Command ngrok).Source
    $ngrokProcess = Start-Process `
        -FilePath $ngrokCommand `
        -ArgumentList @("http", "8000", "--url", $NgrokUrl, "--log", "stdout") `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
    Set-Content -LiteralPath $pidFile -Value $ngrokProcess.Id
}

Wait-Until -TimeoutSeconds 60 -FailureMessage "The ngrok endpoint did not become ready in time." -Condition {
    $response = Invoke-RestMethod `
        -Uri "$NgrokUrl/health/ready" `
        -Headers @{ "ngrok-skip-browser-warning" = "true" } `
        -TimeoutSec 10
    return $response.pipeline_ready -eq $true
}

"Demo backend ready: $NgrokUrl"
"ngrok PID: $($ngrokProcess.Id)"
