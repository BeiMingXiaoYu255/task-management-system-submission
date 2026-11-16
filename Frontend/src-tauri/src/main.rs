// 发布模式隐藏 Windows 控制台窗口；开发模式保留控制台便于查看日志，切勿删除本属性。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

/// 程序入口：委托给库模块的 run 函数，保持入口文件精简。
fn main() {
    task_management_desktop_lib::run();
}
