#requires -Version 5.1
<#
.SYNOPSIS
    启动本地开发运行时：独立 MySQL 实例（默认 3307）与便携 Redis（默认 6380）。

.DESCRIPTION
    1. 使用本机已安装的 MySQL 8 二进制，在 .devdata/mysql 独立数据目录启动实例，
       完全不修改系统已有的 MySQL80 服务；
    2. Redis 使用 Runtime/redis 下的便携版本，数据目录 .devdata/redis；
    3. 脚本幂等：端口已监听时直接跳过；自动创建业务数据库与开发账号；
    4. 使用 -KeepAlive 时脚本在启动后保持前台运行（供自动化开发会话托管）。

.PARAMETER MysqlPort
    MySQL 监听端口，默认 3307。

.PARAMETER RedisPort
    Redis 监听端口，默认 6380。

.PARAMETER KeepAlive
    启动后保持进程存活，直到手动终止。
#>
param(
    [int]$MysqlPort = 3307,
    [int]$RedisPort = 6380,
    [switch]$KeepAlive
)

$ErrorActionPreference = 'Stop'

# ===== 路径解析 =====
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDirectory = Join-Path $projectRoot '.devdata'
$mysqlDataDirectory = Join-Path $runtimeDirectory 'mysql'
$redisDataDirectory = Join-Path $runtimeDirectory 'redis'
$mysqlLogFile = Join-Path $runtimeDirectory 'mysql.log'
$redisLogFile = Join-Path $runtimeDirectory 'redis.log'
$databaseInitializeSqlFile = Join-Path $PSScriptRoot 'initializeDatabase.sql'
New-Item -ItemType Directory -Force -Path $runtimeDirectory, $redisDataDirectory | Out-Null

# 已启动的子进程列表，KeepAlive 结束时统一清理
$script:startedProcesses = @()

