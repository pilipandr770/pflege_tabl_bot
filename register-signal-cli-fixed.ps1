# PowerShell script to register signal-cli user
Write-Host "Registering Signal user with signal-cli..." -ForegroundColor Green

# Check if Java is installed
try {
    java -version 2>&1 | Out-String
    Write-Host "Java is installed." -ForegroundColor Green
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
Write-Host "Choose verification method:" -ForegroundColor Yellow
Write-Host "1. SMS (text message)" -ForegroundColor Yellow
Write-Host "2. Voice call" -ForegroundColor Yellow
$methodChoice = Read-Host "Enter 1 for SMS or 2 for Voice"

$verificationMethod = "sms"
if ($methodChoice -eq "2") {
    $verificationMethod = "voice"
}

# Request verification code
try {
    Write-Host "Requesting verification code via $verificationMethod..." -ForegroundColor Green
    
    # Use Java to run signal-cli for registration
    if ($verificationMethod -eq "voice") {
        Write-Host "Requesting voice verification..." -ForegroundColor Green
        java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "register" "--voice"
    } else {
        Write-Host "Requesting SMS verification..." -ForegroundColor Green
        java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "register"
    }
    
    # Prompt for verification code
    Write-Host "You should receive a verification code shortly." -ForegroundColor Green
    $verificationCode = Read-Host "Enter the verification code you received"
    
    # Verify the code
    Write-Host "Verifying code..." -ForegroundColor Green
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "verify" "$verificationCode"
    
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
    
    # Update the .env file with the recipient phone number
    $updateEnvFile = Read-Host "Do you want to update the .env file with your phone number as recipient? (y/n)"
    if ($updateEnvFile -eq "y") {
        $envFile = Join-Path (Get-Location) ".env"
        if (Test-Path $envFile) {
            $envContent = Get-Content $envFile -Raw
            if ($envContent -match "SIGNAL_PHONE=") {
                $envContent = $envContent -replace "SIGNAL_PHONE=.*", "SIGNAL_PHONE=$phoneNumber"
            } else {
                $envContent += "`nSIGNAL_PHONE=$phoneNumber"
            }
            $envContent | Set-Content $envFile -Force
            Write-Host ".env file updated with phone number." -ForegroundColor Green
        } else {
            # Create new .env file if it doesn't exist
            "SIGNAL_PHONE=$phoneNumber" | Out-File $envFile
            Write-Host "Created new .env file with SIGNAL_PHONE=$phoneNumber" -ForegroundColor Green
        }
    }
    
} catch {
    Write-Host "Error during registration process: $_" -ForegroundColor Red
    Write-Host "Please try again." -ForegroundColor Yellow
}

# Finally, let's test the registration
Write-Host ""
Write-Host "Testing Signal registration..." -ForegroundColor Green
$testRegistration = Read-Host "Do you want to test if registration was successful? (y/n)"

if ($testRegistration -eq "y") {
    try {
        Write-Host "Checking registration status..." -ForegroundColor Green
        java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "listDevices"
        Write-Host "Registration successful! You can now use Signal from your bot." -ForegroundColor Green
        
        # Test sending a message to self
        $testMessage = Read-Host "Do you want to send a test message to yourself? (y/n)"
        if ($testMessage -eq "y") {
            java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "send" "-m" "Test message from signal-cli" "$phoneNumber"
            Write-Host "Test message sent!" -ForegroundColor Green
        }
    } catch {
        Write-Host "Error checking registration: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "You can now run your bot with 'py bot.py'" -ForegroundColor Green
