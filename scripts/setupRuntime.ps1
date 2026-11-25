#requires -Version 5.1
<#
.SYNOPSIS
    准备 Windows 便携运行时：裁剪并落地 MariaDB 11.4 winx64 与便携 Redis 到 Runtime/ 目录。

.DESCRIPTION
    本脚本由 scripts/buildWindowsInstaller.ps1 调用，也可以手动执行：
    1. MariaDB：优先使用 Runtime/downloads 下的 winx64 zip 缓存，否则从 archive.mariadb.org / 清华镜像下载；
       解压后裁剪掉 include、语言包、调试符号、备份工具等非运行必需文件，只保留 bin/lib/share 的最小集；
    2. Redis：优先使用 Runtime/downloads/redis-windows.zip（tporadowski/redis 构建），解压并移除 .pdb 调试符号；
    3. 产物目录 Runtime/mariadb 与 Runtime/redis 不进入 git，最终由 Tauri 作为 resource 打入安装包。

.PARAMETER MariaDbVersion
    MariaDB 版本号，默认 11.4.14（11.4 为 LTS 分支）。

.PARAMETER Force
    强制重新解压裁剪，即使目标目录已存在。

.PARAMETER SkipRedis
    只准备 MariaDB，跳过 Redis。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/setupRuntime.ps1 -Force
#>
param(
    [string]$MariaDbVersion = '11.4.14',
    [switch]$Force,
    [switch]$SkipRedis
)

$ErrorActionPreference = 'Stop'

# ===== 路径常量 =====
$repoRootDirectory = Split-Path -Parent $PSScriptRoot
$runtimeRootDirectory = Join-Path $repoRootDirectory 'Runtime'
$downloadDirectory = Join-Path $runtimeRootDirectory 'downloads'
$mariaDbTargetDirectory = Join-Path $runtimeRootDirectory 'mariadb'
$redisTargetDirectory = Join-Path $runtimeRootDirectory 'redis'
$mariaDbArchiveFileName = 'mariadb-' + $MariaDbVersion + '-winx64.zip'
$mariaDbArchivePath = Join-Path $downloadDirectory $mariaDbArchiveFileName
$redisArchivePath = Join-Path $downloadDirectory 'redis-windows.zip'

# MariaDB 下载地址（按可用性依次尝试；清华镜像在国内速度快）
$mariaDbDownloadUrls = @(
    'https://mirrors.tuna.tsinghua.edu.cn/mariadb//mariadb-' + $MariaDbVersion + '/winx64-packages/' + $mariaDbArchiveFileName,
    'https://mirrors.ustc.edu.cn/mariadb/mariadb-' + $MariaDbVersion + '/winx64-packages/' + $mariaDbArchiveFileName,
    'https://archive.mariadb.org/mariadb-' + $MariaDbVersion + '/winx64-packages/' + $mariaDbArchiveFileName
)
# Redis 下载地址（tporadowski/redis Windows 构建，GitHub Release 资产）
$redisDownloadUrls = @(
    'https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip'
)

New-Item -ItemType Directory -Force -Path $downloadDirectory, $runtimeRootDirectory | Out-Null

function Write-Section {
    <#
    .SYNOPSIS
        输出分节标题，便于阅读构建日志。
    #>
    param([string]$Title)
    Write-Host ''
    Write-Host ('===== ' + $Title + ' =====')
}

