# resources 目录说明

本目录用于 Tauri 打包时随安装包分发的资源，全部在 `scripts/buildWindowsInstaller.ps1` 中由构建脚本写入，
**不提交到 git**（仅保留 .gitkeep 占位，保证未执行 staging 时 `npm run tauri build` 仍可完成编译）：

- `backend/`：PyInstaller onedir 打包产物 `Backend/dist/runServer/` 的全部内容，入口为 `runServer.exe`；
- `runtime/`：便携运行时，`mariadb/` 为裁剪后的 MariaDB 11.4 winx64，`redis/` 为 tporadowski Redis；
- `frontend/`：前端构建产物 `Frontend/dist/`，由桌面端后端托管，供局域网浏览器访问。

发布模式启动时，Rust 外壳通过环境变量把 `runtime/`、`frontend/` 路径传递给后端可执行文件。
