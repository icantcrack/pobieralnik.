# Buduje pobieralnik.lol dla Windows: PyInstaller + naprawa DLL OpenSSL.
# Użycie: powershell -File build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m PyInstaller --noconfirm --clean --windowed --onedir --name pobieralnik --icon assets/icon.ico --add-data "bin;bin" --add-data "assets;assets" --collect-data certifi main.py

# Krytyczne: PySide6 nadpisuje libssl/libcrypto Qt-owymi buildami — podmień na DLL-e Pythona
$dlls = python -c "import sysconfig, pathlib; print(pathlib.Path(sysconfig.get_path('stdlib')).parent / 'DLLs')"
Copy-Item "$dlls\libcrypto-3-x64.dll", "$dlls\libssl-3-x64.dll" "dist\pobieralnik\_internal\" -Force

# Szybki selftest sieci (Start-Process -Wait: exe jest windowed, & nie czeka na koniec)
if (Test-Path selftest_log.txt) { Remove-Item selftest_log.txt }
$p = Start-Process -FilePath ".\dist\pobieralnik\pobieralnik.exe" `
    -ArgumentList '--selftest', 'https://www.youtube.com/watch?v=aqz-KE-bpKQ' `
    -Wait -PassThru
Write-Host "selftest exit: $($p.ExitCode)"
$log = Get-Content selftest_log.txt -Raw
if ($log -match "KONIEC: done") { Write-Host "SELFTEST OK" } else { Write-Host "SELFTEST FAIL"; Write-Host $log; exit 1 }

Set-Location dist
tar -a -c -f pobieralnik-windows.zip pobieralnik
Write-Host "Gotowe: dist\pobieralnik-windows.zip"
