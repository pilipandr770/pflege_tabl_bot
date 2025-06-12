# Create the directory structure for the Signal CLI jar file
$outputDir = "signal-cli\signal-cli-0.13.16\build\libs"
$outputPath = Join-Path -Path $outputDir -ChildPath "signal-cli-0.13.16-all.jar"

# Create directory if it doesn't exist
if (-not (Test-Path $outputDir)) {
    New-Item -Path $outputDir -ItemType Directory -Force | Out-Null
    Write-Host "Created directory: $outputDir"
}

# Download the Signal CLI jar file directly
$url = "https://github.com/AsamK/signal-cli/releases/download/v0.13.16/signal-cli-0.13.16-all.jar"
Write-Host "Downloading Signal CLI jar from $url..."

try {
    # Use more robust download method
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    # Create WebClient for download
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($url, (Join-Path -Path (Get-Location) -ChildPath $outputPath))
    Write-Host "Signal CLI jar successfully downloaded to: $outputPath"
} catch {
    Write-Host "Error downloading file: $_"
    
    # Alternative download method if first one fails
    Write-Host "Trying alternative download method..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $outputPath
        Write-Host "Signal CLI jar successfully downloaded to: $outputPath"
    } catch {
        Write-Host "Failed to download Signal CLI jar: $_"
        exit 1
    }
}

# Verify file exists and has content
if (Test-Path $outputPath) {
    $fileSize = (Get-Item $outputPath).Length
    if ($fileSize -gt 0) {
        Write-Host "Download successful! File size: $([math]::Round($fileSize/1MB, 2)) MB"
        Write-Host "You can now use the Signal integration in your bot!"
    } else {
        Write-Host "Warning: Downloaded file is empty!"
    }
} else {
    Write-Host "Error: File was not created!"
}
