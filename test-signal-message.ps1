# PowerShell script to test sending a message with signal-cli
Write-Host "Testing signal-cli messaging..." -ForegroundColor Green

# Define the path to signal-cli
$signalCliDir = Join-Path (Get-Location) "signal-cli\signal-cli-0.13.16"
$classpath = "$signalCliDir\lib\*"

# Get sender phone number
$senderPhone = Read-Host "Enter your registered Signal phone number (with country code, e.g., +4916095030120)"

# Check if the phone number format is correct
if (-not ($senderPhone -match '^\+\d+$')) {
    Write-Host "Phone number must start with a plus sign followed by country code and number, e.g., +4916095030120" -ForegroundColor Red
    exit 1
}

# Get recipient phone number
$recipientPhone = Read-Host "Enter the recipient's phone number (with country code, e.g., +4916095030120)"

# Check if the recipient phone number format is correct
if (-not ($recipientPhone -match '^\+\d+$')) {
    Write-Host "Phone number must start with a plus sign followed by country code and number, e.g., +4916095030120" -ForegroundColor Red
    exit 1
}

# Get test message
$message = Read-Host "Enter a test message to send"

# Send the message
try {
    Write-Host "Sending test message..." -ForegroundColor Green
    
    # Use Java to run signal-cli for sending message
    $command = "java --enable-native-access=ALL-UNNAMED -classpath `"$classpath`" org.asamk.signal.Main -u `"$senderPhone`" send -m `"$message`" `"$recipientPhone`""
    
    Write-Host "Executing: $command" -ForegroundColor DarkGray
    Invoke-Expression $command
    
    Write-Host "Message sent successfully!" -ForegroundColor Green
    
    # Update the bot.py file with the registered numbers
    $updateBotFile = Read-Host "Do you want to update the bot.py file with these phone numbers? (y/n)"
    if ($updateBotFile -eq "y") {
        $botFile = Join-Path (Get-Location) "bot.py"
        $content = Get-Content $botFile -Raw
        $content = $content -replace "sender = '\+\d+'", "sender = '$senderPhone'"
        
        # Check if SIGNAL_PHONE environment variable is set or update .env file
        $envFile = Join-Path (Get-Location) ".env"
        if (Test-Path $envFile) {
            $envContent = Get-Content $envFile -Raw
            if ($envContent -match "SIGNAL_PHONE=") {
                $envContent = $envContent -replace "SIGNAL_PHONE=.*", "SIGNAL_PHONE=$recipientPhone"
            } else {
                $envContent += "`nSIGNAL_PHONE=$recipientPhone"
            }
            $envContent | Set-Content $envFile -Force
            Write-Host ".env file updated with recipient phone number." -ForegroundColor Green
        } else {
            Write-Host "SIGNAL_PHONE environment variable needs to be set to: $recipientPhone" -ForegroundColor Yellow
            Write-Host "Add this to your .env file or set it as an environment variable." -ForegroundColor Yellow
        }
        
        $content | Set-Content $botFile -Force
        Write-Host "bot.py updated with your sender phone number." -ForegroundColor Green
    }
    
} catch {
    Write-Host "Error sending message: $_" -ForegroundColor Red
}