function Invoke-FileDownload {
    <#
    .SYNOPSIS
        下载文件到指定路径：依次尝试多个地址，校验最小文件大小，失败时删除半成品。
    #>
    param(
        [string[]]$UrlList,
        [string]$TargetPath,
        [long]$MinimumBytes
    )
    if ((Test-Path $TargetPath) -and ((Get-Item $TargetPath).Length -ge $MinimumBytes)) {
        Write-Host ('使用已缓存文件：' + $TargetPath + '（' + [math]::Round((Get-Item $TargetPath).Length / 1MB, 1) + ' MB）')
        return
    }
    foreach ($url in $UrlList) {
        Write-Host ('开始下载：' + $url)
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            & curl.exe -L --fail --retry 3 --retry-delay 2 --connect-timeout 20 --max-time 3600 -o $TargetPath $url
            $downloadSucceeded = ($LASTEXITCODE -eq 0)
        } catch {
            $downloadSucceeded = $false
            Write-Host ('下载异常：' + $_.Exception.Message)
        }
        if ($downloadSucceeded -and (Test-Path $TargetPath)) {
            $downloadedSize = (Get-Item $TargetPath).Length
            if ($downloadedSize -ge $MinimumBytes) {
                $stopwatch.Stop()
                Write-Host ('下载完成：' + [math]::Round($downloadedSize / 1MB, 1) + ' MB，耗时 ' + [math]::Round($stopwatch.Elapsed.TotalSeconds) + ' 秒')
                return
            }
            Write-Host ('文件大小异常（' + $downloadedSize + ' 字节），删除后尝试下一个地址')
            Remove-Item -Force -ErrorAction SilentlyContinue $TargetPath
        }
    }
    throw ('所有下载地址均失败，请检查网络后重试：' + ($UrlList -join ' , '))
}

function Export-ZipToDirectory {
    <#
    .SYNOPSIS
        使用 .NET 解压 zip 到指定目录（比 Expand-Archive 快，且不受长路径限制影响）。
    #>
    param([string]$ArchivePath, [string]$TargetDirectory)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $TargetDirectory) { Remove-Item -Recurse -Force $TargetDirectory }
    New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $TargetDirectory)
}

function Copy-SelectedFiles {
    <#
    .SYNOPSIS
        把源目录中匹配指定文件名集合的文件复制到目标目录（用于裁剪 bin 目录）。
    #>
    param(
        [string]$SourceDirectory,
        [string]$TargetDirectory,
        [string[]]$FileNameList
    )
    New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
    foreach ($fileName in $FileNameList) {
        $sourcePath = Join-Path $SourceDirectory $fileName
        if (Test-Path $sourcePath) {
            Copy-Item -Force -Path $sourcePath -Destination (Join-Path $TargetDirectory $fileName)
        }
    }
}

function Copy-FilesByExtension {
    <#
    .SYNOPSIS
        把源目录中指定扩展名的文件复制到目标目录。
    #>
    param([string]$SourceDirectory, [string]$TargetDirectory, [string]$Extension)
    New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
    Get-ChildItem $SourceDirectory -File -Filter ('*' + $Extension) | ForEach-Object {
        Copy-Item -Force -Path $_.FullName -Destination (Join-Path $TargetDirectory $_.Name)
    }
}

