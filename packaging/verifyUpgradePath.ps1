#requires -Version 5.1
<#
.SYNOPSIS
    Windows 安装包升级路径验收：旧版安装并生成数据 → 新版覆盖安装 → 数据库增量迁移、旧数据保留、新功能冒烟。

.DESCRIPTION
    验收流程：
        1. 清理应用数据，静默安装旧版（默认 release/任务管理系统_1.0.0_x64-setup.exe）并首次启动；
        2. 旧版中创建标记数据：注册 migrationDemoUser、创建团队 迁移验证团队-v1.0；
        3. 关闭旧版 → 静默覆盖安装新版（默认 release/任务管理系统_1.2.2_x64-setup.exe）；
        4. 启动新版：health 版本=1.2.2、backend.log 出现数据库结构升级日志；
        5. 旧数据保留校验：标记用户可登录、标记团队仍在、用户数不减少；
        6. 新功能冒烟：/api/v1/ai/status 返回 provider/dispatchMode；
        7. 再次启动验证迁移幂等（“数据库结构已是最新”）→ 退出进程清理 → 卸载。

.PARAMETER OldInstallerPath
    旧版安装包路径；缺省自动查找 release/任务管理系统_1.0.0_x64-setup.exe。

.PARAMETER NewInstallerPath
    新版安装包路径；缺省自动查找 release/任务管理系统_1.2.2_x64-setup.exe。

.PARAMETER SkipUninstall
    跳过最后的新版卸载。
#>
param(
    [string]$OldInstallerPath = '',
    [string]$NewInstallerPath = '',
    [int]$StartupTimeoutSeconds = 240,
    [switch]$SkipUninstall
)

$ErrorActionPreference = 'Stop'
$productName = '任务管理系统'
$superAdminUsername = 'superAdmin'
$superAdminPassword = 'SuperAdmin@123'
$markerUsername = 'migrationDemoUser'
$markerPassword = 'Migration@123'
$markerTeamName = '迁移验证团队-v1.0'
$resultList = New-Object System.Collections.ArrayList
$applicationDataDirectory = Join-Path $env:APPDATA 'TaskManagementSystem'
$backendLogPath = Join-Path $applicationDataDirectory 'logs/backend.log'
. (Join-Path $PSScriptRoot 'verifyInstalledAppWindow.ps1')

