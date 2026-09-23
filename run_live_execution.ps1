[CmdletBinding()]
param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$workspaceRoot = $PSScriptRoot
$frameworkRoot = Join-Path $workspaceRoot "api_framework"
$stateDirectory = Join-Path $frameworkRoot "live-execution"
$stateFile = Join-Path $stateDirectory "execution_state.json"
$serverScript = Join-Path $frameworkRoot "reporting\live_execution_server.py"

New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$env:EXECUTION_STATE_FILE = $stateFile
$server = Start-Process -FilePath "python" -ArgumentList @($serverScript, "--state-file", $stateFile, "--port", $Port) -PassThru -WindowStyle Hidden

try {
    Start-Process "http://127.0.0.1:$Port"
    Push-Location $frameworkRoot
    $resultsDirectory = Join-Path (Get-Location) "allure-results"
    if (-not (Test-Path -LiteralPath $resultsDirectory)) {
        New-Item -ItemType Directory -Path $resultsDirectory -Force | Out-Null
    }
    Get-ChildItem -LiteralPath $resultsDirectory -Force | Remove-Item -Recurse -Force
    python -m behave -f allure_behave.formatter:AllureFormatter -o $resultsDirectory features/
    & ".\reporting\generate_allure_report.ps1" -ResultsDirectory $resultsDirectory -ReportDirectory "allure-report" -Open

    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " Live Execution Dashboard is ACTIVE: http://127.0.0.1:$Port" -ForegroundColor Cyan
    Write-Host " (Keep this window open. Press Enter when you want to stop the server)" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Green
    [Console]::ReadLine() | Out-Null
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id
    }
    Pop-Location -ErrorAction SilentlyContinue
}
