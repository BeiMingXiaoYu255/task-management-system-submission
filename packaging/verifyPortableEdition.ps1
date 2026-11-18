# 便携版实机验收脚本（v1.2.1）
#
# 流程：解压 release/TaskManagementSystem-portable-1.2.1.zip → 清空应用数据模拟首次运行 →
#       启动便携版 → 等待主窗口与后端就绪 → UIAutomation 登录 → 打开 Sticky Notes 并验证
#       主窗口未卡死 → Close 关闭便签窗 → 关闭主窗口 → 确认进程清理 → 清理临时数据。
#
# 用法：powershell -ExecutionPolicy Bypass -File packaging/verifyPortableEdition.ps1
# 输出：[通过]/[失败] 明细与汇总；全部通过退出码 0。

param(
    [string]$PortableZipPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'release\TaskManagementSystem-portable-1.2.1.zip'),
    [string]$ApplicationDataDirectory = (Join-Path $env:APPDATA 'TaskManagementSystem'),
    [string]$InstallDataDirectory = (Join-Path $env:LOCALAPPDATA '任务管理系统'),
    [string]$Username = 'superAdmin',
    [string]$Password = 'SuperAdmin@123',
    [int]$StartupWaitSeconds = 180
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$script:passed = 0
$script:failed = 0
$extractDirectory = Join-Path $env:TEMP ('TaskManagementPortableVerify-' + [System.Guid]::NewGuid().ToString('N'))
$preexistingProcessIds = @(Get-Process runServer,mariadbd,mysqld,redis-server -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)

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
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, $ProcessId)
    return $rootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
}

