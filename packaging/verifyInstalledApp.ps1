#requires -Version 5.1
<#
.SYNOPSIS
    Windows 安装包安装后验收脚本：静默安装 → 启动 → 窗口显示 → 后端健康 → 账号登录 → 局域网访问 → 退出清理 → 卸载。
.DESCRIPTION
    用于自动化验证 release/ 下的 NSIS 安装包，覆盖任务验收要求的全部检查项，输出中文结果表格。
    检查项：
        1. 安装包静默安装（NSIS /S）成功；
        2. 安装目录存在桌面可执行文件与桌面快捷方式；
        3. 启动后主窗口显示（进程 MainWindowHandle 非零）；
        4. 后端 HTTP 服务健康检查通过（8765..8775 自动探测）；
        5. 内置超级用户 superAdmin 登录成功并可读取 /auth/me；
        6. 局域网地址可访问前端页面（http://<本机IP>:<端口>/）；
        7. 关闭窗口后应用与内置数据库/缓存进程优雅退出（端口释放）；
        8. 静默卸载成功。
.PARAMETER InstallerPath
    NSIS 安装包路径；缺省时使用 release/ 下最新的 *setup.exe。
.PARAMETER SkipInstall
    跳过安装步骤（验证已安装的应用）。
.PARAMETER SkipUninstall
    跳过卸载步骤（保留安装结果便于人工复测）。
