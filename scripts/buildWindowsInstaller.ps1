#requires -Version 5.1
<#
.SYNOPSIS
    一键构建 Windows 安装包（NSIS .exe）与便携 zip。

.DESCRIPTION
    构建流水线（任一步失败立即终止并输出中文错误）：
        1. 前端生产构建：Frontend 目录执行 npm run build；
        2. 后端可执行文件：Backend/buildBackend.py（PyInstaller onedir → runServer.exe）；
        3. 便携运行时：scripts/setupRuntime.ps1（裁剪 MariaDB 11.4 + Redis 到 Runtime/）；
        4. 资源 staging：把后端产物、便携运行时与前端 dist 复制到 Frontend/src-tauri/resources；
        5. Tauri 打包：npx tauri build --bundles nsis 产出安装包；
        6. 产物整理：安装包与可执行文件复制到 release/，并生成便携 zip。

    前置要求：Node 24+、Rust MSVC 工具链、VS Build Tools、Python 虚拟环境 Backend/.venv（含 pyinstaller）。

.PARAMETER SkipFrontendBuild
    跳过前端构建（复用已有 Frontend/dist）。

.PARAMETER SkipBackendBuild
    跳过后端打包（复用已有 Backend/dist/runServer）。

.PARAMETER SkipRuntimeSetup
    跳过便携运行时准备（复用已有 Runtime/mariadb 与 Runtime/redis）。

.PARAMETER SkipTauriBuild
    跳过 Tauri 打包（只做 staging，用于验证资源是否正确）。

.PARAMETER SkipPortableZip
    跳过便携 zip 生成（安装包构建通常已足够）。

.PARAMETER CleanBackend
    后端打包前执行 PyInstaller --clean（完整重建，耗时更长）。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/buildWindowsInstaller.ps1
#>
param(
    [switch]$SkipFrontendBuild,
    [switch]$SkipBackendBuild,
    [switch]$SkipRuntimeSetup,
    [switch]$SkipTauriBuild,
    [switch]$SkipPortableZip,
    [switch]$CleanBackend
)

$ErrorActionPreference = 'Stop'

# ===== 路径与常量 =====
$repoRootDirectory = Split-Path -Parent $PSScriptRoot
$frontendDirectory = Join-Path $repoRootDirectory 'Frontend'
$backendDirectory = Join-Path $repoRootDirectory 'Backend'
$pythonExecutablePath = Join-Path $backendDirectory '.venv/Scripts/python.exe'
$tauriResourcesDirectory = Join-Path $frontendDirectory 'src-tauri/resources'
$backendResourceDirectory = Join-Path $tauriResourcesDirectory 'backend'
$runtimeResourceDirectory = Join-Path $tauriResourcesDirectory 'runtime'
$frontendResourceDirectory = Join-Path $tauriResourcesDirectory 'frontend'
$releaseDirectory = Join-Path $repoRootDirectory 'release'
# 产品名与版本号自动读取 Tauri 配置，避免打包脚本与代码版本不一致（Lead 发布前只需改 tauri.conf.json）
$tauriConfigurationPath = Join-Path $frontendDirectory 'src-tauri/tauri.conf.json'
if (-not (Test-Path $tauriConfigurationPath)) {
    throw ('未找到 Tauri 配置：' + $tauriConfigurationPath)
}
$tauriConfiguration = Get-Content $tauriConfigurationPath -Raw -Encoding UTF8 | ConvertFrom-Json
$productName = [string]$tauriConfiguration.productName
$productVersion = [string]$tauriConfiguration.version
if (-not $productName -or -not $productVersion) {
    throw '无法从 tauri.conf.json 解析 productName / version'
}
Write-Host ('构建目标：' + $productName + ' v' + $productVersion)
$totalStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Write-BuildStep {
    <#
    .SYNOPSIS
        输出带序号的构建步骤标题。
    #>
    param([int]$StepIndex, [string]$Description)
    Write-Host ''
    Write-Host ('===== [' + $StepIndex + '/6] ' + $Description + ' =====')
}

function Reset-Directory {
    <#
    .SYNOPSIS
        清空并重建目录（不存在则直接创建）。
    #>
    param([string]$DirectoryPath)
    if (Test-Path $DirectoryPath) {
        Remove-Item -Recurse -Force $DirectoryPath
    }
    New-Item -ItemType Directory -Force -Path $DirectoryPath | Out-Null
}