function Initialize-MariaDbRuntime {
    <#
    .SYNOPSIS
        解压并裁剪 MariaDB 便携运行时：仅保留 server、安装工具、客户端、管理工具与必要插件。
    #>
    if ((Test-Path (Join-Path $mariaDbTargetDirectory 'bin/server.dll')) -and -not $Force) {
        Write-Host ('MariaDB 运行时已存在，跳过：' + $mariaDbTargetDirectory + '（使用 -Force 强制重建）')
        return
    }
    Invoke-FileDownload -UrlList $mariaDbDownloadUrls -TargetPath $mariaDbArchivePath -MinimumBytes 52428800
    $extractDirectory = Join-Path $downloadDirectory 'mariadb-extract'
    Write-Host '解压 MariaDB 归档 ...'
    Export-ZipToDirectory -ArchivePath $mariaDbArchivePath -TargetDirectory $extractDirectory
    $extractedRoot = Get-ChildItem $extractDirectory -Directory | Select-Object -First 1
    if ($null -eq $extractedRoot) { throw 'MariaDB 归档解压后缺少根目录' }
    Write-Host ('裁剪 MariaDB：' + $extractedRoot.FullName)
    if (Test-Path $mariaDbTargetDirectory) { Remove-Item -Recurse -Force $mariaDbTargetDirectory }
    New-Item -ItemType Directory -Force -Path $mariaDbTargetDirectory | Out-Null
    # bin：服务器（stub + server.dll）、初始化工具、客户端、管理工具、VC 运行时 DLL
    $binaryFileNameList = @(
        'mysqld.exe', 'mariadbd.exe', 'server.dll',
        'mariadb-install-db.exe', 'mysql_install_db.exe',
        'mariadb.exe', 'mariadb-admin.exe',
        'my_print_defaults.exe'
    )
    Copy-SelectedFiles -SourceDirectory (Join-Path $extractedRoot.FullName 'bin') -TargetDirectory (Join-Path $mariaDbTargetDirectory 'bin') -FileNameList $binaryFileNameList
    Copy-FilesByExtension -SourceDirectory (Join-Path $extractedRoot.FullName 'bin') -TargetDirectory (Join-Path $mariaDbTargetDirectory 'bin') -Extension '.dll'
    # lib：客户端库 + 认证相关插件（运行时不需要 ha_* 存储引擎插件与备份工具）
    $libraryTargetDirectory = Join-Path $mariaDbTargetDirectory 'lib'
    New-Item -ItemType Directory -Force -Path (Join-Path $libraryTargetDirectory 'plugin') | Out-Null
    $clientLibraryPath = Join-Path $extractedRoot.FullName 'lib/libmariadb.dll'
    if (Test-Path $clientLibraryPath) { Copy-Item -Force $clientLibraryPath -Destination $libraryTargetDirectory }
    $pluginFileNameList = @(
        'caching_sha2_password.dll', 'mysql_clear_password.dll', 'dialog.dll',
        'auth_ed25519.dll', 'client_ed25519.dll', 'sha256_password.dll', 'locales.dll'
    )
    Copy-SelectedFiles -SourceDirectory (Join-Path $extractedRoot.FullName 'lib/plugin') -TargetDirectory (Join-Path $libraryTargetDirectory 'plugin') -FileNameList $pluginFileNameList
    # share：系统表 SQL、英文错误信息与字符集
    $shareTargetDirectory = Join-Path $mariaDbTargetDirectory 'share'
    New-Item -ItemType Directory -Force -Path $shareTargetDirectory | Out-Null
    Get-ChildItem (Join-Path $extractedRoot.FullName 'share') -File | ForEach-Object { Copy-Item -Force $_.FullName -Destination $shareTargetDirectory }
    foreach ($shareSubDirectoryName in @('english', 'charsets')) {
        $shareSubDirectorySource = Join-Path $extractedRoot.FullName ('share/' + $shareSubDirectoryName)
        if (Test-Path $shareSubDirectorySource) {
            Copy-Item -Recurse -Force $shareSubDirectorySource -Destination $shareTargetDirectory
        }
    }
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $extractDirectory
    Write-Host 'MariaDB 运行时裁剪完成'
}