.PARAMETER StartupTimeoutSeconds
    等待后端就绪与窗口显示的最长时间（秒），首次启动需初始化数据库，默认 240。
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File packaging/verifyInstalledApp.ps1
#>
param(
    [string]$InstallerPath = '',
    [switch]$SkipInstall,
    [switch]$SkipUninstall,
    [int]$StartupTimeoutSeconds = 240
)
$ErrorActionPreference = 'Stop'
$productName = '任务管理系统'
$superAdminUsername = 'superAdmin'
$superAdminPassword = 'SuperAdmin@123'
$checkResults = New-Object System.Collections.ArrayList
$appProcess = $null
# 窗口操作辅助函数（通过 Win32 API 精确定位类名为 Tauri Window 的主窗口并投递 WM_CLOSE）
. (Join-Path $PSScriptRoot 'verifyInstalledAppWindow.ps1')
function Add-CheckResult {
    <#
    .SYNOPSIS
        记录并输出单项验收结果。
    #>
    param([string]$Name, [bool]$Passed, [string]$Detail = '')
    $resultText = if ($Passed) { '通过' } else { '失败' }
    $resultColor = if ($Passed) { 'Green' } else { 'Red' }
    [void]$checkResults.Add([PSCustomObject]@{ 检查项 = $Name; 结果 = $resultText; 详情 = $Detail })
    Write-Host ('[' + $resultText + '] ' + $Name + '  ' + $Detail) -ForegroundColor $resultColor
}
function Wait-Until {
    <#
    .SYNOPSIS
        轮询等待条件成立，超时返回 $false。
    #>
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [int]$IntervalMilliseconds = 1000
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            if (& $Condition) { return $true }
        } catch {
            # 探测过程中的连接异常视为条件未满足
        }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
    return $false
}
function Get-InstalledExecutablePath {
    <#
    .SYNOPSIS
        枚举常见安装目录，返回已安装的可执行文件路径（找不到返回 $null）。
    #>
    $candidateDirectories = @(
        (Join-Path $env:LOCALAPPDATA $productName),
        (Join-Path $env:LOCALAPPDATA ('Programs/' + $productName)),
        (Join-Path $env:ProgramFiles $productName),
        (Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) $productName)
    )
    foreach ($candidateDirectory in $candidateDirectories) {
        if (-not (Test-Path $candidateDirectory)) { continue }
        # 优先产品名，其次 Cargo 包名（Tauri 默认沿用 Cargo bin 名，安装后可能不是产品名）
        foreach ($candidateFileName in @(($productName + '.exe'), 'task-management-desktop.exe')) {
            $candidatePath = Join-Path $candidateDirectory $candidateFileName
            if (Test-Path $candidatePath) { return $candidatePath }
        }
        # 兜底：安装目录下任意非卸载器可执行文件（取体积最大者，避免误选辅助程序）
        $executableFiles = Get-ChildItem $candidateDirectory -File -Filter '*.exe' -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -ne 'uninstall.exe' } | Sort-Object Length -Descending
        if ($executableFiles) { return $executableFiles[0].FullName }
    }
    return $null
}
function Get-BackendHealthPort {
    <#
    .SYNOPSIS
        在 8765..8775 范围探测后端健康检查端口，返回第一个可用端口（找不到返回 0）。
    #>
    for ($port = 8765; $port -le 8775; $port++) {
        try {
            $healthResponse = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/api/v1/health') -TimeoutSec 2
            if ($healthResponse.status -eq 'ok' -and $healthResponse.database -eq 'connected') { return $port }
        } catch {
            continue
        }
    }
    return 0
}
function Get-LanIPv4Address {
    <#
    .SYNOPSIS
        获取本机用于局域网访问的 IPv4 地址（排除回环与自动配置地址）。
    #>
    $udpSocket = New-Object System.Net.Sockets.UdpClient
    try {
        $udpSocket.Connect('8.8.8.8', 80)
        return $udpSocket.Client.LocalEndPoint.Address.ToString()
    } catch {
        return $null
    } finally {
        $udpSocket.Close()
    }
}
function Invoke-JsonPost {
    <#
    .SYNOPSIS
        发送 JSON POST 请求并返回解析后的响应对象。
    #>
    param([string]$Uri, [string]$BodyText, [string]$BearerToken = '')
    $requestHeaders = @{ 'Content-Type' = 'application/json; charset=utf-8' }
    if ($BearerToken) { $requestHeaders['Authorization'] = 'Bearer ' + $BearerToken }
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($BodyText)
    return Invoke-RestMethod -Uri $Uri -Method Post -Headers $requestHeaders -Body $bodyBytes -TimeoutSec 20
}
# ===== 1. 安装 =====
Write-Host ''
Write-Host '===== [1/8] 静默安装 ====='
if (-not $SkipInstall) {
    if (-not $InstallerPath) {
        $InstallerPath = Get-ChildItem (Join-Path (Split-Path -Parent $PSScriptRoot) 'release') -Filter '*setup.exe' -File |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $InstallerPath -or -not (Test-Path $InstallerPath)) {
        Add-CheckResult -Name '安装包存在' -Passed $false -Detail ('未找到安装包：' + $InstallerPath)
        exit 1
    }
    Write-Host ('安装包：' + $InstallerPath + '（' + [math]::Round((Get-Item $InstallerPath).Length / 1MB, 1) + ' MB）')
    $installProcess = Start-Process -FilePath $InstallerPath -ArgumentList '/S' -Wait -PassThru
    Add-CheckResult -Name '静默安装' -Passed ($installProcess.ExitCode -eq 0) -Detail ('安装程序退出码：' + $installProcess.ExitCode)
    Start-Sleep -Seconds 3
} else {
    Add-CheckResult -Name '静默安装' -Passed $true -Detail '已跳过（-SkipInstall）'
}
# ===== 2. 安装产物 =====
Write-Host ''
Write-Host '===== [2/8] 检查安装产物 ====='
$installedExecutablePath = Get-InstalledExecutablePath
Add-CheckResult -Name '安装后可执行文件存在' -Passed ($null -ne $installedExecutablePath) -Detail ([string]$installedExecutablePath)
if ($null -eq $installedExecutablePath) { exit 1 }
$installDirectory = Split-Path -Parent $installedExecutablePath
$resourcesDirectory = Join-Path $installDirectory 'resources'
$desktopShortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) ($productName + '.lnk')
Add-CheckResult -Name '桌面快捷方式存在' -Passed (Test-Path $desktopShortcutPath) -Detail $desktopShortcutPath
Add-CheckResult -Name '内置后端可执行文件存在' -Passed (Test-Path (Join-Path $resourcesDirectory 'backend/runServer.exe')) -Detail (Join-Path $resourcesDirectory 'backend')
Add-CheckResult -Name '便携 MariaDB 资源存在' -Passed (Test-Path (Join-Path $resourcesDirectory 'runtime/mariadb/bin/server.dll')) -Detail (Join-Path $resourcesDirectory 'runtime/mariadb')
Add-CheckResult -Name '便携 Redis 资源存在' -Passed (Test-Path (Join-Path $resourcesDirectory 'runtime/redis/redis-server.exe')) -Detail (Join-Path $resourcesDirectory 'runtime/redis')
# ===== 3. 启动应用 =====
Write-Host ''
Write-Host '===== [3/8] 启动应用 ====='
$appProcess = Start-Process -FilePath $installedExecutablePath -PassThru
Add-CheckResult -Name '应用进程已启动' -Passed ($null -ne $appProcess) -Detail ('进程号：' + $appProcess.Id)
# ===== 4. 窗口显示与后端健康 =====
Write-Host ''
Write-Host '===== [4/8] 等待窗口显示与后端就绪（首次启动需初始化数据库，最长 ' + $StartupTimeoutSeconds + ' 秒）====='
$windowShown = Wait-Until -TimeoutSeconds $StartupTimeoutSeconds -Condition {
    $script:tauriWindowHandle = Find-TauriMainWindow -ProcessId $appProcess.Id
    return ($script:tauriWindowHandle -ne [IntPtr]::Zero)
}
Add-CheckResult -Name '主窗口已显示' -Passed $windowShown -Detail ('窗口句柄：' + $script:tauriWindowHandle)
$backendPort = 0
$backendReady = Wait-Until -TimeoutSeconds $StartupTimeoutSeconds -Condition {
    $script:backendPort = Get-BackendHealthPort
    return ($script:backendPort -gt 0)
}
if (-not $backendReady) { $backendPort = Get-BackendHealthPort }
Add-CheckResult -Name '后端健康检查通过' -Passed ($backendPort -gt 0) -Detail ('端口：' + $backendPort)
if ($backendPort -le 0) {
    Write-Host '后端未就绪，输出桌面外壳日志：'
    $desktopLogPath = Join-Path $env:APPDATA 'TaskManagementSystem/logs/desktop.log'
    if (Test-Path $desktopLogPath) { Get-Content $desktopLogPath -Tail 30 }
    exit 1
}
$apiBaseUrl = 'http://127.0.0.1:' + $backendPort + '/api/v1'
# ===== 5. 默认账号登录 =====
Write-Host ''
Write-Host '===== [5/8] 默认账号登录 ====='
$loginBodyText = '{"username":"' + $superAdminUsername + '","password":"' + $superAdminPassword + '"}'
$loginSucceeded = $false
$loginDetail = ''
try {
    $loginResponse = Invoke-JsonPost -Uri ($apiBaseUrl + '/auth/login') -BodyText $loginBodyText
    $loginToken = $loginResponse.token
    $loginSucceeded = ($null -ne $loginToken -and $loginToken.Length -gt 20)
    $loginDetail = '用户：' + $loginResponse.user.user.username + '；token 长度：' + $loginToken.Length
    if ($loginSucceeded) {
        $currentUserResponse = Invoke-RestMethod -Uri ($apiBaseUrl + '/auth/me') -Headers @{ Authorization = 'Bearer ' + $loginToken } -TimeoutSec 20
        $loginDetail += '；/auth/me 角色：' + $currentUserResponse.user.globalRole
    }
} catch {
    $loginDetail = '登录异常：' + $_.Exception.Message
}
Add-CheckResult -Name 'superAdmin 登录成功' -Passed $loginSucceeded -Detail $loginDetail
# ===== 6. 局域网访问 =====
Write-Host ''
Write-Host '===== [6/8] 局域网访问 ====='
$lanAddress = Get-LanIPv4Address
$lanAccessPassed = $false
$lanDetail = '未获取到局域网地址'
if ($lanAddress) {
    try {
        $lanResponse = Invoke-WebRequest -Uri ('http://' + $lanAddress + ':' + $backendPort + '/') -UseBasicParsing -TimeoutSec 20
        $lanContentText = $lanResponse.Content
        $lanAccessPassed = ($lanResponse.StatusCode -eq 200 -and $lanContentText -match 'id="root"')
        $lanDetail = ('http://' + $lanAddress + ':' + $backendPort + '/ 状态码 ' + $lanResponse.StatusCode + '，前端入口已加载')
    } catch {
        $lanDetail = ('局域网访问失败：' + $_.Exception.Message)
    }
}
Add-CheckResult -Name '局域网访问前端页面' -Passed $lanAccessPassed -Detail $lanDetail
# ===== 7. 关闭应用并确认优雅退出 =====
Write-Host ''
Write-Host '===== [7/8] 关闭应用并确认进程清理 ====='
$tauriWindowHandleForClose = Find-TauriMainWindow -ProcessId $appProcess.Id
if ($tauriWindowHandleForClose -eq [IntPtr]::Zero) { $tauriWindowHandleForClose = $script:tauriWindowHandle }
$closeMessagePosted = [Win32WindowEnumerator]::PostMessage($tauriWindowHandleForClose, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
$processExited = Wait-Until -TimeoutSeconds 40 -IntervalMilliseconds 500 -Condition { return $appProcess.HasExited }
if (-not $processExited) {
    Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue
}
Add-CheckResult -Name '应用进程已退出' -Passed $processExited -Detail ('进程号：' + $appProcess.Id)
$portReleased = Wait-Until -TimeoutSeconds 45 -IntervalMilliseconds 1000 -Condition {
    return ((Get-BackendHealthPort) -eq 0)
}
Add-CheckResult -Name '后端端口已释放' -Passed $portReleased -Detail ('健康端口：' + $backendPort)
$desktopLogPath = Join-Path $env:APPDATA 'TaskManagementSystem/logs/desktop.log'
$gracefulShutdownLogged = $false
$backendLogPath = Join-Path $env:APPDATA 'TaskManagementSystem/logs/backend.log'
if (Test-Path $backendLogPath) {
    $backendLogText = Get-Content $backendLogPath -Tail 50 -Encoding UTF8
    $gracefulShutdownLogged = [bool]($backendLogText -match '托管运行时已关闭|Managed runtime has shut down')
}
Add-CheckResult -Name '后端记录优雅停机日志' -Passed $gracefulShutdownLogged -Detail $backendLogPath
# 确认内置后端、MariaDB、Redis 子进程全部退出（按命令行路径匹配本项目安装目录/数据目录）
$runtimeProcessesExited = Wait-Until -TimeoutSeconds 45 -IntervalMilliseconds 1000 -Condition {
    $runtimeProcessList = Get-CimInstance Win32_Process -Filter "Name='runServer.exe' OR Name='mariadbd.exe' OR Name='mysqld.exe' OR Name='redis-server.exe'" -ErrorAction SilentlyContinue
    $projectRuntimeProcesses = $runtimeProcessList | Where-Object {
        $processCommandLine = [string]$_.CommandLine
        return ($processCommandLine -match [regex]::Escape($installDirectory)) -or ($processCommandLine -match 'TaskManagementSystem')
    }
    return ($null -eq $projectRuntimeProcesses -or @($projectRuntimeProcesses).Count -eq 0)
}
Add-CheckResult -Name '内置后端/数据库/缓存进程已退出' -Passed $runtimeProcessesExited -Detail 'runServer.exe、mariadbd.exe/mysqld.exe、redis-server.exe'
# ===== 8. 卸载 =====
Write-Host ''
Write-Host '===== [8/8] 静默卸载 ====='
if (-not $SkipUninstall) {
    $uninstallerPath = Join-Path $installDirectory 'uninstall.exe'
    if (Test-Path $uninstallerPath) {
        $uninstallProcess = Start-Process -FilePath $uninstallerPath -ArgumentList '/S' -Wait -PassThru
        Start-Sleep -Seconds 5
        $uninstalled = -not (Test-Path $installedExecutablePath)
        Add-CheckResult -Name '静默卸载成功' -Passed ($uninstalled -and $uninstallProcess.ExitCode -eq 0) -Detail ('卸载程序退出码：' + $uninstallProcess.ExitCode)
    } else {
        Add-CheckResult -Name '静默卸载成功' -Passed $false -Detail ('未找到卸载程序：' + $uninstallerPath)
    }
} else {
    Add-CheckResult -Name '静默卸载成功' -Passed $true -Detail '已跳过（-SkipUninstall）'
}
# ===== 汇总 =====
Write-Host ''
Write-Host '================ 验收结果汇总 ================'
$checkResults | Format-Table -AutoSize | Out-String | Write-Host
$failedCount = ($checkResults | Where-Object { $_.结果 -eq '失败' }).Count
Write-Host ('通过 ' + ($checkResults.Count - $failedCount) + ' 项，失败 ' + $failedCount + ' 项')
if ($failedCount -gt 0) { exit 1 }
Write-Host '全部检查项通过'
exit 0