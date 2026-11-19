param([Parameter(Mandatory=$true)][string]$Work, [switch]$Detach)
$ErrorActionPreference = 'Stop'
# Allocate a new, bounded VHD in the disposable test directory. Never format an existing disk.
$path = Join-Path $Work 'armario-test.vhd'
$script = Join-Path $Work 'volume.diskpart'
if ($Detach) {
  if (!(Test-Path -LiteralPath $path)) { return }
  @("select vdisk file=`"$path`"","detach vdisk") | Set-Content $script -Encoding ASCII
  diskpart /s $script | Out-Host
  return
}
if (Test-Path -LiteralPath $path) { throw 'El volumen de prueba ya existe.' }
$used = (Get-PSDrive -PSProvider FileSystem).Name
$letter = @('V','W','X','Y') | Where-Object { $_ -notin $used } | Select-Object -First 1
if (!$letter) { throw 'No hay letra libre para el volumen de prueba.' }
@("create vdisk file=`"$path`" maximum=64 type=expandable","select vdisk file=`"$path`"","attach vdisk","create partition primary","format fs=ntfs label=ARMARIO_QA quick","assign letter=$letter") | Set-Content $script -Encoding ASCII
diskpart /s $script | Out-Host
$volume=Get-Volume -DriveLetter $letter
if ($volume.FileSystemLabel -ne 'ARMARIO_QA' -or $volume.Size -gt 64MB) { throw 'No se pudo verificar el volumen temporal.' }
Write-Output ("ARMARIO_VOLUME="+$letter+":\")
