$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Claude Bridge Bot.lnk")
$Shortcut.TargetPath = "C:\Users\lazymark2\Downloads\MateBot-Fixed\start_bot_hidden.vbs"
$Shortcut.WorkingDirectory = "C:\Users\lazymark2\Downloads\MateBot-Fixed"
$Shortcut.Save()
Write-Host "开机启动已设置完成！" -ForegroundColor Green
