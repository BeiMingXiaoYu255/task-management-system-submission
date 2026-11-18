#requires -Version 5.1
<#
.SYNOPSIS
    v1.2.2 桌面端新样式确认：Toast 顶部位置（下移至顶栏下方 76px）与便签小窗头部两行布局/计数不换行。

.DESCRIPTION
    前置：已安装 v1.2.2 应用（verifyInstalledApp.ps1 -SkipUninstall 之后执行）。
    流程：启动应用 → UIA 登录 → 点击 LAN Address 触发 Toast，按 UIA 包围盒校验 Toast 顶部明显位于顶栏下方；
          再点击 Sticky Notes 打开便签窗，校验 Sticky To-dos 标题与计数同一行、计数不换行且完整显示、
          Refresh/Main Window/Close 三按钮同行且位于标题行下方（两行布局）、Close 完整可见。
    输出：[通过]/[失败] 明细与汇总；全部通过退出码 0，否则 1。
#>
param(
    [string]$ApplicationPath = (Join-Path $env:LOCALAPPDATA '任务管理系统\task-management-desktop.exe'),
    [string]$Username = 'superAdmin',
    [string]$Password = 'SuperAdmin@123',
    [int]$WindowWaitSeconds = 120
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$script:passed = 0
$script:failed = 0

function Assert-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')
    if ($Condition) { Write-Host ('[通过] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' })); $script:passed += 1 }
    else { Write-Host ('[失败] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' })); $script:failed += 1 }
}

function Get-AppWindows {
    param([int]$ProcessId)
    $rootElement = [System.Windows.Automation.AutomationElement]::RootElement
    $processCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $ProcessId)
    return $rootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $processCondition)
}

function Find-AppWindow {
    param([int]$ProcessId, [string]$NameLike)
    foreach ($window in (Get-AppWindows -ProcessId $ProcessId)) {
        if ($window.Current.Name -like $NameLike) { return $window }
    }
    return $null
}

function Get-Descendants {
    param($Root)
    if (-not $Root) { return @() }
    return @($Root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition))
}

function Find-TextByNamePattern {
    param($Root, [string]$NamePattern)
    foreach ($element in (Get-Descendants -Root $Root)) {
        if ($element.Current.Name -match $NamePattern) { return $element }
    }
    return $null
}

function Find-ButtonByName {
    param($Root, [string]$Name, [switch]$NameLike)
    foreach ($element in (Get-Descendants -Root $Root)) {
        if ($element.Current.ControlType.ProgrammaticName -ne 'ControlType.Button') { continue }
        $elementName = $element.Current.Name
        if ($NameLike -and $elementName -like $Name) { return $element }
        if (-not $NameLike -and $elementName -eq $Name) { return $element }
    }
    return $null
}

function Find-EditByName {
    param($Root, [string]$Name)
    foreach ($element in (Get-Descendants -Root $Root)) {
        if ($element.Current.ControlType.ProgrammaticName -eq 'ControlType.Edit' -and $element.Current.Name -eq $Name) { return $element }
    }
    return $null
}

function Wait-Until {
    param([scriptblock]$Condition, [int]$TimeoutSeconds = 30, [int]$IntervalMilliseconds = 400)
    for ($index = 0; $index -lt ($TimeoutSeconds * 1000 / $IntervalMilliseconds); $index++) {
        try { if (& $Condition) { return $true } } catch { }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
    return $false
}

function Set-EditValue {
    param($Edit, [string]$Value)
    if (-not $Edit) { return $false }
    $Edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Value)
    return $true
}

function Invoke-Element {
    param($Element)
    if (-not $Element) { return $false }
    $Element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    return $true
}

function Get-Rect {
    param($Element)
    if (-not $Element) { return $null }
    return $Element.Current.BoundingRectangle
}

Write-Host '===== v1.2.2 桌面端新样式确认 ====='
if (-not (Test-Path $ApplicationPath)) { Write-Host ('[失败] 未找到安装后的主程序：' + $ApplicationPath); exit 1 }

if (-not (Get-Process task-management-desktop -ErrorAction SilentlyContinue)) { Start-Process -FilePath $ApplicationPath | Out-Null }
$appStarted = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
    return $null -ne (Get-Process task-management-desktop -ErrorAction SilentlyContinue)
}
$appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
Assert-Check '应用进程已启动' ($null -ne $appProcess -and $appStarted) ('进程号：' + $(if ($appProcess) { $appProcess.Id } else { '无' }))
if (-not $appProcess) { exit 1 }
$processId = $appProcess.Id

