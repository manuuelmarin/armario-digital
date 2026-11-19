param([Parameter(Mandatory=$true)][string]$Folder)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [Windows.Automation.AutomationElement]::RootElement
$children = [Windows.Automation.TreeScope]::Children
$tree = [Windows.Automation.TreeScope]::Descendants
function ByProperty($property, $value) {
  return New-Object Windows.Automation.PropertyCondition($property, $value)
}
$class = [Windows.Automation.AutomationElement]::ClassNameProperty
$type = [Windows.Automation.AutomationElement]::ControlTypeProperty
$name = [Windows.Automation.AutomationElement]::NameProperty
$window = $null
$until = [DateTime]::UtcNow.AddSeconds(30)
while (!$window -and [DateTime]::UtcNow -lt $until) {
  foreach ($candidate in $root.FindAll($children, (ByProperty $class '#32770'))) {
    $proc = Get-Process -Id $candidate.Current.ProcessId -ErrorAction SilentlyContinue
    if ($proc.ProcessName -in @('chrome','msedge')) { $window=$candidate; break }
  }
  if (!$window) { Start-Sleep -Milliseconds 250 }
}
if (!$window) { throw 'No se encontró el selector nativo de carpetas en el escritorio del runner.' }
$edits = $window.FindAll($tree,(ByProperty $type ([Windows.Automation.ControlType]::Edit)))
$folderBox = $edits | Where-Object {$_.Current.Name -match 'Folder|Carpeta'} | Select-Object -Last 1
if (!$folderBox) { $folderBox = $edits | Select-Object -Last 1 }
if (!$folderBox) { throw 'El selector no expuso su campo de carpeta.' }
$folderBox.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).SetValue($Folder)
$buttons = $window.FindAll($tree,(ByProperty $type ([Windows.Automation.ControlType]::Button)))
$select = $buttons | Where-Object {$_.Current.Name -match '^(Select Folder|Seleccionar carpeta|Open|Abrir)$'} | Select-Object -First 1
if (!$select) { throw 'No se encontró el botón de selección.' }
$select.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
# Chrome/Edge may show a separate browser-owned access prompt.
$until = [DateTime]::UtcNow.AddSeconds(8)
while ([DateTime]::UtcNow -lt $until) {
  foreach ($browser in $root.FindAll($children,(ByProperty $class 'Chrome_WidgetWin_1'))) {
    foreach ($label in @('Allow','Allow this time','Allow on every visit','Edit files','Permitir','Editar archivos','View files')) {
      $allow = $browser.FindFirst($tree,(ByProperty $name $label))
      if ($allow -and $allow.Current.ControlType -eq [Windows.Automation.ControlType]::Button) {
        $allow.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
      }
    }
  }
  Start-Sleep -Milliseconds 300
}
