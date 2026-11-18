#requires -Version 5.1
<#
.SYNOPSIS
    验收脚本窗口辅助函数：通过 Win32 API 精确操作 Tauri 主窗口。

.DESCRIPTION
    PowerShell 的 Process.MainWindowHandle 在 Tauri 应用中可能选中 IME/事件目标等隐藏窗口（实测会误选），
    因此改用 EnumWindows 按类名 Tauri Window 定位主窗口，并用 PostMessage(WM_CLOSE) 模拟用户点击关闭按钮。
#>
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class Win32WindowEnumerator
{
    public delegate bool EnumWindowsCallback(IntPtr windowHandle, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsCallback callback, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr windowHandle, out uint processId);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr windowHandle, StringBuilder text, int maxCount);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr windowHandle, StringBuilder className, int maxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr windowHandle);
    [DllImport("user32.dll", SetLastError = true)] public static extern bool PostMessage(IntPtr windowHandle, uint message, IntPtr wParam, IntPtr lParam);

    public static List<IntPtr> CollectProcessWindows(uint targetProcessId)
    {
        List<IntPtr> windowHandleList = new List<IntPtr>();
        EnumWindows((windowHandle, lParam) =>
        {
            uint windowProcessId;
            GetWindowThreadProcessId(windowHandle, out windowProcessId);
            if (windowProcessId == targetProcessId) { windowHandleList.Add(windowHandle); }
            return true;
        }, IntPtr.Zero);
        return windowHandleList;
    }
}
'@

function Find-TauriMainWindow {
    <#
    .SYNOPSIS
        枚举进程全部顶层窗口，返回类名为 Tauri Window 且可见的主窗口句柄（找不到返回 Zero）。
    #>
    param([int]$ProcessId)
    $windowHandleList = [Win32WindowEnumerator]::CollectProcessWindows([uint32]$ProcessId)
    foreach ($windowHandle in $windowHandleList) {
        $classNameBuilder = New-Object System.Text.StringBuilder 256
        [void][Win32WindowEnumerator]::GetClassName($windowHandle, $classNameBuilder, 256)
        if ($classNameBuilder.ToString() -eq 'Tauri Window' -and [Win32WindowEnumerator]::IsWindowVisible($windowHandle)) {
            return $windowHandle
        }
    }
    return [IntPtr]::Zero
}
