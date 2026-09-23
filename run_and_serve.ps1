[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Auto-detect if features/ directory is located inside api_framework/
$switchedDir = $false
if (-not (Test-Path "features") -and (Test-Path "api_framework\features")) {
    Push-Location "api_framework"
    $switchedDir = $true
}

try {
    $resultsDirectory = Join-Path (Get-Location) "allure-results"
    if (-not (Test-Path -LiteralPath $resultsDirectory)) {
        New-Item -ItemType Directory -Path $resultsDirectory -Force | Out-Null
    }
    Get-ChildItem -LiteralPath $resultsDirectory -Force | Remove-Item -Recurse -Force

    # 1. Run the test suite with Allure formatter
    Write-Host "Running Behave test suite..." -ForegroundColor Cyan
    behave -f allure_behave.formatter:AllureFormatter -o $resultsDirectory features/

    # Resolve local Allure binary path
    $allureBat = ".\.tools\allure\bin\allure.bat"
    if (-not (Test-Path $allureBat) -and (Test-Path "..\.tools\allure\bin\allure.bat")) {
        $allureBat = "..\.tools\allure\bin\allure.bat"
    }

    # 2. Check if .tools/allure/bin/allure.bat exists. If not, prompt the user to run .\install_allure.ps1 first.
    if (-not (Test-Path $allureBat)) {
        Write-Host ""
        Write-Host "Error: Local Allure CLI not found at '$allureBat'." -ForegroundColor Red
        Write-Host "Please run .\install_allure.ps1 first to install Allure CLI locally." -ForegroundColor Yellow
        exit 1
    }

    # Verify Java runtime presence (Allure requires Java 8+)
    if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "Warning: Java (JRE/JDK) was not found in your PATH." -ForegroundColor Yellow
        Write-Host "Allure CLI requires Java 8+ to compile and serve the HTML dashboard." -ForegroundColor Yellow
        Write-Host "If Allure throws an error, install Java (e.g., Eclipse Temurin JDK) and retry." -ForegroundColor Yellow
        Write-Host ""
    }

    # 3. Generate a native Allure report with the project's restrained presentation theme.
    Write-Host "Generating and opening Allure report..." -ForegroundColor Green
    & ".\reporting\generate_allure_report.ps1" -ResultsDirectory $resultsDirectory -ReportDirectory "allure-report" -Open

} finally {
    if ($switchedDir) {
        Pop-Location
    }
}
