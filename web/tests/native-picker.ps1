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
# The shell's folder view is also a #32770 window, nested inside the actual picker.
# Target the outer Win32 window and use the same address-bar keys as a desktop user.
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class PickerWindow {
    [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flag);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
}
"@
$outer = [PickerWindow]::GetAncestor([IntPtr]$window.Current.NativeWindowHandle,2)
if (!$outer -or $outer -eq [IntPtr]::Zero) { throw 'Ventana de selector no encontrada.' }
$dialog = [Windows.Automation.AutomationElement]::FromHandle($outer)
Write-Output ('Selector: '+$dialog.Current.Name+' '+$dialog.Current.ClassName)
[void][PickerWindow]::SetForegroundWindow($outer)
Start-Sleep -Milliseconds 500
if ([PickerWindow]::GetForegroundWindow() -ne $outer) { throw 'El selector no tiene el foco del escritorio.' }
[System.Windows.Forms.SendKeys]::SendWait('^l')
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait($Folder)
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Start-Sleep -Milliseconds 750
if ([PickerWindow]::IsWindowVisible($outer)) {
  $ok = [PickerWindow]::GetDlgItem($outer,1)
  if ($ok -ne [IntPtr]::Zero) { [void][PickerWindow]::PostMessage($ok,0x00f5,[IntPtr]::Zero,[IntPtr]::Zero) }
  else { [System.Windows.Forms.SendKeys]::SendWait('%s') }
}
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
