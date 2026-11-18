# 便签小窗验收脚本（v1.2.1）
#
# 前置：已安装 v1.2.1 应用；可通过参数 -ApplicationPath 指定主程序，默认读取
#       %LOCALAPPDATA%\任务管理系统\task-management-desktop.exe。
# 流程：启动应用（若未运行）→ UIAutomation 登录 → 点击 Sticky Notes →
#       验证便签窗打开且主窗口不卡死 → Close 关闭 → 重新打开 → Esc 关闭 →
#       关闭主窗口并确认应用退出。
#
# 输出：[通过]/[失败] 明细与汇总；全部通过退出码 0，否则 1。

param(
    [string]$ApplicationPath = (Join-Path $env:LOCALAPPDATA '任务管理系统\task-management-desktop.exe'),
    [string]$Username = 'superAdmin',
    [string]$Password = 'SuperAdmin@123',
    [int]$WindowWaitSeconds = 120
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

$script:passed = 0
$script:failed = 0

function Assert-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')
    if ($Condition) {
        Write-Host ('[通过] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' }))
        $script:passed += 1
    } else {
        Write-Host ('[失败] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' }))
        $script:failed += 1
    }
}

function Get-AppWindows {
    param([int]$ProcessId)
    $rootElement = [System.Windows.Automation.AutomationElement]::RootElement
    $processCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $ProcessId)
    return $rootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $processCondition)
}

function Find-AppWindow {
    param([int]$ProcessId, [string]$NameLike)
    $windows = Get-AppWindows -ProcessId $ProcessId
    foreach ($window in $windows) {
        if ($window.Current.Name -like $NameLike) { return $window }
    }
    return $null
}

function Find-Descendant {
    param($Root, [string]$Name, [string]$ControlType = '')
    if (-not $Root) { return $null }
    $allElements = $Root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($element in $allElements) {
        if ($element.Current.Name -eq $Name -and (-not $ControlType -or $element.Current.ControlType.ProgrammaticName -eq ('ControlType.' + $ControlType))) {
            return $element
        }
    }
    return $null
}

function Wait-Until {
    param([scriptblock]$Condition, [int]$TimeoutSeconds = 20, [int]$IntervalMilliseconds = 500)
    for ($index = 0; $index -lt ($TimeoutSeconds * 1000 / $IntervalMilliseconds); $index++) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
    return $false
}

function Set-EditValue {
    param($Root, [string]$Name, [string]$Value)
    $edit = Find-Descendant -Root $Root -Name $Name -ControlType 'Edit'
    if (-not $edit) { return $false }
    $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Value)
    return $true
}

function Invoke-Button {
    param($Root, [string]$Name)
    $button = Find-Descendant -Root $Root -Name $Name -ControlType 'Button'
    if (-not $button) { return $false }
    $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    return $true
}

Write-Host '===== 便签小窗验收 ====='
Write-Host ('主程序：' + $ApplicationPath)
if (-not (Test-Path $ApplicationPath)) {
    Write-Output ('[失败] 未找到安装后的主程序：' + $ApplicationPath)
    exit 1
}

# 启动应用（若已有进程则复用）
$appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $appProcess) {
    Start-Process -FilePath $ApplicationPath | Out-Null
    $appProcess = $null
    $started = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
        $script:appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
        return $null -ne $script:appProcess
    }
    if (-not $started) {
        Write-Output '[失败] 应用进程未启动'
        exit 1
    }
    $appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
}
$processId = $appProcess.Id
Assert-Check '应用进程已启动' $true ('进程号：' + $processId)

# 等待主窗口
$mainWindow = $null
$mainReady = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    return $null -ne $script:mainWindow
}
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
Assert-Check '主窗口已显示' ($null -ne $mainWindow)
if (-not $mainWindow) { exit 1 }