function Find-AppWindow {
    param([int]$ProcessId, [string]$NameLike)
    foreach ($window in (Get-AppWindows -ProcessId $ProcessId)) {
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
    param([scriptblock]$Condition, [int]$TimeoutSeconds = 20)
    for ($index = 0; $index -lt $TimeoutSeconds * 2; $index++) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds 500
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

Write-Host '===== 便携版实机验收 ====='
Write-Host ('便携包：' + $PortableZipPath)
if (-not (Test-Path $PortableZipPath)) {
    Write-Output ('[失败] 便携包不存在：' + $PortableZipPath)
    exit 1
}

$appProcess = $null
try {
    # 解压并模拟首次运行
    New-Item -ItemType Directory -Force -Path $extractDirectory | Out-Null
    Expand-Archive -LiteralPath $PortableZipPath -DestinationPath $extractDirectory -Force
    $executablePath = (Get-ChildItem $extractDirectory -Recurse -Filter '任务管理系统.exe' | Select-Object -First 1).FullName
    Assert-Check '便携包解压后找到主程序' ($null -ne $executablePath) ([string]$executablePath)
    if (-not $executablePath) { exit 1 }
    foreach ($dataDirectory in @($ApplicationDataDirectory, $InstallDataDirectory)) {
        if (Test-Path $dataDirectory) { Remove-Item -Recurse -Force $dataDirectory -ErrorAction SilentlyContinue }
    }
    Assert-Check '主程序版本为 1.2.1' ((Get-Item $executablePath).VersionInfo.FileVersion -like '*1.2.1*')

    Start-Process -FilePath $executablePath | Out-Null
    $started = Wait-Until -TimeoutSeconds $StartupWaitSeconds -Condition {
        $script:appProcess = Get-Process | Where-Object { $_.MainWindowTitle -like '*Task Management System*' } | Select-Object -First 1
        return $null -ne $script:appProcess
    }
    $appProcess = Get-Process | Where-Object { $_.MainWindowTitle -like '*Task Management System*' } | Select-Object -First 1
    Assert-Check '便携版进程启动' ($null -ne $appProcess)
    if (-not $appProcess) { exit 1 }
    $processId = $appProcess.Id

    $mainWindow = $null
    $windowReady = Wait-Until -TimeoutSeconds $StartupWaitSeconds -Condition {
        $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
        return $null -ne $script:mainWindow
    }
    $mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    Assert-Check '便携版主窗口显示' ($null -ne $mainWindow)

    $healthOk = Wait-Until -TimeoutSeconds $StartupWaitSeconds -Condition {
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/v1/health' -UseBasicParsing -TimeoutSec 3
            return $response.StatusCode -eq 200
        } catch { return $false }
    }
    $healthContent = ''
    if ($healthOk) {
        $healthContent = (Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/v1/health' -UseBasicParsing -TimeoutSec 5).Content
    }
    Assert-Check '便携版后端健康检查' $healthOk $healthContent
    Assert-Check '便携版后端版本为 1.2.1' ($healthContent -like '*1.2.1*')

    # 登录并验证便签小窗
    if (Find-Descendant -Root $mainWindow -Name 'Username' -ControlType 'Edit') {
        Assert-Check '登录用户名填写' (Set-EditValue -Root $mainWindow -Name 'Username' -Value $Username)
        Assert-Check '登录密码填写' (Set-EditValue -Root $mainWindow -Name 'Password' -Value $Password)
        Start-Sleep -Milliseconds 300
        Assert-Check '点击 Sign In' (Invoke-Button -Root $mainWindow -Name 'Sign In')
        Start-Sleep -Seconds 4
    }
    $stickyButton = $null
    $stickyReady = Wait-Until -TimeoutSeconds 40 -Condition {
        $script:mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
        $script:stickyButton = Find-Descendant -Root $script:mainWindow -Name 'Sticky Notes' -ControlType 'Button'
        return $null -ne $script:stickyButton
    }
    $stickyButton = Find-Descendant -Root (Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*') -Name 'Sticky Notes' -ControlType 'Button'
    Assert-Check '登录成功并显示 Sticky Notes 入口' ($null -ne $stickyButton)
    if ($stickyButton) { $stickyButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }

    $stickyWindow = $null
    $stickyOpened = Wait-Until -TimeoutSeconds 20 -Condition {
        $script:stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
        return $null -ne $script:stickyWindow
    }
    $stickyWindow = Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*'
    Assert-Check '便签窗口打开' ($null -ne $stickyWindow)
    $mainAfterOpen = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    Assert-Check '打开便签后主窗口未卡死' ($null -ne $mainAfterOpen -and $null -ne (Find-Descendant -Root $mainAfterOpen -Name 'Sticky Notes' -ControlType 'Button'))
    $closeButton = Find-Descendant -Root $stickyWindow -Name 'Close' -ControlType 'Button'
    Assert-Check '便签窗 Close 按钮存在' ($null -ne $closeButton)
    if ($closeButton) { $closeButton.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
    $stickyClosed = Wait-Until -TimeoutSeconds 20 -Condition { return $null -eq (Find-AppWindow -ProcessId $processId -NameLike 'Sticky To-dos*') }
    Assert-Check '便签窗口关闭成功' $stickyClosed

    # 关闭主窗口
    $mainWindow = Find-AppWindow -ProcessId $processId -NameLike 'Task Management System*'
    if ($mainWindow) { $mainWindow.GetCurrentPattern([System.Windows.Automation.WindowPattern]::Pattern).Close() }
    $appExited = Wait-Until -TimeoutSeconds 40 -Condition { return $null -eq (Get-Process -Id $processId -ErrorAction SilentlyContinue) }
    Assert-Check '关闭主窗口后便携版正常退出' $appExited
    Start-Sleep -Seconds 3
    $newResidualProcesses = Get-Process runServer,mariadbd,mysqld,redis-server -ErrorAction SilentlyContinue |
        Where-Object { $preexistingProcessIds -notcontains $_.Id }
    Assert-Check '退出后无新增后端/数据库/缓存进程' ($newResidualProcesses.Count -eq 0) (($newResidualProcesses | Select-Object -ExpandProperty ProcessName) -join ',')
} finally {
    # 清理临时解压目录与应用数据（不删除用户文档，仅应用数据）
    if (Test-Path $extractDirectory) { Remove-Item -Recurse -Force $extractDirectory -ErrorAction SilentlyContinue }
    foreach ($dataDirectory in @($ApplicationDataDirectory, $InstallDataDirectory)) {
        if (Test-Path $dataDirectory) { Remove-Item -Recurse -Force $dataDirectory -ErrorAction SilentlyContinue }
    }
}

Write-Host ''
Write-Host '================ 便携版实机验收结果汇总 ================'
Write-Host ('通过 ' + $script:passed + ' 项，失败 ' + $script:failed + ' 项')
if ($script:failed -eq 0) {
    Write-Host '便携版实机验收全部通过'
    exit 0
}
Write-Host '便携版实机验收存在失败项'
exit 1