function Add-ReportResult {
    <# .SYNOPSIS 记录并输出单项升级验收结果 #>
    param([string]$Name, [bool]$Passed, [string]$Detail = '')
    $resultText = if ($Passed) { '通过' } else { '失败' }
    $resultColor = if ($Passed) { 'Green' } else { 'Red' }
    [void]$resultList.Add([PSCustomObject]@{ 检查项 = $Name; 结果 = $resultText; 详情 = $Detail })
    Write-Host ('[' + $resultText + '] ' + $Name + '  ' + $Detail) -ForegroundColor $resultColor
}
function Wait-Until {
    <# .SYNOPSIS 轮询等待条件成立（超时返回 $false） #>
    param([scriptblock]$Condition, [int]$TimeoutSeconds, [int]$IntervalMilliseconds = 1000)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try { if (& $Condition) { return $true } } catch { }
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
    return $false
}
function Get-InstalledExecutablePath {
    <# .SYNOPSIS 返回安装目录下的桌面可执行文件（找不到返回 $null） #>
    $candidateDirectory = Join-Path $env:LOCALAPPDATA $productName
    foreach ($candidateFileName in @(($productName + '.exe'), 'task-management-desktop.exe')) {
        $candidatePath = Join-Path $candidateDirectory $candidateFileName
        if (Test-Path $candidatePath) { return $candidatePath }
    }
    return $null
}
function Get-HealthPort {
    <# .SYNOPSIS 在 8765..8775 探测后端健康检查端口（返回 0 表示未就绪） #>
    for ($port = 8765; $port -le 8775; $port++) {
        try {
            $healthResponse = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/api/v1/health') -TimeoutSec 2
            if ($healthResponse.status -eq 'ok' -and $healthResponse.database -eq 'connected') { return $port }
        } catch { continue }
    }
    return 0
}
function Invoke-ApiJson {
    <# .SYNOPSIS 调用后端 JSON 接口（UTF-8 请求/响应，可选 Bearer Token）
        说明：Windows PowerShell 5.1 的 Invoke-RestMethod 在响应头无 charset 时会按 ISO-8859-1 解码导致中文乱码，
        这里改为 Invoke-WebRequest + 手动 UTF-8 解码响应字节流后再 ConvertFrom-Json。 #>
    param([string]$Method, [string]$Uri, $BodyObject = $null, [string]$BearerToken = '')
    $requestHeaders = @{ 'Content-Type' = 'application/json; charset=utf-8' }
    if ($BearerToken) { $requestHeaders['Authorization'] = 'Bearer ' + $BearerToken }
    $requestArguments = @{ Uri = $Uri; Method = $Method; Headers = $requestHeaders; TimeoutSec = 30; UseBasicParsing = $true }
    if ($null -ne $BodyObject) { $requestArguments['Body'] = [System.Text.Encoding]::UTF8.GetBytes(($BodyObject | ConvertTo-Json -Depth 6)) }
    $webResponse = Invoke-WebRequest @requestArguments
    $responseBytes = $null
    if ($webResponse.PSObject.Properties['RawContentStream'] -and $null -ne $webResponse.RawContentStream) {
        $responseBytes = $webResponse.RawContentStream.ToArray()
    } elseif ($webResponse.Content -is [byte[]]) {
        $responseBytes = $webResponse.Content
    }
    if ($null -eq $responseBytes) { return ($webResponse.Content | ConvertFrom-Json) }
    $responseText = [System.Text.Encoding]::UTF8.GetString($responseBytes)
    if ([string]::IsNullOrWhiteSpace($responseText)) { return $null }
    return ($responseText | ConvertFrom-Json)
}
function Start-InstalledApplication {
    <# .SYNOPSIS 启动已安装应用并等待窗口可见 + 后端健康就绪 #>
    param([int]$TimeoutSeconds)
    $installedExecutablePath = Get-InstalledExecutablePath
    if (-not $installedExecutablePath) { throw '未找到已安装的桌面可执行文件' }
    $appProcess = Start-Process -FilePath $installedExecutablePath -PassThru
    $windowShown = Wait-Until -TimeoutSeconds $TimeoutSeconds -Condition { return ((Find-TauriMainWindow -ProcessId $appProcess.Id) -ne [IntPtr]::Zero) }
    $script:detectedApplicationPort = 0
    $backendReady = Wait-Until -TimeoutSeconds $TimeoutSeconds -Condition { $script:detectedApplicationPort = Get-HealthPort; return ($script:detectedApplicationPort -gt 0) }
    return [PSCustomObject]@{ Process = $appProcess; Port = $script:detectedApplicationPort; WindowShown = $windowShown; BackendReady = $backendReady }
}
function Stop-InstalledApplication {
    <# .SYNOPSIS 通过 WM_CLOSE 关闭主窗口并等待进程退出（超时强制结束） #>
    param($Application)
    $windowHandle = Find-TauriMainWindow -ProcessId $Application.Process.Id
    if ($windowHandle -ne [IntPtr]::Zero) { [void][Win32WindowEnumerator]::PostMessage($windowHandle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }
    $exited = Wait-Until -TimeoutSeconds 45 -IntervalMilliseconds 500 -Condition { return $Application.Process.HasExited }
    if (-not $exited) { Stop-Process -Id $Application.Process.Id -Force -ErrorAction SilentlyContinue }
    return $exited
}
function Wait-ProjectRuntimeProcessesExited {
    <# .SYNOPSIS 等待本项目的后端/MariaDB/Redis 子进程全部退出（最多 60 秒） #>
    return Wait-Until -TimeoutSeconds 60 -Condition {
        $runtimeProcessList = Get-CimInstance Win32_Process -Filter "Name='runServer.exe' OR Name='mariadbd.exe' OR Name='mysqld.exe' OR Name='redis-server.exe'" -ErrorAction SilentlyContinue
        $projectProcesses = $runtimeProcessList | Where-Object { [string]$_.CommandLine -match '任务管理系统|TaskManagementSystem' }
        return ($null -eq $projectProcesses -or @($projectProcesses).Count -eq 0)
    }
}
function Install-ApplicationPackage {
    <# .SYNOPSIS 静默安装指定安装包（NSIS /S），失败时清理残留进程并最多重试 2 次 #>
    param([string]$InstallerPath)
    $lastExitCode = -1
    for ($attemptIndex = 1; $attemptIndex -le 3; $attemptIndex++) {
        Get-Process -Name 'task-management-desktop' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        [void](Wait-ProjectRuntimeProcessesExited)
        Start-Sleep -Seconds 2
        $installProcess = Start-Process -FilePath $InstallerPath -ArgumentList '/S' -Wait -PassThru
        $lastExitCode = $installProcess.ExitCode
        Write-Host ('  安装尝试 ' + $attemptIndex + ' 退出码：' + $lastExitCode)
        if ($lastExitCode -eq 0) { break }
        Start-Sleep -Seconds 10
    }
    Start-Sleep -Seconds 3
    return [PSCustomObject]@{ ExitCode = $lastExitCode; Succeeded = ($lastExitCode -eq 0) }
}
function Clear-ApplicationData {
    <# .SYNOPSIS 结束残留应用进程并清理应用数据目录（模拟全新安装） #>
    Get-Process -Name 'task-management-desktop' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    if (Test-Path $applicationDataDirectory) { Remove-Item -Recurse -Force $applicationDataDirectory }
    Start-Sleep -Seconds 2
}
function Get-BackendLogSegment {
    <# .SYNOPSIS 读取 backend.log 指定字符偏移之后新增的内容（判断本次启动的迁移日志） #>
    param([long]$StartOffset)
    if (-not (Test-Path $backendLogPath)) { return '' }
    $logText = Get-Content $backendLogPath -Raw -Encoding UTF8
    if ($StartOffset -ge $logText.Length) { return '' }
    return $logText.Substring([int]$StartOffset)
}
# ===== 0. 解析并校验安装包 =====
Write-Host ''
Write-Host '===== [0/9] 解析旧版/新版安装包 ====='
$releaseDirectory = Join-Path (Split-Path -Parent $PSScriptRoot) 'release'
if (-not $OldInstallerPath) { $OldInstallerPath = Join-Path $releaseDirectory '任务管理系统_1.0.0_x64-setup.exe' }
if (-not $NewInstallerPath) {
    $NewInstallerPath = Join-Path $releaseDirectory '任务管理系统_1.2.2_x64-setup.exe'
    if (-not (Test-Path $NewInstallerPath)) {
        $NewInstallerPath = Get-ChildItem $releaseDirectory -Filter '任务管理系统_1.2.2_x64-setup.exe' -File | Select-Object -First 1 -ExpandProperty FullName
    }
}
foreach ($installerCandidate in @($OldInstallerPath, $NewInstallerPath)) { if (-not (Test-Path $installerCandidate)) { throw ('未找到安装包：' + $installerCandidate) } }
Write-Host ('旧版：' + $OldInstallerPath)
Write-Host ('新版：' + $NewInstallerPath)

# ===== 1. 全新安装旧版 =====
Write-Host ''
Write-Host '===== [1/9] 清理数据并安装旧版（v1.0） ====='
Clear-ApplicationData
$oldInstallResult = Install-ApplicationPackage -InstallerPath $OldInstallerPath
Add-ReportResult -Name '旧版静默安装' -Passed $oldInstallResult.Succeeded -Detail ('退出码：' + $oldInstallResult.ExitCode)

# ===== 2. 旧版首次启动并生成标记数据 =====
Write-Host ''
Write-Host '===== [2/9] 旧版首次启动 + 生成 v1.0 标记数据 ====='
$oldApplication = Start-InstalledApplication -TimeoutSeconds $StartupTimeoutSeconds
Add-ReportResult -Name '旧版窗口显示/后端就绪' -Passed ($oldApplication.WindowShown -and $oldApplication.BackendReady) -Detail ('端口：' + $oldApplication.Port)
$oldApiBaseUrl = 'http://127.0.0.1:' + $oldApplication.Port + '/api/v1'
$oldHealth = Invoke-ApiJson -Method 'GET' -Uri ($oldApiBaseUrl + '/health')
Add-ReportResult -Name '旧版 health 版本为 1.0.0' -Passed ($oldHealth.version -eq '1.0.0') -Detail ('version=' + $oldHealth.version)
$oldAdminLogin = Invoke-ApiJson -Method 'POST' -Uri ($oldApiBaseUrl + '/auth/login') -BodyObject @{ username = $superAdminUsername; password = $superAdminPassword }
$oldAdminToken = $oldAdminLogin.token
Add-ReportResult -Name '旧版 superAdmin 登录' -Passed ($null -ne $oldAdminToken -and $oldAdminToken.Length -gt 20) -Detail ('token 长度：' + $oldAdminToken.Length)
$markerRegisterResponse = Invoke-ApiJson -Method 'POST' -Uri ($oldApiBaseUrl + '/auth/register') -BodyObject @{ username = $markerUsername; password = $markerPassword; nickname = '迁移验证用户' }
$markerUserCreated = ($null -ne $markerRegisterResponse.token)
$createdTeam = Invoke-ApiJson -Method 'POST' -Uri ($oldApiBaseUrl + '/teams') -BearerToken $oldAdminToken -BodyObject @{ name = $markerTeamName; description = 'v1.0 数据保留验证'; joinMethod = 'free' }
$markerTeamId = $createdTeam.id
Add-ReportResult -Name '旧版生成标记数据' -Passed ($markerUserCreated -and $markerTeamId -gt 0) -Detail ('用户：' + $markerUsername + '；团队ID：' + $markerTeamId)
$oldOverview = Invoke-ApiJson -Method 'GET' -Uri ($oldApiBaseUrl + '/admin/overview') -BearerToken $oldAdminToken
Write-Host ('旧版数据概况：userCount=' + $oldOverview.userCount + ' teamCount=' + $oldOverview.teamCount)
$oldClosed = Stop-InstalledApplication -Application $oldApplication
Add-ReportResult -Name '旧版关闭并退出' -Passed $oldClosed -Detail 'WM_CLOSE 后进程退出'
# 旧版进程已退出，此时读取日志长度作为升级日志区间起点（避免运行中文件被占用无法读取）
$logOffsetBeforeUpgrade = 0
if (Test-Path $backendLogPath) { $logOffsetBeforeUpgrade = (Get-Content $backendLogPath -Raw -Encoding UTF8).Length }

# ===== 3. 覆盖安装新版 =====
Write-Host ''
Write-Host '===== [3/9] 覆盖安装新版（v1.2.2） ====='
$newInstallResult = Install-ApplicationPackage -InstallerPath $NewInstallerPath
Add-ReportResult -Name '新版覆盖安装成功' -Passed $newInstallResult.Succeeded -Detail ('退出码：' + $newInstallResult.ExitCode)
$installedExecutableAfterUpgrade = Get-InstalledExecutablePath
$installedFileVersion = if ($installedExecutableAfterUpgrade) { (Get-Item $installedExecutableAfterUpgrade).VersionInfo.FileVersion } else { '' }
Add-ReportResult -Name '安装文件版本已更新为 1.2.2' -Passed ($installedFileVersion -like '1.2.2*') -Detail ('FileVersion=' + $installedFileVersion)
$runtimeConfigurationPath = Join-Path $applicationDataDirectory 'runtimeConfig.json'
Add-ReportResult -Name '升级不清除数据目录' -Passed (Test-Path $runtimeConfigurationPath) -Detail $applicationDataDirectory

# ===== 4. 启动新版并检查健康 =====
Write-Host ''
Write-Host '===== [4/9] 启动新版：健康检查 ====='
$newApplication = Start-InstalledApplication -TimeoutSeconds $StartupTimeoutSeconds
Add-ReportResult -Name '新版窗口显示/后端就绪' -Passed ($newApplication.WindowShown -and $newApplication.BackendReady) -Detail ('端口：' + $newApplication.Port)
$newApiBaseUrl = 'http://127.0.0.1:' + $newApplication.Port + '/api/v1'
$newHealth = Invoke-ApiJson -Method 'GET' -Uri ($newApiBaseUrl + '/health')
Add-ReportResult -Name '新版 health 版本为 1.2.2' -Passed ($newHealth.version -eq '1.2.2') -Detail ('version=' + $newHealth.version + '；database=' + $newHealth.database)

# ===== 5. 旧数据保留 + 新功能冒烟 =====
Write-Host ''
Write-Host '===== [5/9] 旧数据保留 + 新功能冒烟 ====='
$newAdminLogin = Invoke-ApiJson -Method 'POST' -Uri ($newApiBaseUrl + '/auth/login') -BodyObject @{ username = $superAdminUsername; password = $superAdminPassword }
$newAdminToken = $newAdminLogin.token
Add-ReportResult -Name '新版 superAdmin 登录' -Passed ($null -ne $newAdminToken -and $newAdminToken.Length -gt 20) -Detail ('token 长度：' + $newAdminToken.Length)
$markerLoginResponse = Invoke-ApiJson -Method 'POST' -Uri ($newApiBaseUrl + '/auth/login') -BodyObject @{ username = $markerUsername; password = $markerPassword }
$markerUserPreserved = ($null -ne $markerLoginResponse.token -and $markerLoginResponse.user.user.username -eq $markerUsername)
Add-ReportResult -Name '旧版注册用户可登录（数据保留）' -Passed $markerUserPreserved -Detail ('用户：' + $markerUsername)
$newTeamList = Invoke-ApiJson -Method 'GET' -Uri ($newApiBaseUrl + '/teams') -BearerToken $newAdminToken
$markerTeamPreserved = [bool]($newTeamList | Where-Object { $_.name -eq $markerTeamName })
Add-ReportResult -Name '旧版创建团队仍在（数据保留）' -Passed $markerTeamPreserved -Detail ('团队：' + $markerTeamName)
$newOverview = Invoke-ApiJson -Method 'GET' -Uri ($newApiBaseUrl + '/admin/overview') -BearerToken $newAdminToken
Add-ReportResult -Name '用户数据数量未丢失' -Passed ($newOverview.userCount -ge $oldOverview.userCount -and $newOverview.userCount -ge 2) -Detail ('升级前 userCount=' + $oldOverview.userCount + '；升级后 userCount=' + $newOverview.userCount)
$aiStatusResponse = Invoke-ApiJson -Method 'GET' -Uri ($newApiBaseUrl + '/ai/status') -BearerToken $newAdminToken
$aiStatusPassed = ([string]$aiStatusResponse.provider -ne '' -and [string]$aiStatusResponse.dispatchMode -ne '')
Add-ReportResult -Name '新功能冒烟：/api/v1/ai/status' -Passed $aiStatusPassed -Detail ('provider=' + $aiStatusResponse.provider + '；dispatchMode=' + $aiStatusResponse.dispatchMode + '；llmConfigured=' + $aiStatusResponse.llmConfigured)

# ===== 6. 关闭新版并检查进程清理 =====
Write-Host ''
Write-Host '===== [6/9] 关闭新版并检查进程清理 ====='
$newClosed = Stop-InstalledApplication -Application $newApplication
Add-ReportResult -Name '新版关闭后应用退出' -Passed $newClosed -Detail 'WM_CLOSE 后进程退出'
$portReleased = Wait-Until -TimeoutSeconds 45 -Condition { return ((Get-HealthPort) -eq 0) }
Add-ReportResult -Name '后端端口释放' -Passed $portReleased -Detail '8765..8775 无健康响应'
$runtimeProcessesExited = Wait-Until -TimeoutSeconds 45 -Condition {
    $runtimeProcessList = Get-CimInstance Win32_Process -Filter "Name='runServer.exe' OR Name='mariadbd.exe' OR Name='mysqld.exe' OR Name='redis-server.exe'" -ErrorAction SilentlyContinue
    $projectProcesses = $runtimeProcessList | Where-Object { [string]$_.CommandLine -match '任务管理系统|TaskManagementSystem' }
    return ($null -eq $projectProcesses -or @($projectProcesses).Count -eq 0)
}
Add-ReportResult -Name '内置后端/MariaDB/Redis 进程退出' -Passed $runtimeProcessesExited -Detail 'runServer/mariadbd/redis-server'
# 进程已退出，读取升级后新增的日志片段并校验数据库结构迁移证据
$upgradeLogSegment = Get-BackendLogSegment -StartOffset $logOffsetBeforeUpgrade
$migrationDetected = ($upgradeLogSegment -match '数据库结构升级完成|Database schema upgrade completed') -and ($upgradeLogSegment -match '数据库升级：|Database upgrade:')
Add-ReportResult -Name '数据库结构升级日志出现' -Passed $migrationDetected -Detail 'backend.log 含升级完成与数据库升级明细（中/英任一）'
$logOffsetBeforeSecondStart = [System.IO.File]::ReadAllText($backendLogPath, [System.Text.Encoding]::UTF8).Length

# ===== 7. 再次启动验证迁移幂等 =====
Write-Host ''
Write-Host '===== [7/9] 再次启动新版：迁移幂等校验 ====='
$logOffsetBeforeSecondStart = [System.IO.File]::ReadAllText($backendLogPath, [System.Text.Encoding]::UTF8).Length
$secondApplication = Start-InstalledApplication -TimeoutSeconds $StartupTimeoutSeconds
Add-ReportResult -Name '新版第二次启动正常' -Passed ($secondApplication.WindowShown -and $secondApplication.BackendReady) -Detail ('端口：' + $secondApplication.Port)
$secondClosed = Stop-InstalledApplication -Application $secondApplication
Add-ReportResult -Name '第二次关闭并退出' -Passed $secondClosed -Detail 'WM_CLOSE 后进程退出'
# 进程退出后读取第二次启动新增日志，校验迁移幂等
$secondStartLogSegment = Get-BackendLogSegment -StartOffset $logOffsetBeforeSecondStart
$migrationIdempotent = ($secondStartLogSegment -match '数据库结构已是最新|Database schema is up to date')
Add-ReportResult -Name '迁移幂等（无重复变更）' -Passed $migrationIdempotent -Detail 'backend.log 含“数据库结构已是最新 / Database schema is up to date”'

# ===== 8. 卸载 =====
Write-Host ''
Write-Host '===== [8/9] 卸载新版 ====='
if (-not $SkipUninstall) {
    $installedExecutablePath = Get-InstalledExecutablePath
    $uninstallerPath = Join-Path (Split-Path -Parent $installedExecutablePath) 'uninstall.exe'
    if (Test-Path $uninstallerPath) {
        $uninstallProcess = Start-Process -FilePath $uninstallerPath -ArgumentList '/S' -Wait -PassThru
        Start-Sleep -Seconds 5
        $uninstalled = -not (Test-Path $installedExecutablePath)
        Add-ReportResult -Name '新版静默卸载' -Passed ($uninstalled -and $uninstallProcess.ExitCode -eq 0) -Detail ('退出码：' + $uninstallProcess.ExitCode)
    } else { Add-ReportResult -Name '新版静默卸载' -Passed $false -Detail ('未找到卸载程序：' + $uninstallerPath) }
} else { Add-ReportResult -Name '新版静默卸载' -Passed $true -Detail '已跳过（-SkipUninstall）' }

# ===== 9. 汇总 =====
Write-Host ''
Write-Host '================ 升级路径验收结果汇总 ================'
$resultList | Format-Table -AutoSize | Out-String | Write-Host
$failedCount = @($resultList | Where-Object { $_.结果 -eq '失败' }).Count
Write-Host ('通过 ' + ($resultList.Count - $failedCount) + ' 项，失败 ' + $failedCount + ' 项')
if ($failedCount -gt 0) { exit 1 }
Write-Host '升级路径验收全部通过'
exit 0