function Copy-DirectoryContent {
    <#
    .SYNOPSIS
        把源目录全部内容复制到目标目录（目标目录需已存在）。
    #>
    param([string]$SourceDirectory, [string]$TargetDirectory)
    if (-not (Test-Path $SourceDirectory)) {
        throw ('复制失败，源目录不存在：' + $SourceDirectory)
    }
    New-Item -ItemType Directory -Force -Path $TargetDirectory | Out-Null
    Copy-Item -Path (Join-Path $SourceDirectory '*') -Destination $TargetDirectory -Recurse -Force
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

function Assert-LastExitCode {
    <#
    .SYNOPSIS
        校验上一条外部命令退出码，失败时抛出中文异常。
    #>
    param([string]$CommandDescription)
    if ($LASTEXITCODE -ne 0) {
        throw ($CommandDescription + ' 失败（退出码：' + $LASTEXITCODE + '）')
    }
}

# ===== 步骤 1：前端生产构建 =====
Write-BuildStep -StepIndex 1 -Description '前端生产构建（npm run build）'
if (-not $SkipFrontendBuild) {
    Push-Location $frontendDirectory
    try {
        $frontendStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        & npm run build
        Assert-LastExitCode -CommandDescription '前端构建'
        Write-Host ('前端构建完成，耗时 ' + [math]::Round($frontendStopwatch.Elapsed.TotalSeconds) + ' 秒')
    } finally {
        Pop-Location
    }
} else {
    Write-Host '已跳过前端构建（-SkipFrontendBuild）'
}
$frontendIndexPath = Join-Path $frontendDirectory 'dist/index.html'
if (-not (Test-Path $frontendIndexPath)) {
    throw ('前端构建产物缺失：' + $frontendIndexPath)
}

# ===== 步骤 2：后端可执行文件打包 =====
Write-BuildStep -StepIndex 2 -Description '后端可执行文件打包（PyInstaller onedir）'
if (-not $SkipBackendBuild) {
    if (-not (Test-Path $pythonExecutablePath)) {
        throw ('未找到后端虚拟环境：' + $pythonExecutablePath)
    }
    $backendBuildArguments = @((Join-Path $backendDirectory 'buildBackend.py'))
    if ($CleanBackend) { $backendBuildArguments += '--clean' }
    & $pythonExecutablePath @backendBuildArguments
    Assert-LastExitCode -CommandDescription '后端打包'
} else {
    Write-Host '已跳过后端打包（-SkipBackendBuild）'
}
$backendExecutablePath = Join-Path $backendDirectory 'dist/runServer/runServer.exe'
if (-not (Test-Path $backendExecutablePath)) {
    throw ('后端打包产物缺失：' + $backendExecutablePath)
}

# ===== 步骤 3：便携运行时准备 =====
Write-BuildStep -StepIndex 3 -Description '便携运行时准备（MariaDB 11.4 + Redis）'
if (-not $SkipRuntimeSetup) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'setupRuntime.ps1')
    Assert-LastExitCode -CommandDescription '便携运行时准备'
} else {
    Write-Host '已跳过便携运行时准备（-SkipRuntimeSetup）'
}
$mariaDbRuntimeDirectory = Join-Path $repoRootDirectory 'Runtime/mariadb'
$redisRuntimeDirectory = Join-Path $repoRootDirectory 'Runtime/redis'
if (-not (Test-Path (Join-Path $mariaDbRuntimeDirectory 'bin/server.dll'))) {
    throw ('便携 MariaDB 缺失：' + $mariaDbRuntimeDirectory)
}
if (-not (Test-Path (Join-Path $redisRuntimeDirectory 'redis-server.exe'))) {
    throw ('便携 Redis 缺失：' + $redisRuntimeDirectory)
}

# ===== 步骤 4：资源 staging（写入 Frontend/src-tauri/resources） =====
Write-BuildStep -StepIndex 4 -Description '资源 staging（后端/运行时/前端 → src-tauri/resources）'
Write-Host '清理并复制后端产物 ...'
Reset-Directory -DirectoryPath $backendResourceDirectory
New-Item -ItemType File -Force -Path (Join-Path $backendResourceDirectory '.gitkeep') | Out-Null
Copy-DirectoryContent -SourceDirectory (Join-Path $backendDirectory 'dist/runServer') -TargetDirectory $backendResourceDirectory

Write-Host '复制便携运行时（MariaDB 全量 + Redis 仅保留可执行文件）...'
Reset-Directory -DirectoryPath $runtimeResourceDirectory
New-Item -ItemType Directory -Force -Path (Join-Path $runtimeResourceDirectory 'mariadb'), (Join-Path $runtimeResourceDirectory 'redis') | Out-Null
Copy-DirectoryContent -SourceDirectory $mariaDbRuntimeDirectory -TargetDirectory (Join-Path $runtimeResourceDirectory 'mariadb')
Copy-Item -Force (Join-Path $redisRuntimeDirectory 'redis-server.exe') -Destination (Join-Path $runtimeResourceDirectory 'redis/redis-server.exe')
if (Test-Path (Join-Path $redisRuntimeDirectory 'redis-cli.exe')) {
    Copy-Item -Force (Join-Path $redisRuntimeDirectory 'redis-cli.exe') -Destination (Join-Path $runtimeResourceDirectory 'redis/redis-cli.exe')
}

Write-Host '复制前端静态资源（供局域网浏览器访问）...'
Reset-Directory -DirectoryPath $frontendResourceDirectory
New-Item -ItemType File -Force -Path (Join-Path $frontendResourceDirectory '.gitkeep') | Out-Null
Copy-DirectoryContent -SourceDirectory (Join-Path $frontendDirectory 'dist') -TargetDirectory $frontendResourceDirectory