$mainWindowFound = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    return $null -ne $script:mainWindow
}
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
Assert-Check '主窗口已显示' ($null -ne $mainWindow)
if (-not $mainWindow) { exit 1 }

# UIA 登录（登录表单存在时）
$usernameEdit = Find-EditByName -Root $mainWindow -Name 'Username'
if ($usernameEdit) {
    [void](Set-EditValue -Edit $usernameEdit -Value $Username)
    [void](Set-EditValue -Edit (Find-EditByName -Root $mainWindow -Name 'Password') -Value $Password)
    Start-Sleep -Milliseconds 300
    [void](Invoke-Element -Element (Find-ButtonByName -Root $mainWindow -Name 'Sign In'))
    Start-Sleep -Seconds 4
}

# ===== Toast 顶部位置校验 =====
$copyButton = $null
$dashboardReady = Wait-Until -TimeoutSeconds 40 -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    $script:copyButton = Find-ButtonByName -Root $script:mainWindow -Name 'LAN Address*' -NameLike
    return $null -ne $script:copyButton
}
$copyButton = Find-ButtonByName -Root (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*') -Name 'LAN Address*' -NameLike
Assert-Check '主窗口已登录并显示 LAN Address 按钮' ($null -ne $copyButton) $(if ($copyButton) { '按钮名称：' + $copyButton.Current.Name } else { '未找到（可能登录未完成）' })
if (-not $copyButton) { Write-Host '无法触发 Toast，后续检查跳过'; exit 1 }

[void](Invoke-Element -Element $copyButton)
$toastElement = $null
$toastAppeared = Wait-Until -TimeoutSeconds 8 -IntervalMilliseconds 250 -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    $script:toastElement = Find-TextByNamePattern -Root $script:mainWindow -NamePattern 'LAN address copied|Copy failed|Failed to get the LAN address'
    return $null -ne $script:toastElement
}
$toastElement = Find-TextByNamePattern -Root (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*') -NamePattern 'LAN address copied|Copy failed|Failed to get the LAN address'
Assert-Check '操作后出现 Toast 提示' $toastAppeared $(if ($toastElement) { '内容：' + $toastElement.Current.Name } else { '' })
if ($toastElement) {
    $currentMainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    $mainWindowRect = Get-Rect -Element $currentMainWindow
    $toastRect = Get-Rect -Element $toastElement
    $copyButtonRect = Get-Rect -Element $copyButton
    $toastOffsetFromWindowTop = [math]::Round($toastRect.Top - $mainWindowRect.Top, 1)
    Assert-Check 'Toast 下移后位于窗口顶部下方' ($toastOffsetFromWindowTop -ge 90) ('相对主窗口顶部偏移 ' + $toastOffsetFromWindowTop + ' px（旧实现约 20px，新实现约 76px + 标题栏 + DPI 缩放）')
    Assert-Check 'Toast 位于顶栏按钮区域下方（不再遮挡顶栏）' ($toastRect.Top -ge ($copyButtonRect.Top + 2)) ('Toast.Top=' + [math]::Round($toastRect.Top, 1) + '；顶栏按钮 Bottom=' + [math]::Round($copyButtonRect.Bottom, 1))
    Assert-Check 'Toast 完整位于窗口水平范围内' ($toastRect.Right -le ($mainWindowRect.Right - 2)) ('Toast.Right=' + [math]::Round($toastRect.Right, 1) + '；窗口.Right=' + [math]::Round($mainWindowRect.Right, 1))
}

# ===== 便签小窗头部布局校验 =====
$stickyButton = Find-ButtonByName -Root (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*') -Name 'Sticky Notes'
Assert-Check '主窗口存在打开便签窗按钮' ($null -ne $stickyButton)
[void](Invoke-Element -Element $stickyButton)
$stickyOpened = Wait-Until -TimeoutSeconds 20 -Condition {
    $script:stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
    return $null -ne $script:stickyWindow
}
$stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
Assert-Check '便签窗口已打开' ($null -ne $stickyWindow)
if ($stickyWindow) {
    $stickyWindowRect = Get-Rect -Element $stickyWindow
    $titleElement = Find-TextByNamePattern -Root $stickyWindow -NamePattern '^Sticky To-dos$'
    $countElement = Find-TextByNamePattern -Root $stickyWindow -NamePattern '(?i)items$'
    $countNumberElement = Find-TextByNamePattern -Root $stickyWindow -NamePattern '^\d+$'
    $refreshButton = Find-ButtonByName -Root $stickyWindow -Name 'Refresh'
    $mainWindowButton = Find-ButtonByName -Root $stickyWindow -Name 'Main Window'
    $closeButton = Find-ButtonByName -Root $stickyWindow -Name 'Close'
    Assert-Check '便签头部包含 Sticky To-dos 标题' ($null -ne $titleElement)
    Assert-Check '便签头部包含计数（items 单位）' ($null -ne $countElement) $(if ($countElement) { '计数单位：' + $countElement.Current.Name.Trim() } else { '' })
    Assert-Check '便签头部包含计数值（数字）' ($null -ne $countNumberElement) $(if ($countNumberElement) { '计数值：' + $countNumberElement.Current.Name } else { '' })
    Assert-Check '便签头部包含 Refresh/Main Window/Close 按钮' ($null -ne $refreshButton -and $null -ne $mainWindowButton -and $null -ne $closeButton)
    if ($titleElement -and $countElement) {
        $titleRect = Get-Rect -Element $titleElement
        $countRect = Get-Rect -Element $countElement
        $sameRowTolerance = 8
        Assert-Check '便签标题与计数位于同一行' ([math]::Abs($titleRect.Top - $countRect.Top) -le $sameRowTolerance) ('标题.Top=' + [math]::Round($titleRect.Top, 1) + '；计数.Top=' + [math]::Round($countRect.Top, 1))
        Assert-Check '计数不换行且完整显示在窗口内' ($countRect.Right -le ($stickyWindowRect.Right - 2) -and $countRect.Height -lt 40) ('计数.Right=' + [math]::Round($countRect.Right, 1) + '；窗口.Right=' + [math]::Round($stickyWindowRect.Right, 1) + '；计数高度=' + [math]::Round($countRect.Height, 1))
        if ($countNumberElement) {
            $countNumberRect = Get-Rect -Element $countNumberElement
            Assert-Check '计数值与计数单位同一行（计数整体不换行）' ([math]::Abs($countNumberRect.Top - $countRect.Top) -le $sameRowTolerance -and $countNumberRect.Left -le $countRect.Left) ('数字.Top=' + [math]::Round($countNumberRect.Top, 1) + '；单位.Top=' + [math]::Round($countRect.Top, 1))
        }
        if ($refreshButton -and $mainWindowButton -and $closeButton) {
            $refreshRect = Get-Rect -Element $refreshButton
            $mainWindowRectInSticky = Get-Rect -Element $mainWindowButton
            $closeRect = Get-Rect -Element $closeButton
            $buttonRowTops = @($refreshRect.Top, $mainWindowRectInSticky.Top, $closeRect.Top)
            $buttonRowMax = ($buttonRowTops | Measure-Object -Maximum).Maximum
            $buttonRowMin = ($buttonRowTops | Measure-Object -Minimum).Minimum
            Assert-Check 'Refresh/Main Window/Close 三按钮同行' (($buttonRowMax - $buttonRowMin) -le 8) ('按钮行 Top 差异 ' + [math]::Round($buttonRowMax - $buttonRowMin, 1) + ' px')
            Assert-Check '按钮行位于标题行下方（头部两行布局）' ($refreshRect.Top -ge ($titleRect.Bottom - 2)) ('标题.Bottom=' + [math]::Round($titleRect.Bottom, 1) + '；按钮.Top=' + [math]::Round($refreshRect.Top, 1))
            Assert-Check 'Close 按钮完整显示在窗口内（不换行不溢出）' ($closeRect.Right -le ($stickyWindowRect.Right - 2)) ('Close.Right=' + [math]::Round($closeRect.Right, 1) + '；窗口.Right=' + [math]::Round($stickyWindowRect.Right, 1))
        }
    }
    [void](Invoke-Element -Element $closeButton)
    $stickyClosed = Wait-Until -TimeoutSeconds 20 -Condition { return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*') }
    Assert-Check '新样式检查后便签窗可正常关闭' $stickyClosed
}

# ===== 关闭主窗口并确认应用退出 =====
$mainWindowForClose = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
if ($mainWindowForClose) { $mainWindowForClose.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close() }
$appExited = Wait-Until -TimeoutSeconds 40 -Condition { return $null -eq (Get-Process -Id $processId -ErrorAction SilentlyContinue) }
Assert-Check '关闭主窗口后应用正常退出' $appExited

Write-Host ''
Write-Host '================ v1.2.2 桌面端新样式确认结果 ================'
Write-Host ('通过 ' + $script:passed + ' 项，失败 ' + $script:failed + ' 项')
if ($script:failed -eq 0) { Write-Host '桌面端新样式确认全部通过'; exit 0 }
Write-Host '桌面端新样式确认存在失败项'; exit 1