# 登录（若显示登录表单）
if (Find-Descendant -Root $mainWindow -Name 'Username' -ControlType 'Edit') {
    Assert-Check '登录表单填写用户名' (Set-EditValue -Root $mainWindow -Name 'Username' -Value $Username)
    Assert-Check '登录表单填写密码' (Set-EditValue -Root $mainWindow -Name 'Password' -Value $Password)
    Start-Sleep -Milliseconds 300
    Assert-Check '点击登录按钮' (Invoke-Button -Root $mainWindow -Name 'Sign In')
    Start-Sleep -Seconds 4
}

# 等待登录完成，找到 Sticky Notes 按钮
$stickyButton = $null
$stickyButtonReady = Wait-Until -TimeoutSeconds 40 -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    $script:stickyButton = Find-Descendant -Root $script:mainWindow -Name 'Sticky Notes' -ControlType 'Button'
    return $null -ne $script:stickyButton
}
$stickyButton = Find-Descendant -Root (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*') -Name 'Sticky Notes' -ControlType 'Button'
Assert-Check '主窗口已登录并显示 Sticky Notes 入口' ($null -ne $stickyButton)
if (-not $stickyButton) { exit 1 }

# 打开便签窗并验证主窗口未卡死
$stickyButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
$stickyWindow = $null
$stickyOpened = Wait-Until -TimeoutSeconds 20 -Condition {
    $script:stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
    return $null -ne $script:stickyWindow
}
$stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
Assert-Check '便签窗口已打开' ($null -ne $stickyWindow) $(if ($stickyWindow) { '标题：' + $stickyWindow.Current.Name } else { '' })
Assert-Check '便签窗标题正确' ($null -ne (Find-Descendant -Root $stickyWindow -Name 'Sticky To-dos' -ControlType 'Text'))
Assert-Check '便签窗加载完成（出现 Close 按钮）' ($null -ne (Find-Descendant -Root $stickyWindow -Name 'Close' -ControlType 'Button'))

# 主窗口仍响应：重新找到主窗口并读取按钮
$mainWindowAfterOpen = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
$mainStillResponsive = $null -ne $mainWindowAfterOpen -and $null -ne (Find-Descendant -Root $mainWindowAfterOpen -Name 'Sticky Notes' -ControlType 'Button')
Assert-Check '打开便签窗后主窗口未卡死' $mainStillResponsive

# 点击 Close 关闭
$closeButton = Find-Descendant -Root $stickyWindow -Name 'Close' -ControlType 'Button'
if ($closeButton) { $closeButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
$closed = Wait-Until -TimeoutSeconds 20 -Condition {
    return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*')
}
Assert-Check '点击 Close 后便签窗口已关闭' $closed
Assert-Check '关闭便签后主窗口仍存在' ($null -ne (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'))

# 重新打开 → Esc 关闭
if ($stickyButton) {
    $mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    $stickyButton = Find-Descendant -Root $mainWindow -Name 'Sticky Notes' -ControlType 'Button'
    if ($stickyButton) { $stickyButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
}
$reopened = Wait-Until -TimeoutSeconds 20 -Condition {
    return $null -ne (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*')
}
Assert-Check '便签窗口可重复打开' $reopened
$stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
if ($stickyWindow) {
    $stickyWindow.SetFocus()
    Start-Sleep -Milliseconds 800
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
}
$escClosed = Wait-Until -TimeoutSeconds 20 -Condition {
    return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*')
}
Assert-Check '按 Esc 可关闭便签窗口' $escClosed

# 关闭主窗口并确认应用退出
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
if ($mainWindow) {
    $mainWindow.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close()
}
$appExited = Wait-Until -TimeoutSeconds 30 -Condition {
    return $null -eq (Get-Process -Id $processId -ErrorAction SilentlyContinue)
}
Assert-Check '关闭主窗口后应用正常退出' $appExited

Write-Host ''
Write-Host '================ 便签小窗验收结果汇总 ================'
Write-Host ('通过 ' + $script:passed + ' 项，失败 ' + $script:failed + ' 项')
if ($script:failed -eq 0) {
    Write-Host '便签小窗验收全部通过'
    exit 0
}
Write-Host '便签小窗验收存在失败项'
exit 1
