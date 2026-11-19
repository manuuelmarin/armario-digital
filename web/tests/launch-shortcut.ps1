param([Parameter(Mandatory=$true)][string]$Channel)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ActiveWindow {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
"@
$root=[Windows.Automation.AutomationElement]::RootElement
$children=[Windows.Automation.TreeScope]::Children
$tree=[Windows.Automation.TreeScope]::Descendants
function By($property,$value) { return New-Object Windows.Automation.PropertyCondition($property,$value) }
$class=[Windows.Automation.AutomationElement]::ClassNameProperty
$name=[Windows.Automation.AutomationElement]::NameProperty
function WindowsForBrowser {
  foreach ($w in $root.FindAll($children,(By $class 'Chrome_WidgetWin_1'))) {
    $proc=Get-Process -Id $w.Current.ProcessId -ErrorAction SilentlyContinue
    if ($proc.ProcessName -eq $Channel) { $w }
  }
}
$before=@(WindowsForBrowser | ForEach-Object {$_.Current.NativeWindowHandle})
$dirs=@([Environment]::GetFolderPath('DesktopDirectory'),[Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('CommonDesktopDirectory'),[Environment]::GetFolderPath('CommonPrograms')) | Where-Object {$_ -and (Test-Path $_)}
$until=[DateTime]::UtcNow.AddSeconds(12)
$shortcut=$null
while (!$shortcut -and [DateTime]::UtcNow -lt $until) {
  $shortcut=Get-ChildItem -LiteralPath $dirs -Filter '*Armario*.lnk' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if (!$shortcut) {
    foreach($w in WindowsForBrowser) {
      $create=$w.FindFirst($tree,(By $name 'Create'))
      if ($create -and $create.Current.ControlType -eq [Windows.Automation.ControlType]::Button -and !$create.Current.IsOffscreen) {
        $create.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
      }
    }
    Start-Sleep -Milliseconds 350
  }
}
if (!$shortcut) {
  $app = Get-StartApps | Where-Object {$_.Name -match 'Armario'} | Select-Object -First 1
  if (!$app) {throw 'Windows no encuentra el acceso directo ni la aplicación instalada en Inicio.'}
  $shell=New-Object -ComObject WScript.Shell
  $desktop=[Environment]::GetFolderPath('DesktopDirectory')
  $desktopLink=$shell.CreateShortcut((Join-Path $desktop 'Mi Armario Digital.lnk'))
  $desktopLink.TargetPath=(Join-Path $env:SystemRoot 'explorer.exe')
  $desktopLink.Arguments='shell:AppsFolder\'+$app.AppID
  $desktopLink.Save()
  $shortcut=Get-Item -LiteralPath (Join-Path $desktop 'Mi Armario Digital.lnk')
  Write-Output 'Acceso creado desde la aplicación registrada en Inicio.'
}
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($shortcut.FullName)
Write-Output ('Acceso directo: '+$shortcut.Name+' '+$link.TargetPath+' '+$link.Arguments)
Start-Process -FilePath $shortcut.FullName
$until=[DateTime]::UtcNow.AddSeconds(35)
while ([DateTime]::UtcNow -lt $until) {
  foreach ($w in WindowsForBrowser) {
    if ($w.Current.Name -notmatch 'Armario') {continue}
    if ($w.Current.NativeWindowHandle -in $before -and $w.Current.NativeWindowHandle -ne [ActiveWindow]::GetForegroundWindow().ToInt32()) {continue}
    $demo=$w.FindFirst($tree,(By $name 'Probar la demo'))
    if (!$demo) {continue}
    $omnibox=$w.FindFirst($tree,(By ([Windows.Automation.AutomationElement]::AutomationIdProperty) 'addressEditBox'))
    $tabs=$w.FindFirst($tree,(By $name 'New Tab'))
    if ($omnibox -or $tabs) {continue}
    Write-Output ('Ventana independiente: '+$w.Current.Name)
    $demo.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
    $untilDemo=[DateTime]::UtcNow.AddSeconds(15)
    while ([DateTime]::UtcNow -lt $untilDemo) {
      foreach ($item in $w.FindAll($tree,[Windows.Automation.Condition]::TrueCondition)) {
        if ($item.Current.Name -match 'Camisa blanca') { Write-Output 'Catálogo ficticio abierto desde el icono.'; return }
      }
      Start-Sleep -Milliseconds 300
    }
    throw 'Se abrió la ventana instalada, pero la demo no cargó.'
  }
  Start-Sleep -Milliseconds 300
}
WindowsForBrowser | ForEach-Object {Write-Output ('Ventana observada: '+$_.Current.Name)}
throw 'El acceso no abrió una ventana nueva de Armario Digital.'
