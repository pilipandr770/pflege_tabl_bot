# PowerShell скрипт для изменения номера получателя Signal
Write-Host "Настройка номера получателя уведомлений Signal" -ForegroundColor Green

# Получаем текущие настройки
$envFile = Join-Path (Get-Location) ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "Файл .env не найден. Создаю новый..." -ForegroundColor Yellow
    "" | Out-File $envFile
}

$envContent = Get-Content $envFile -Raw

Write-Host "Текущие настройки:" -ForegroundColor Cyan
if ($envContent -match "SIGNAL_PHONE=(.+)") {
    $currentPhone = $matches[1]
    Write-Host "Текущий номер получателя: $currentPhone" -ForegroundColor Cyan
} else {
    $currentPhone = ""
    Write-Host "Номер получателя не настроен" -ForegroundColor Yellow
}

# Получаем настройки из bot.py
$botFile = Join-Path (Get-Location) "bot.py"
$botContent = Get-Content $botFile -Raw

if ($botContent -match "sender = '(\+\d+)'") {
    $senderPhone = $matches[1]
    Write-Host "Текущий номер отправителя (из bot.py): $senderPhone" -ForegroundColor Cyan
} else {
    $senderPhone = ""
    Write-Host "Номер отправителя не найден в bot.py" -ForegroundColor Yellow
}

# Запрашиваем новый номер
$newPhone = Read-Host "Введите номер телефона получателя (с кодом страны, например +79001234567)"

# Проверка формата номера
if (-not ($newPhone -match '^\+\d+$')) {
    Write-Host "Неверный формат номера. Номер должен начинаться со знака + и содержать только цифры." -ForegroundColor Red
    exit 1
}

# Применяем новые настройки
if ($envContent -match "SIGNAL_PHONE=") {
    $envContent = $envContent -replace "SIGNAL_PHONE=.*", "SIGNAL_PHONE=$newPhone"
} else {
    $envContent += "`nSIGNAL_PHONE=$newPhone"
}

$envContent | Set-Content $envFile -Force

Write-Host "Номер получателя обновлен: $newPhone" -ForegroundColor Green
Write-Host ""
Write-Host "Для тестирования отправки сообщения можно выполнить команду:" -ForegroundColor Cyan
Write-Host ".\test-signal-message.ps1" -ForegroundColor White
