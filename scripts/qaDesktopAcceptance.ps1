# 桌面端真人式 QA 验收脚本（已安装的 v1.2.1 应用）
#
# 驱动真实桌面应用：UIAutomation 登录 → 依次点击侧边栏页面并截图（视觉验收）→
# 切换深浅色主题并截图 → 打开便签小窗并截图、验证主窗口不卡死 → Close/Esc 关闭 →
# 打开管理后台并截图。应用保持运行，供后续 Web/LAN 验收继续使用。
#
# 用法：powershell -ExecutionPolicy Bypass -File scripts/qaDesktopAcceptance.ps1 -Username <user> -Password <pwd>

param(
    [string]$Username = 'superAdmin',
    [string]$Password = 'SuperAdmin@123',
    [string]$ScreenshotDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'docs\screenshots\qa-acceptance'),
    [int]$WindowWaitSeconds = 120
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$script:passed = 0
$script:failed = 0
$capturedScreenshots = New-Object System.Collections.Generic.List[string]

if (-not (Test-Path $ScreenshotDirectory)) { New-Item -ItemType Directory -Force -Path $ScreenshotDirectory | Out-Null }

function Assert-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')
    if ($Condition) { Write-Host ('[通过] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' })); $script:passed += 1 }
    else { Write-Host ('[失败] ' + $Name + $(if ($Detail) { '  ' + $Detail } else { '' })); $script:failed += 1 }
}

function Get-AppWindows {
    param([int]$ProcessId)
    $rootElement = [System.Windows.Automation.AutomationElement]::RootElement
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $ProcessId)
    return $rootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
}

function Find-AppWindow {
    param([int]$ProcessId, [string]$NameLike)
    foreach ($window in (Get-AppWindows -ProcessId $ProcessId)) { if ($window.Current.Name -like $NameLike) { return $window } }
    return $null
}

function Find-Descendant {
    param($Root, [string]$Name, [string]$ControlType = '')
    if (-not $Root) { return $null }
    $allElements = $Root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($element in $allElements) {
        if ($element.Current.Name -eq $Name -and (-not $ControlType -or $element.Current.ControlType.ProgrammaticName -eq ('ControlType.' + $ControlType))) { return $element }
    }
    return $null
}

function Wait-Until {
    param([scriptblock]$Condition, [int]$TimeoutSeconds = 20)
    for ($index = 0; $index -lt $TimeoutSeconds * 2; $index++) { if (& $Condition) { return $true }; Start-Sleep -Milliseconds 500 }
    return $false
}

function Invoke-Element {
    param($Element)
    if (-not $Element) { return $false }
    try { $Element.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true } catch { return $false }
}

function Set-EditValue {
    param($Root, [string]$Name, [string]$Value)
    $edit = Find-Descendant -Root $Root -Name $Name -ControlType 'Edit'
    if (-not $edit) { return $false }
    $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Value)
    return $true
}