function Test-PortListening {
    <#
    .SYNOPSIS
        判断本机端口是否已处于监听状态。
    #>
    param([int]$Port)
    $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Find-MysqlBaseDirectory {
    <#
    .SYNOPSIS
        定位本机 MySQL 8 安装根目录（优先默认路径，其次从 MySQL80 服务路径推断）。
    #>
    $candidateDirectories = @(
        'C:\Program Files\MySQL\MySQL Server 8.0',
        'C:\Program Files\MySQL\MySQL Server 8.4'
    )
    foreach ($candidate in $candidateDirectories) {
        if (Test-Path (Join-Path $candidate 'bin\mysqld.exe')) {
            return $candidate
        }
    }
    $mysqlService = Get-CimInstance Win32_Service -Filter "Name='MySQL80'" -ErrorAction SilentlyContinue
    if ($null -ne $mysqlService) {
        $servicePath = $mysqlService.PathName
        if ($servicePath -match '^"([^"]+)"') {
            $executablePath = $Matches[1]
            return (Split-Path -Parent (Split-Path -Parent $executablePath))
        }
    }
    throw '未找到 MySQL 8 安装目录，请先安装 MySQL 8 或调整本脚本中的候选路径。'
}

function Start-DetachedProcess {
    <#
    .SYNOPSIS
        以无窗口方式启动后台进程，返回进程对象。
    #>
    param([string]$FilePath, [string]$ArgumentString, [string]$WorkingDirectory)
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $ArgumentString
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $script:startedProcesses += $process
    return $process
}

function Wait-PortListening {
    <#
    .SYNOPSIS
        在限定时间内等待端口进入监听状态。
    #>
    param([int]$Port, [int]$TimeoutSeconds = 30)
    for ($index = 0; $index -lt ($TimeoutSeconds * 2); $index++) {
        if (Test-PortListening -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Initialize-MysqlDataDirectory {
    <#
    .SYNOPSIS
        若数据目录尚未初始化，则执行 mysqld --initialize-insecure 生成初始数据目录。
    #>
    param([string]$MysqlBaseDirectory)
    if (Test-Path (Join-Path $mysqlDataDirectory 'mysql')) {
        Write-Host ('[MySQL] 数据目录已存在，跳过初始化：' + $mysqlDataDirectory)
        return
    }
    Write-Host '[MySQL] 正在初始化独立数据目录 ...'
    $mysqldPath = Join-Path $MysqlBaseDirectory 'bin\mysqld.exe'
    & $mysqldPath --initialize-insecure ("--basedir=" + $MysqlBaseDirectory) ("--datadir=" + $mysqlDataDirectory) ("--log-error=" + $mysqlLogFile) 2>$null | Out-Null
    if (-not (Test-Path (Join-Path $mysqlDataDirectory 'mysql'))) {
        throw ('MySQL 数据目录初始化失败，请查看日志：' + $mysqlLogFile)
    }
    Write-Host '[MySQL] 数据目录初始化完成'
}

function Ensure-MysqlRunning {
    <#
    .SYNOPSIS
        确保开发 MySQL 实例运行，并创建业务数据库与开发账号。
    #>
    param([string]$MysqlBaseDirectory)
    if (Test-PortListening -Port $MysqlPort) {
        Write-Host ('[MySQL] 端口 ' + $MysqlPort + ' 已在监听，跳过启动')
    } else {
        Write-Host ('[MySQL] 启动独立实例，端口 ' + $MysqlPort + ' ...')
        $mysqldPath = Join-Path $MysqlBaseDirectory 'bin\mysqld.exe'
        $arguments = @(
            '--basedir="' + $MysqlBaseDirectory + '"',
            '--datadir="' + $mysqlDataDirectory + '"',
            '--port=' + $MysqlPort,
            '--bind-address=127.0.0.1',
            '--mysqlx=0',
            '--pid-file="' + (Join-Path $runtimeDirectory 'mysql.pid') + '"',
            '--log-error="' + $mysqlLogFile + '"'
        ) -join ' '
        Start-DetachedProcess -FilePath $mysqldPath -ArgumentString $arguments -WorkingDirectory $projectRoot | Out-Null
        if (-not (Wait-PortListening -Port $MysqlPort -TimeoutSeconds 40)) {
            throw ('MySQL 启动超时，请查看日志：' + $mysqlLogFile)
        }
        Write-Host '[MySQL] 启动成功'
    }
    $mysqlClientPath = Join-Path $MysqlBaseDirectory 'bin\mysql.exe'
    $sqlStatements = Get-Content -Raw -Encoding UTF8 $databaseInitializeSqlFile
    & $mysqlClientPath --protocol=TCP -h 127.0.0.1 -P $MysqlPort -u root -e $sqlStatements 2>$null | Out-Null
    Write-Host '[MySQL] 数据库与开发账号已就绪'
}

function Ensure-RedisRunning {
    <#
    .SYNOPSIS
        确保便携 Redis 实例运行（配置文件方式启动，避免参数转义问题）。
    #>
    $redisServerPath = Join-Path $projectRoot 'Runtime/redis/redis-server.exe'
    $redisClientPath = Join-Path $projectRoot 'Runtime/redis/redis-cli.exe'
    if (-not (Test-Path $redisServerPath)) {
        throw ('未找到便携 Redis：' + $redisServerPath + '，请先运行安装脚本下载运行时。')
    }
    if (Test-PortListening -Port $RedisPort) {
        Write-Host ('[Redis] 端口 ' + $RedisPort + ' 已在监听，跳过启动')
    } else {
        Write-Host ('[Redis] 启动便携实例，端口 ' + $RedisPort + ' ...')
        $redisConfigurationFile = Join-Path $runtimeDirectory 'redis.conf'
        $redisConfiguration = @(
            'port ' + $RedisPort,
            'bind 127.0.0.1',
            'protected-mode yes',
            'dir "' + $redisDataDirectory + '"',
            'save ""',
            'appendonly no',
            'logfile "' + $redisLogFile + '"',
            'databases 16'
        ) -join "`r`n"
        [System.IO.File]::WriteAllText($redisConfigurationFile, $redisConfiguration)
        Start-DetachedProcess -FilePath $redisServerPath -ArgumentString ('"' + $redisConfigurationFile + '"') -WorkingDirectory $projectRoot | Out-Null
        if (-not (Wait-PortListening -Port $RedisPort -TimeoutSeconds 20)) {
            throw ('Redis 启动超时，请查看日志：' + $redisLogFile)
        }
        Write-Host '[Redis] 启动成功'
    }
    $pingResult = & $redisClientPath -p $RedisPort ping 2>$null
    Write-Host ('[Redis] PING 结果：' + $pingResult)
}

# ===== 主流程 =====
$mysqlBaseDirectory = Find-MysqlBaseDirectory
Initialize-MysqlDataDirectory -MysqlBaseDirectory $mysqlBaseDirectory
Ensure-MysqlRunning -MysqlBaseDirectory $mysqlBaseDirectory
Ensure-RedisRunning

Write-Host ''
Write-Host '本地开发运行时已就绪：'
Write-Host ('  MySQL : 127.0.0.1:' + $MysqlPort + '（task_management / task_management_test，账号 taskadmin / taskadmin123）')
Write-Host ('  Redis : 127.0.0.1:' + $RedisPort)
Write-Host ''

if ($KeepAlive) {
    Write-Host '保持运行中 ...'
    try {
        while ($true) {
            Start-Sleep -Seconds 3600
        }
    } finally {
        foreach ($process in $script:startedProcesses) {
            if (-not $process.HasExited) {
                $process.Kill()
            }
        }
    }
}
