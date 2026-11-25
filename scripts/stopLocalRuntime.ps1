#requires -Version 5.1
<#
.SYNOPSIS
    停止本地开发运行时（3307 MySQL 与 6380 Redis）。

.DESCRIPTION
    只停止本项目的开发实例，不会影响系统服务 MySQL80 与其他 Redis 实例。
#>
$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $PSScriptRoot

function Stop-ProcessOnPort {
    <#
    .SYNOPSIS
        停止监听指定端口的进程。
    #>
    param([int]$Port, [string]$DisplayName)
    $connections = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($null -eq $connections) {
        Write-Host ('[' + $DisplayName + '] 端口 ' + $Port + ' 未在监听')
        return
    }
    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host ('[' + $DisplayName + '] 已停止进程 ' + $processId)
        } catch {
            Write-Host ('[' + $DisplayName + '] 停止进程 ' + $processId + ' 失败：' + $_.Exception.Message)
        }
    }
}

Stop-ProcessOnPort -Port 3307 -DisplayName 'MySQL'
Stop-ProcessOnPort -Port 6380 -DisplayName 'Redis'
Write-Host '本地开发运行时已停止'