function Capture-Window {
    param($Window, [string]$FileName)
    if (-not $Window) { return $false }
    $bounds = $Window.Current.BoundingRectangle
    if ($bounds.Width -le 0 -or $bounds.Height -le 0) { return $false }
    $width = [int]$bounds.Width
    $height = [int]$bounds.Height
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen([int]$bounds.X, [int]$bounds.Y, 0, 0, $bitmap.Size)
        $targetPath = Join-Path $ScreenshotDirectory $FileName
        $bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $capturedScreenshots.Add($targetPath)
        Write-Host ('[截图] ' + $FileName)
        return $true
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Open-NavPage {
    param($MainWindow, [int]$ProcessId, [string]$NavName, [string]$ScreenshotName, [string[]]$ExpectedTexts = @())
    $navButton = Find-Descendant -Root $MainWindow -Name $NavName -ControlType 'Button'
    if (-not $navButton) { $navButton = Find-Descendant -Root $MainWindow -Name $NavName }
    $clicked = Invoke-Element -Element $navButton
    Assert-Check ('点击侧边栏 ' + $NavName) $clicked
    if (-not $clicked) { return $false }
    Start-Sleep -Milliseconds 1200
    $freshWindow = Find-AppWindow -ProcessId $ProcessId -NameLike 'Task Management System*'
    $foundText = $true
    foreach ($expectedText in $ExpectedTexts) {
        $found = $null -ne (Find-Descendant -Root $freshWindow -Name $expectedText)
        if (-not $found) { $foundText = $false }
    }
    if ($ExpectedTexts.Count -gt 0) { Assert-Check ('页面 ' + $NavName + ' 内容渲染') $foundText }
    Capture-Window -Window $freshWindow -FileName $ScreenshotName | Out-Null
    return $true
}

Write-Host '===== 桌面端真人式 QA 验收 ====='
$appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $appProcess) {
    $exe = Join-Path $env:LOCALAPPDATA '任务管理系统\task-management-desktop.exe'
    Start-Process -FilePath $exe | Out-Null
    $started = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
        $script:appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
        return $null -ne $script:appProcess
    }
    $appProcess = Get-Process task-management-desktop -ErrorAction SilentlyContinue | Select-Object -First 1
}
Assert-Check '桌面应用进程存在' ($null -ne $appProcess)
if (-not $appProcess) { exit 1 }
$processId = $appProcess.Id

$mainWindow = $null
$windowReady = Wait-Until -TimeoutSeconds $WindowWaitSeconds -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    return $null -ne $script:mainWindow
}
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
Assert-Check '主窗口显示' ($null -ne $mainWindow)
if (-not $mainWindow) { exit 1 }

# 登录（若登录页）
if (Find-Descendant -Root $mainWindow -Name 'Username' -ControlType 'Edit') {
    Assert-Check '输入用户名' (Set-EditValue -Root $mainWindow -Name 'Username' -Value $Username)
    Assert-Check '输入密码' (Set-EditValue -Root $mainWindow -Name 'Password' -Value $Password)
    Start-Sleep -Milliseconds 300
    Assert-Check '点击 Sign In' (Invoke-Element -Element (Find-Descendant -Root $mainWindow -Name 'Sign In' -ControlType 'Button'))
    Start-Sleep -Seconds 4
}

$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
$loggedIn = Wait-Until -TimeoutSeconds 30 -Condition {
    $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    return ($null -ne (Find-Descendant -Root $script:mainWindow -Name 'Sticky Notes')) -or ($null -ne (Find-Descendant -Root $script:mainWindow -Name 'Teams'))
}
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
Assert-Check '登录成功（显示侧边栏与顶栏）' $loggedIn
Capture-Window -Window $mainWindow -FileName 'desktop-01-dashboard-light.png' | Out-Null

# 逐页导航 + 截图
$navPages = @(
    @{ Name = 'Dashboard'; File = 'desktop-02-dashboard.png'; Texts = @('Dashboard') },
    @{ Name = 'Teams'; File = 'desktop-03-teams.png'; Texts = @('My Teams') },
    @{ Name = 'To-dos'; File = 'desktop-04-todos.png'; Texts = @('My To-dos') },
    @{ Name = 'Tasks'; File = 'desktop-05-tasks.png'; Texts = @('Task Center') },
    @{ Name = 'Collaborations'; File = 'desktop-06-collaborations.png'; Texts = @('Collaboration Center') },
    @{ Name = 'Profile'; File = 'desktop-07-profile.png'; Texts = @('Profile') },
    @{ Name = 'Settings'; File = 'desktop-08-settings.png'; Texts = @('System Settings') }
)
foreach ($page in $navPages) { Open-NavPage -MainWindow $mainWindow -ProcessId $processId -NavName $page.Name -ScreenshotName $page.File -ExpectedTexts $page.Texts | Out-Null }

