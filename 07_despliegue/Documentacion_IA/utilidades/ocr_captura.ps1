# Lee el texto visible de una imagen (captura de pantalla) con el OCR de Windows.
# Uso:  powershell -ExecutionPolicy Bypass -File ocr_captura.ps1 -Imagen "ruta\captura_ventana.png"
param(
    [string]$Imagen = "$PSScriptRoot\captura_ventana.png"
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

if (-not (Test-Path $Imagen)) { Write-Error "No existe la imagen: $Imagen"; exit 1 }

$archivo = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $Imagen).Path)) ([Windows.Storage.StorageFile])
$flujo = Await ($archivo.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($flujo)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

$motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($null -eq $motor) { $motor = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language "es")) }
if ($null -eq $motor) { Write-Error "No hay motor OCR disponible"; exit 1 }

$resultado = Await ($motor.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
($resultado.Lines | ForEach-Object { $_.Text }) -join " | "
