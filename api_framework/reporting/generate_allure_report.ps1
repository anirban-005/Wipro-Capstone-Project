[CmdletBinding()]
param(
    [string]$ResultsDirectory = (Join-Path $PSScriptRoot "..\allure-results"),
    [string]$ReportDirectory  = (Join-Path $PSScriptRoot "..\allure-report"),
    [switch]$Open
)

$ErrorActionPreference = "Stop"
$projectRoot    = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workspaceRoot  = (Resolve-Path (Join-Path $projectRoot "..")).Path
$allureCommand  = Join-Path $workspaceRoot ".tools\allure\bin\allure.bat"
$themeSource    = Join-Path $PSScriptRoot "allure-student-theme.css"
$resolvedResults = (Resolve-Path $ResultsDirectory).Path
# Resolve the report directory to an absolute path (create it if needed so Resolve-Path works)
if (-not (Test-Path -LiteralPath $ReportDirectory)) {
    New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
}
$resolvedReport = (Resolve-Path $ReportDirectory).Path

if (-not (Test-Path -LiteralPath $allureCommand -PathType Leaf)) {
    throw "Allure CLI was not found at $allureCommand. Run .\install_allure.ps1 from the workspace root."
}


# --- environment.properties ---------------------------------------------------
# Write clean key=value lines with no UTF-8 BOM.
# Keys use plain spaces (no backtick escaping) so Allure renders them verbatim.
$environment    = if ($env:API_ENV) { $env:API_ENV } else { "staging" }
$pythonVersion  = (& python --version 2>&1).ToString().Trim()

$environmentLines = @(
    "API\ Base\ URL=https://gorest.co.in/public/v2",
    "Environment=$environment",
    "Framework=Behave BDD + Requests",
    "Runtime=$pythonVersion",
    "Report\ Theme=Simple technical report"
)

$environmentFile  = Join-Path $resolvedResults "environment.properties"
# UTF8Encoding($false) = UTF-8 without BOM — Allure requires this.
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($environmentFile, $environmentLines, $utf8NoBom)

# --- Generate the native Allure report ----------------------------------------
& $allureCommand generate $resolvedResults --clean -o $resolvedReport
if ($LASTEXITCODE -ne 0) {
    throw "Allure report generation failed with exit code $LASTEXITCODE."
}

# --- Inject the lightweight student CSS theme ---------------------------------
Copy-Item -LiteralPath $themeSource -Destination (Join-Path $resolvedReport "allure-student-theme.css") -Force

$indexPath = Join-Path $resolvedReport "index.html"
$indexHtml = [System.IO.File]::ReadAllText($indexPath, $utf8NoBom)
$indexHtml = $indexHtml.Replace("<title>Allure Report</title>", "<title>API Automation Test Report</title>")
$themeLink = '    <link rel="stylesheet" type="text/css" href="allure-student-theme.css">'
if (-not $indexHtml.Contains($themeLink)) {
    $indexHtml = $indexHtml.Replace(
        '    <link rel="stylesheet" type="text/css" href="styles.css">',
        "    <link rel=`"stylesheet`" type=`"text/css`" href=`"styles.css`">`n$themeLink"
    )
}
[System.IO.File]::WriteAllText($indexPath, $indexHtml, $utf8NoBom)

Write-Host "Allure report generated: $resolvedReport" -ForegroundColor Green
if ($Open) {
    & $allureCommand open $resolvedReport
}
