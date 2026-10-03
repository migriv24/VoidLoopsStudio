# install_shortcut.ps1 — (re)create the "Void Loops Studio" desktop shortcut
# for the native build. The native VLS successor of the Python era's
# VoidLoops.bat + desktop icon. Run after the first build:
#   powershell -ExecutionPolicy Bypass -File native/install_shortcut.ps1
#
# The exe is self-contained (the GCC runtime is static-linked; only
# libvoidcore.dll rides beside it, and Windows finds a DLL in the exe's own
# directory), so the shortcut needs no PATH juggling — it points straight at
# the exe.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path   # native/
$exe  = Join-Path $root "build\bin\vls_native.exe"
$icon = Join-Path $root "assets\vls.ico"
$bin  = Join-Path $root "build\bin"

if (-not (Test-Path $exe)) {
    Write-Error "vls_native.exe not found — build first (cmake --build native/build)."
    exit 1
}

$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Void Loops Studio.lnk"
$ws  = New-Object -ComObject WScript.Shell
$sc  = $ws.CreateShortcut($lnk)
$sc.TargetPath       = $exe
$sc.WorkingDirectory = $bin
if (Test-Path $icon) { $sc.IconLocation = "$icon,0" }
$sc.Description       = "Void Loops Studio - native (node-based DAW on Void Maiz)"
$sc.WindowStyle      = 1
$sc.Save()

Write-Output "Desktop shortcut created: $lnk"