$backendResourceSize = Get-DirectorySizeMegabytes -DirectoryPath $backendResourceDirectory
$runtimeResourceSize = Get-DirectorySizeMegabytes -DirectoryPath $runtimeResourceDirectory
$frontendResourceSize = Get-DirectorySizeMegabytes -DirectoryPath $frontendResourceDirectory
Write-Host ('资源就绪：backend=' + $backendResourceSize + ' MB，runtime=' + $runtimeResourceSize + ' MB，frontend=' + $frontendResourceSize + ' MB')

# ===== 步骤 5：Tauri 打包（NSIS） =====
Write-BuildStep -StepIndex 5 -Description 'Tauri 打包（NSIS 安装包）'
$tauriBundleDirectory = Join-Path $frontendDirectory 'src-tauri/target/release/bundle/nsis'
if (-not $SkipTauriBuild) {
    Push-Location $frontendDirectory
    try {
        $tauriStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        & npx tauri build --bundles nsis
        Assert-LastExitCode -CommandDescription 'Tauri 打包'
        Write-Host ('Tauri 打包完成，耗时 ' + [math]::Round($tauriStopwatch.Elapsed.TotalSeconds) + ' 秒')
    } finally {
        Pop-Location
    }
} else {
    Write-Host '已跳过 Tauri 打包（-SkipTauriBuild）'
}
$installerPath = Get-ChildItem -Path $tauriBundleDirectory -Filter '*.exe' -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($null -eq $installerPath) {
    throw ('未找到 Tauri NSIS 安装包：' + $tauriBundleDirectory)
}

# ===== 步骤 6：产物整理（release/） =====
Write-BuildStep -StepIndex 6 -Description '产物整理（release/ 安装包与便携 zip）'
New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
$releaseInstallerPath = Join-Path $releaseDirectory ($productName + '_' + $productVersion + '_x64-setup.exe')
Copy-Item -Force $installerPath.FullName -Destination $releaseInstallerPath
Write-Host ('安装包：' + $releaseInstallerPath + '（' + [math]::Round((Get-Item $releaseInstallerPath).Length / 1MB, 1) + ' MB）')

# Tauri 的 Cargo 产物名为 Cargo 包名（task-management-desktop.exe），安装后由 NSIS 重命名为产品名；
# 便携包内统一复制为重命名为 任务管理系统.exe，与安装版保持一致的目录结构（exe + resources/）
$portableExecutablePath = $null
foreach ($candidateFileName in @(($productName + '.exe'), 'task-management-desktop.exe')) {
    $candidateExecutablePath = Join-Path $frontendDirectory ('src-tauri/target/release/' + $candidateFileName)
    if (Test-Path $candidateExecutablePath) {
        $portableExecutablePath = $candidateExecutablePath
        break
    }
}
if ($null -ne $portableExecutablePath) {
    Copy-Item -Force $portableExecutablePath -Destination (Join-Path $releaseDirectory ($productName + '.exe'))
} else {
    Write-Host '提示：未找到可直接运行的桌面可执行文件，便携包将只包含 resources 目录'
}

if (-not $SkipPortableZip) {
    $portableStagingRoot = Join-Path $releaseDirectory 'portable-staging'
    Reset-Directory -DirectoryPath $portableStagingRoot
    $portableApplicationDirectory = Join-Path $portableStagingRoot 'TaskManagementSystem'
    New-Item -ItemType Directory -Force -Path $portableApplicationDirectory | Out-Null
    if ($null -ne $portableExecutablePath) {
        Copy-Item -Force $portableExecutablePath -Destination (Join-Path $portableApplicationDirectory ($productName + '.exe'))
    }
    Copy-DirectoryContent -SourceDirectory $tauriResourcesDirectory -TargetDirectory (Join-Path $portableApplicationDirectory 'resources')
    $portableZipPath = Join-Path $releaseDirectory ('TaskManagementSystem-portable-' + $productVersion + '.zip')
    Remove-Item -Force -ErrorAction SilentlyContinue $portableZipPath
    Compress-Archive -Path $portableApplicationDirectory -DestinationPath $portableZipPath -CompressionLevel Optimal
    Remove-Item -Recurse -Force $portableStagingRoot
    Write-Host ('便携 zip：' + $portableZipPath + '（' + [math]::Round((Get-Item $portableZipPath).Length / 1MB, 1) + ' MB）')
}

# ===== 汇总 =====
$totalStopwatch.Stop()
Write-Host ''
Write-Host '================ 构建完成 ================'
Write-Host ('总耗时：' + [math]::Round($totalStopwatch.Elapsed.TotalMinutes, 1) + ' 分钟')
Write-Host ('安装包：' + $releaseInstallerPath)
Write-Host ('release 目录：' + $releaseDirectory)
Get-ChildItem $releaseDirectory -File | Select-Object Name, @{Name = '大小(MB)'; Expression = { [math]::Round($_.Length / 1MB, 1) } } | Format-Table -AutoSize
Write-Host '=========================================='