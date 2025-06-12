# PowerShell script to test signal-cli installation
Write-Host "Testing signal-cli installation..." -ForegroundColor Green

# Check if Java is installed
try {
    $javaVersion = java -version 2>&1 | Out-String
    Write-Host "Java is installed:" -ForegroundColor Green
    Write-Host $javaVersion
} catch {
    Write-Host "Java is not installed or not in PATH. Please install Java." -ForegroundColor Red
    Write-Host "Download from: https://www.oracle.com/java/technologies/downloads/#java11" -ForegroundColor Yellow
    exit 1
}

# Check if signal-cli.bat exists
$signalCliBat = Join-Path (Get-Location) "signal-cli\signal-cli-0.13.16\bin\signal-cli.bat"
if (Test-Path $signalCliBat) {
    Write-Host "signal-cli.bat found at: $signalCliBat" -ForegroundColor Green
    
    # Test running signal-cli
    Write-Host "Testing signal-cli execution..." -ForegroundColor Green
    try {
        $output = cmd /c $signalCliBat --version 2>&1
        Write-Host "signal-cli output:" -ForegroundColor Green
        Write-Host $output
        
        Write-Host "signal-cli test successful!" -ForegroundColor Green
        Write-Host "You can now use signal-cli with your bot." -ForegroundColor Green
    } catch {
        Write-Host "Error running signal-cli: $_" -ForegroundColor Red
    }
} else {
    Write-Host "signal-cli.bat not found at expected location: $signalCliBat" -ForegroundColor Red
    Write-Host "Please make sure the signal-cli files are correctly extracted." -ForegroundColor Yellow
}
