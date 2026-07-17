# ====================================================================
# PowerShell Script to register GQN AI Bot as a Windows Startup Task
# Run this script as Administrator.
# ====================================================================

# Ensure running as Admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Vui lòng chạy PowerShell dưới quyền Administrator (Run as Administrator)!"
    Exit
}

$TaskName = "GQN_AI_Telegram_Bot"
$ActionScript = "D:\ADMIN\TelegramRemoteDev\start_bot.bat"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$User = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name  # Chạy bằng user hiện tại

# Tạo hành động (Action) - Mở file .bat
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ActionScript`""

# Cấu hình cài đặt nâng cao
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Kiểm tra nếu Task đã tồn tại thì xóa trước
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[-] Đã gỡ bỏ Scheduled Task cũ." -ForegroundColor Yellow
}

# Đăng ký tác vụ mới với quyền cao nhất (Run with highest privileges)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -User $User -RunLevel Highest -Settings $Settings

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " SUCCESS: Đã đăng ký GQN AI Bot vào Windows Task Scheduler!" -ForegroundColor Green
Write-Host " Tác vụ sẽ tự động chạy ngầm mỗi khi khởi động Windows." -ForegroundColor Green
Write-Host " Tên tác vụ: $TaskName" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