# 管理后台（仅管理员可见，superAdmin 有）
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
if (Find-Descendant -Root $mainWindow -Name 'Admin Console') {
    Open-NavPage -MainWindow $mainWindow -ProcessId $processId -NavName 'Admin Console' -ScreenshotName 'desktop-09-admin-console.png' -ExpectedTexts @('Admin Console') | Out-Null
} else {
    Write-Host '[跳过] 当前账号不显示 Admin Console（非全局管理员）'
}

# 主题切换（浅色 → 深色）
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
$darkModeButton = Find-Descendant -Root $mainWindow -Name 'Switch to dark mode' -ControlType 'Button'
Assert-Check '找到主题切换按钮' ($null -ne $darkModeButton)
if ($darkModeButton) {
    Invoke-Element -Element $darkModeButton | Out-Null
    Start-Sleep -Milliseconds 800
    $mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    Capture-Window -Window $mainWindow -FileName 'desktop-10-dark-mode.png' | Out-Null
    Assert-Check '切换为深色主题' ($null -ne (Find-Descendant -Root $mainWindow -Name 'Switch to light mode' -ControlType 'Button'))
    $lightModeButton = Find-Descendant -Root $mainWindow -Name 'Switch to light mode' -ControlType 'Button'
    if ($lightModeButton) { Invoke-Element -Element $lightModeButton | Out-Null; Start-Sleep -Milliseconds 800 }
}

# 便签小窗
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
$stickyButton = Find-Descendant -Root $mainWindow -Name 'Sticky Notes' -ControlType 'Button'
Assert-Check '找到 Sticky Notes 入口' ($null -ne $stickyButton)
if ($stickyButton) {
    Invoke-Element -Element $stickyButton | Out-Null
    $stickyWindow = $null
    $opened = Wait-Until -TimeoutSeconds 20 -Condition {
        $script:stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
        return $null -ne $script:stickyWindow
    }
    $stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
    Assert-Check '便签小窗打开' ($null -ne $stickyWindow)
    Assert-Check '打开便签后主窗口未卡死' ($null -ne (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'))
    if ($stickyWindow) { Capture-Window -Window $stickyWindow -FileName 'desktop-11-sticky-window.png' | Out-Null }
    $closeButton = Find-Descendant -Root $stickyWindow -Name 'Close' -ControlType 'Button'
    Assert-Check '便签窗 Close 按钮存在' ($null -ne $closeButton)
    if ($closeButton) { Invoke-Element -Element $closeButton | Out-Null }
    $closed = Wait-Until -TimeoutSeconds 20 -Condition { return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*') }
    Assert-Check '便签窗关闭' $closed
}

# 再次打开 + Esc 关闭
$mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
$stickyButton = Find-Descendant -Root $mainWindow -Name 'Sticky Notes' -ControlType 'Button'
if ($stickyButton) { Invoke-Element -Element $stickyButton | Out-Null }
$reopened = Wait-Until -TimeoutSeconds 20 -Condition { return $null -ne (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*') }
Assert-Check '便签窗可重复打开' $reopened
$stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
if ($stickyWindow) { $stickyWindow.SetFocus(); Start-Sleep -Milliseconds 800; [System.Windows.Forms.SendKeys]::SendWait('{ESC}') }
$escClosed = Wait-Until -TimeoutSeconds 20 -Condition { return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*') }
Assert-Check 'Esc 关闭便签窗' $escClosed

Write-Host ''
Write-Host '================ 桌面端 QA 验收结果 ================'
Write-Host ('通过 ' + $script:passed + ' 项，失败 ' + $script:failed + ' 项；截图 ' + $capturedScreenshots.Count + ' 张')
Write-Host ('截图目录：' + $ScreenshotDirectory)
if ($script:failed -eq 0) { Write-Host '桌面端 QA 验收全部通过'; exit 0 }
Write-Host '桌面端 QA 验收存在失败项'; exit 1
