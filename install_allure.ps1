[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# 1. Force TLS 1.2 for secure downloading
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$toolsDir = Join-Path $PSScriptRoot ".tools"
$allureDir = Join-Path $toolsDir "allure"
$zipPath = Join-Path $PSScriptRoot "allure.zip"
$downloadUrl = "https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.30.0/allure-commandline-2.30.0.zip"

# 2. Check if .tools/allure directory already exists. If it does, skip the installation.
if (Test-Path $allureDir) {
    Write-Host "Local Allure CLI already exists at: $allureDir. Skipping installation." -ForegroundColor Yellow
    exit 0
}

# 3. Download the Allure 2.30.0 ZIP file from Maven Central and save to temporary allure.zip
Write-Host "Downloading Allure 2.30.0 from Maven Central..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath

# 4. Extract the ZIP archive into a .tools/ directory in the project root
if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
}

Write-Host "Extracting archive to $toolsDir..." -ForegroundColor Cyan
Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force

# 5. Rename the extracted folder (allure-2.30.0) to exactly .tools/allure
$extractedDir = Join-Path $toolsDir "allure-2.30.0"
if (Test-Path $extractedDir) {
    Rename-Item -Path $extractedDir -NewName "allure" -Force
}

# 6. Delete the temporary allure.zip file
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

# Optional: Link .tools into api_framework if running from multi-folder structure
$subTools = Join-Path $PSScriptRoot "api_framework\.tools"
if ((Test-Path (Join-Path $PSScriptRoot "api_framework")) -and (-not (Test-Path $subTools))) {
    try {
        New-Item -ItemType Junction -Path $subTools -Target $toolsDir -Force | Out-Null
    } catch {
        # Junction creation optional
    }
}

# 7. Print green success message to the console
Write-Host "Local Allure CLI installed successfully." -ForegroundColor Green
