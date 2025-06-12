# PowerShell script to register with Signal using the captcha method
Write-Host "Registering Signal user with signal-cli (captcha method)..." -ForegroundColor Green

# Define the path to signal-cli
$signalCliDir = Join-Path (Get-Location) "signal-cli\signal-cli-0.13.16"
$classpath = "$signalCliDir\lib\*"

# Get phone number from user
$phoneNumber = Read-Host "Enter your Signal phone number (with country code, e.g., +4916095030120)"

Write-Host "For registration, you need to solve a captcha." -ForegroundColor Yellow
Write-Host "1. Open this URL in your browser: https://signalcaptchas.org/registration/generate.html" -ForegroundColor Cyan
Write-Host "2. Solve the captcha" -ForegroundColor Cyan
Write-Host "3. Right-click on 'Open Signal' and select 'Copy link address'" -ForegroundColor Cyan
Write-Host "4. Extract the captcha token from the URL (the part after 'captcha=')" -ForegroundColor Cyan
Write-Host ""

$captchaToken = Read-Host "Enter the captcha token (the part after 'captcha=' in the URL)"

# Remove any URL encoding or quotes
$captchaToken = $captchaToken -replace "%3D", "="
$captchaToken = $captchaToken -replace '"', ''
$captchaToken = $captchaToken -replace "'", ""

# If the token starts with "signalcaptcha://", remove it
if ($captchaToken.StartsWith("signalcaptcha://")) {
    $captchaToken = $captchaToken.Substring("signalcaptcha://".Length)
}

try {
    # Register with the captcha token
    Write-Host "Registering with captcha token..." -ForegroundColor Green
    
    # Run the registration command
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "register" "--captcha" "$captchaToken"
    
    # Prompt for verification code
    $verificationCode = Read-Host "Enter the verification code you received"
    
    # Verify the code
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "verify" "$verificationCode"
    
    # Check if it worked by listing devices
    Write-Host "Checking registration status..." -ForegroundColor Green
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "listDevices"
    
    # Update files if registration was successful
    Write-Host "Registration successful! Updating configuration files..." -ForegroundColor Green
    
    # Update bot.py
    $botFile = Join-Path (Get-Location) "bot.py"
    $content = Get-Content $botFile -Raw
    $content = $content -replace "sender = '\+\d+'", "sender = '$phoneNumber'"
    $content | Set-Content $botFile -Force
    Write-Host "bot.py updated." -ForegroundColor Green
    
    # Update .env
    $envFile = Join-Path (Get-Location) ".env"
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "SIGNAL_PHONE=") {
        $envContent = $envContent -replace "SIGNAL_PHONE=.*", "SIGNAL_PHONE=$phoneNumber"
    } else {
        $envContent += "`nSIGNAL_PHONE=$phoneNumber"
    }
    $envContent | Set-Content $envFile -Force
    Write-Host ".env updated." -ForegroundColor Green
    
    # Try sending a test message
    Write-Host "Sending a test message to yourself..." -ForegroundColor Green
    java --enable-native-access=ALL-UNNAMED "-classpath" "$classpath" "org.asamk.signal.Main" "-u" "$phoneNumber" "send" "-m" "Test message from signal-cli registration script" "$phoneNumber"
    Write-Host "Test message sent successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "Error during registration: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "You can now run your bot with 'py bot.py'" -ForegroundColor Green
