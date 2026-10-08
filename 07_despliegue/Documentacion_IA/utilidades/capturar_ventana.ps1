# Captura una ventana de Windows (aunque este tapada) usando PrintWindow.
# Uso:  powershell -ExecutionPolicy Bypass -File capturar_ventana.ps1 -Proceso PBIDesktop
param(
    [string]$Proceso = "PBIDesktop",
    [string]$Salida = "$PSScriptRoot\captura_ventana.png"
)

Add-Type -AssemblyName System.Drawing

$sig = @'
using System;
using System.Runtime.InteropServices;
public class CapturaVentana {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdcBlt, uint nFlags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
'@
Add-Type -TypeDefinition $sig

$procesos = Get-Process | Where-Object { $_.ProcessName -like "*$Proceso*" -and $_.MainWindowHandle -ne 0 }
if (-not $procesos) { Write-Error "No hay proceso '$Proceso' con ventana"; exit 1 }

foreach ($p in $procesos) {
    $h = $p.MainWindowHandle
    $r = New-Object CapturaVentana+RECT
    [void][CapturaVentana]::GetWindowRect($h, [ref]$r)
    $ancho = $r.Right - $r.Left
    $alto = $r.Bottom - $r.Top
    $bmp = New-Object System.Drawing.Bitmap $ancho, $alto
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [CapturaVentana]::PrintWindow($h, $hdc, 2)
    $g.ReleaseHdc($hdc)
    $g.Dispose()

    $destino = if ($procesos.Count -gt 1) { $Salida -replace "\.png$", "_$($p.Id).png" } else { $Salida }
    $bmp.Save($destino, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Output "titulo='$($p.MainWindowTitle)' ok=$ok ($ancho x $alto) -> $destino"
}
