$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Mi Armario Digital.lnk'))
$link.TargetPath = Join-Path $root '.venv\Scripts\python.exe'
$link.Arguments = '"' + (Join-Path $root 'run.py') + '" --reopen'
$link.WorkingDirectory = $root
$link.IconLocation = (Join-Path $root 'armario\static\armario.ico') + ',0'
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = 'Elige tu icono o pulsa Cancelar para usar el de Armario Digital'
$dialog.Filter = 'Iconos (*.ico)|*.ico'
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
    $link.IconLocation = $dialog.FileName + ',0'
}
$dialog.Dispose()
$link.Save()
