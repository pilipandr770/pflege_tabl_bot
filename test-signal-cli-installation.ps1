# PowerShell script to test signal-cli functionality
Write-Host "Testing signal-cli installation and configuration..." -ForegroundColor Green

# Define the path to signal-cli
$signalCliDir = Join-Path (Get-Location) "signal-cli\signal-cli-0.13.16"
$signalCliBat = Join-Path $signalCliDir "bin\signal-cli.bat"
$classpath = "$signalCliDir\lib\*"

# Check if signal-cli.bat exists
if (Test-Path $signalCliBat) {
    Write-Host "signal-cli.bat found at: $signalCliBat" -ForegroundColor Green
} else {
    Write-Host "signal-cli.bat not found at expected location: $signalCliBat" -ForegroundColor Red
    exit 1
}

# Get phone number from user
$phoneNumber = Read-Host "Enter your Signal phone number (with country code, e.g., +4916095030120)"

# Test registration status using signal-cli.bat
Write-Host "Checking registration status using signal-cli.bat..." -ForegroundColor Green
try {
    $env:PATH += ";$signalCliDir\bin" # Add to PATH temporarily
    & $signalCliBat -u $phoneNumber version
    & $signalCliBat -u $phoneNumber listDevices
} catch {
    Write-Host "Error using signal-cli.bat: $_" -ForegroundColor Red
}

# Test registration status using direct Java
Write-Host "Checking registration status using direct Java..." -ForegroundColor Green
try {
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "listDevices"
} catch {
    Write-Host "Error using direct Java: $_" -ForegroundColor Red
}

# Try sending a message
$sendMessage = Read-Host "Do you want to try sending a message to yourself? (y/n)"
if ($sendMessage -eq "y") {
    try {
        Write-Host "Sending message using direct Java..." -ForegroundColor Green
        java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "send" "-m" "Test message from signal-cli test script" "$phoneNumber"
        
        Write-Host "Sending message using signal-cli.bat..." -ForegroundColor Green
        & $signalCliBat -u $phoneNumber send -m "Test message from signal-cli.bat" $phoneNumber
    } catch {
        Write-Host "Error sending message: $_" -ForegroundColor Red
    }
}

# Report finish
Write-Host "Test completed." -ForegroundColor Green
