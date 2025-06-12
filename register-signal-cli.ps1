# PowerShell script to register signal-cli user
Write-Host "Registering Signal user with signal-cli..." -ForegroundColor Green

# Check if Java is installed
try {
    $javaVersion = java -version 2>&1 | Out-String
    Write-Host "Java is installed: $javaVersion" -ForegroundColor Green
} catch {
    Write-Host "Java is not installed or not in PATH. Please install Java." -ForegroundColor Red
    Write-Host "Download from: https://www.oracle.com/java/technologies/downloads/#java11" -ForegroundColor Yellow
    exit 1
}

# Define the path to signal-cli
$signalCliDir = Join-Path (Get-Location) "signal-cli\signal-cli-0.13.16"
$libDir = Join-Path $signalCliDir "lib"
$classpath = "$signalCliDir\lib\*"

# Get phone number from user if not provided
$phoneNumber = Read-Host "Enter your Signal phone number (with country code, e.g., +4916095030120)"

# Check if the phone number format is correct
if (-not ($phoneNumber -match '^\+\d+$')) {
    Write-Host "Phone number must start with a plus sign followed by country code and number, e.g., +4916095030120" -ForegroundColor Red
    exit 1
}

# Explain registration process
Write-Host "Signal registration process:" -ForegroundColor Cyan
Write-Host "1. We'll request a verification code to be sent to your phone" -ForegroundColor Cyan
Write-Host "2. You'll receive an SMS or call with the code" -ForegroundColor Cyan
Write-Host "3. You'll need to enter the code to complete registration" -ForegroundColor Cyan
Write-Host ""

# Confirm before proceeding
$confirm = Read-Host "Do you want to proceed with registration for $phoneNumber? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Registration cancelled." -ForegroundColor Yellow
    exit 0
}

# Choose verification method
$verificationMethod = Read-Host "Choose verification method: 'sms' or 'voice'"
if ($verificationMethod -ne "sms" -and $verificationMethod -ne "voice") {
    Write-Host "Invalid verification method. Please choose 'sms' or 'voice'." -ForegroundColor Red
    exit 1
}

# Request verification code
try {
    Write-Host "Requesting verification code via $verificationMethod..." -ForegroundColor Green
    
    # Use Java to run signal-cli for registration
    $command = "java --enable-native-access=ALL-UNNAMED -classpath `"$classpath`" org.asamk.signal.Main -u `"$phoneNumber`" register --voice"
    if ($verificationMethod -eq "sms") {
        $command = "java --enable-native-access=ALL-UNNAMED -classpath `"$classpath`" org.asamk.signal.Main -u `"$phoneNumber`" register"
    }
    
    Write-Host "Executing: $command" -ForegroundColor DarkGray
    Invoke-Expression $command
    
    # Prompt for verification code
    $verificationCode = Read-Host "Enter the verification code you received"
    
    # Verify the code
    Write-Host "Verifying code..." -ForegroundColor Green
    $verifyCommand = "java --enable-native-access=ALL-UNNAMED -classpath `"$classpath`" org.asamk.signal.Main -u `"$phoneNumber`" verify $verificationCode"
    Write-Host "Executing: $verifyCommand" -ForegroundColor DarkGray
    Invoke-Expression $verifyCommand
    
    Write-Host "Registration completed successfully!" -ForegroundColor Green
    Write-Host "You can now use signal-cli with your phone number: $phoneNumber" -ForegroundColor Green
    
    # Update the bot.py file with the registered number
    $updateBotFile = Read-Host "Do you want to update the bot.py file with your registered number? (y/n)"
    if ($updateBotFile -eq "y") {
        $botFile = Join-Path (Get-Location) "bot.py"
        $content = Get-Content $botFile -Raw
        $content = $content -replace "sender = '\+\d+'", "sender = '$phoneNumber'"
        $content | Set-Content $botFile -Force
        Write-Host "bot.py updated with your phone number." -ForegroundColor Green
    }
    
} catch {
    Write-Host "Error during registration process: $_" -ForegroundColor Red
    Write-Host "Please try again." -ForegroundColor Yellow
}
