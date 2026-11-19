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
Write-Output ('Interactive: '+[Environment]::UserInteractive+'; session: '+(Get-Process -Id $PID).SessionId)
$window = $null
$until = [DateTime]::UtcNow.AddSeconds(30)
while (!$window -and [DateTime]::UtcNow -lt $until) {
  foreach ($candidate in $root.FindAll($tree, (ByProperty $class '#32770'))) {
    $proc = Get-Process -Id $candidate.Current.ProcessId -ErrorAction SilentlyContinue
    if ($proc.ProcessName -in @('chrome','msedge')) { $window=$candidate; break }
  }
  if (!$window) { Start-Sleep -Milliseconds 250 }
}
if (!$window) { $root.FindAll($children,[Windows.Automation.Condition]::TrueCondition) | ForEach-Object {Write-Output ($_.Current.ClassName + ' | ' + $_.Current.Name)}; throw 'Selector nativo no accesible en este escritorio.' }
Add-Type -AssemblyName System.Windows.Forms
$editType = ByProperty $type ([Windows.Automation.ControlType]::Edit)
$buttonType = ByProperty $type ([Windows.Automation.ControlType]::Button)
$edits = $window.FindAll($tree,$editType)
$edits | ForEach-Object { Write-Output ('Edit: '+$_.Current.AutomationId+' '+$_.Current.Name) }
$buttons = $window.FindAll($tree,$buttonType)
$buttons | ForEach-Object { Write-Output ('Button: '+$_.Current.AutomationId+' '+$_.Current.Name) }
$edit = $edits | Where-Object {$_.Current.AutomationId -eq '1148' -or $_.Current.Name -match 'Folder|Carpeta'} | Select-Object -Last 1
if (!$edit) { throw 'No se ha encontrado el campo de carpeta.' }
$edit.SetFocus()
$edit.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern).SetValue($Folder)
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Start-Sleep -Milliseconds 700
# Depending on the shell version, Enter opens the directory or completes the picker.
try {
  $ok = $window.FindFirst($tree,(ByProperty ([Windows.Automation.AutomationElement]::AutomationIdProperty) '1'))
  if ($ok -and $ok.Current.IsEnabled) { $ok.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke() }
} catch [Windows.Automation.ElementNotAvailableException] { }
$seen = @{}
$until = [DateTime]::UtcNow.AddSeconds(13)
while ([DateTime]::UtcNow -lt $until) {
  foreach ($browser in $root.FindAll($children,[Windows.Automation.Condition]::TrueCondition)) {
    $proc = Get-Process -Id $browser.Current.ProcessId -ErrorAction SilentlyContinue
    if ($proc.ProcessName -notin @('chrome','msedge')) { continue }
    foreach ($control in $browser.FindAll($tree,$buttonType)) {
      try {
        $label = $control.Current.Name -replace '&',''
        if (!$label -or $control.Current.IsOffscreen) { continue }
        if (!$seen.ContainsKey($label)) { Write-Output ('Browser button: '+$label); $seen[$label]=$true }
        if ($label -match '^(Allow( .+)?|Edit files|View files|Save changes|Permitir( .+)?|Editar archivos)$') {
          $control.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern).Invoke()
        }
      } catch [Windows.Automation.ElementNotAvailableException] { }
    }
  }
  Start-Sleep -Milliseconds 350
}
