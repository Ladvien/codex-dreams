# PowerShell script to install Codex Dreams Daemon as Windows service
# Run this script as Administrator

param(
    [string]$ServiceName = "codex-dreams-daemon",
    [string]$DisplayName = "Codex Dreams Insights Generation Daemon",
    [string]$Description = "Automatically generates insights from memories using Ollama LLM",
    [string]$ProjectPath = $null,
    [switch]$UseNSSM = $false
)

# Get the project root directory
if (-not $ProjectPath) {
    $ProjectPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

Write-Host "Installing Codex Dreams Daemon as Windows Service..."
Write-Host "Project Path: $ProjectPath"
Write-Host "Service Name: $ServiceName"

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator. Exiting..."
    exit 1
}

# Find Python executable
$PythonExe = $null
$PossiblePaths = @(
    "$ProjectPath\venv\Scripts\python.exe",
    "python.exe",
    "py.exe"
)

foreach ($Path in $PossiblePaths) {
    if (Get-Command $Path -ErrorAction SilentlyContinue) {
        $PythonExe = (Get-Command $Path).Source
        break
    }
}

if (-not $PythonExe) {
    Write-Error "Could not find Python executable. Please ensure Python is installed and available in PATH."
    exit 1
}

Write-Host "Using Python: $PythonExe"

# Define the service executable and arguments
$ServicePath = "$ProjectPath\src\daemon\scheduler.py"
$ServiceArgs = "--daemon"

try {
    if ($UseNSSM -and (Get-Command "nssm" -ErrorAction SilentlyContinue)) {
        # Use NSSM (Non-Sucking Service Manager)
        Write-Host "Installing service using NSSM..."

        & nssm install $ServiceName $PythonExe $ServicePath $ServiceArgs
        & nssm set $ServiceName Description $Description
        & nssm set $ServiceName DisplayName $DisplayName
        & nssm set $ServiceName AppDirectory $ProjectPath
        & nssm set $ServiceName Start SERVICE_AUTO_START
        & nssm set $ServiceName ObjectName LocalSystem

        Write-Host "Service installed successfully using NSSM!"

    } else {
        # Use built-in New-Service
        Write-Host "Installing service using PowerShell New-Service..."

        $BinaryPathName = "`"$PythonExe`" `"$ServicePath`" $ServiceArgs"

        New-Service -Name $ServiceName `
                   -BinaryPathName $BinaryPathName `
                   -DisplayName $DisplayName `
                   -Description $Description `
                   -StartupType Automatic

        Write-Host "Service installed successfully!"
    }

    Write-Host ""
    Write-Host "To start the service:"
    Write-Host "  Start-Service -Name $ServiceName"
    Write-Host ""
    Write-Host "To check service status:"
    Write-Host "  Get-Service -Name $ServiceName"
    Write-Host ""
    Write-Host "To view service logs, check the configured log file in the daemon configuration."

} catch {
    Write-Error "Failed to install service: $_"
    exit 1
}