function Initialize-RedisRuntime {
    <#
    .SYNOPSIS
        解压并裁剪便携 Redis：只保留 redis-server.exe 与 redis-cli.exe。
    #>
    if ((Test-Path (Join-Path $redisTargetDirectory 'redis-server.exe')) -and -not $Force) {
        Write-Host ('Redis 运行时已存在，跳过：' + $redisTargetDirectory + '（使用 -Force 强制重建）')
        return
    }
    if (-not (Test-Path $redisArchivePath)) {
        Invoke-FileDownload -UrlList $redisDownloadUrls -TargetPath $redisArchivePath -MinimumBytes 2097152
    }
    $redisExtractDirectory = Join-Path $downloadDirectory 'redis-extract'
    Write-Host '解压 Redis 归档 ...'
    Export-ZipToDirectory -ArchivePath $redisArchivePath -TargetDirectory $redisExtractDirectory
    $redisServerSource = Get-ChildItem $redisExtractDirectory -Recurse -File -Filter 'redis-server.exe' | Select-Object -First 1
    if ($null -eq $redisServerSource) { throw 'Redis 归档中未找到 redis-server.exe' }
    if (Test-Path $redisTargetDirectory) {
        # 开发运行时可能正在使用 Runtime/redis 中的 redis-server.exe（端口被占用时无法删除），
        # 此时退化为覆盖必要文件并清理调试符号，保证脚本可重复执行
        try {
            Remove-Item -Recurse -Force $redisTargetDirectory -ErrorAction Stop
        } catch {
            Write-Host ('Redis 目录被运行中的进程占用，改为覆盖更新：' + $_.Exception.Message)
        }
    }
    New-Item -ItemType Directory -Force -Path $redisTargetDirectory | Out-Null
    Copy-Item -Force $redisServerSource.FullName -Destination (Join-Path $redisTargetDirectory 'redis-server.exe')
    $redisClientSource = Join-Path $redisServerSource.DirectoryName 'redis-cli.exe'
    if (Test-Path $redisClientSource) { Copy-Item -Force $redisClientSource -Destination (Join-Path $redisTargetDirectory 'redis-cli.exe') }
    # 清理体积较大的调试符号文件（.pdb 每个数 MB，运行时不需要）
    Get-ChildItem $redisTargetDirectory -File -Filter '*.pdb' -ErrorAction SilentlyContinue | ForEach-Object {
        try { Remove-Item -Force $_.FullName -ErrorAction Stop } catch { Write-Host ('跳过被占用的调试符号：' + $_.Name) }
    }
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $redisExtractDirectory
    Write-Host 'Redis 运行时裁剪完成'
}

function Get-DirectorySizeMegabytes {
    <#
    .SYNOPSIS
        计算目录内文件总大小（MB，保留 1 位小数）。
    #>
    param([string]$DirectoryPath)
    if (-not (Test-Path $DirectoryPath)) { return 0 }
    $totalBytes = (Get-ChildItem $DirectoryPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
    if ($null -eq $totalBytes) { return 0 }
    return [math]::Round($totalBytes / 1MB, 1)
}

# ===== 主流程 =====
Write-Section '准备便携 MariaDB 运行时'
Initialize-MariaDbRuntime
if (-not $SkipRedis) {
    Write-Section '准备便携 Redis 运行时'
    Initialize-RedisRuntime
}

Write-Section '运行时准备完成'
$mariaDbSize = Get-DirectorySizeMegabytes -DirectoryPath $mariaDbTargetDirectory
$redisSize = Get-DirectorySizeMegabytes -DirectoryPath $redisTargetDirectory
Write-Host ('MariaDB：' + $mariaDbTargetDirectory + '（' + $mariaDbSize + ' MB）')
Write-Host ('Redis  ：' + $redisTargetDirectory + '（' + $redisSize + ' MB）')
$requiredPathList = @(
    (Join-Path $mariaDbTargetDirectory 'bin/mariadbd.exe'),
    (Join-Path $mariaDbTargetDirectory 'bin/server.dll'),
    (Join-Path $mariaDbTargetDirectory 'bin/mariadb-install-db.exe'),
    (Join-Path $mariaDbTargetDirectory 'bin/mariadb.exe'),
    (Join-Path $mariaDbTargetDirectory 'bin/mariadb-admin.exe')
)
foreach ($requiredPath in $requiredPathList) {
    if (-not (Test-Path $requiredPath)) { throw ('便携运行时缺少必要文件：' + $requiredPath) }
}
if (-not $SkipRedis -and -not (Test-Path (Join-Path $redisTargetDirectory 'redis-server.exe'))) {
    throw '便携运行时缺少 redis-server.exe'
}
Write-Host '便携运行时校验通过'
