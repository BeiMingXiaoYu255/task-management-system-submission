# 桌面打包与安装（packaging）

本目录包含 Windows/Linux/macOS 三平台安装包构建说明、验收脚本与系统运行时初始化脚本。
桌面外壳为 Tauri 2 工程（`Frontend/src-tauri`），发布模式下随安装包分发便携 MariaDB、Redis 与
PyInstaller 打包的后端可执行文件；开发模式不托管任何进程，由开发者手动运行后端。

## 1. 目录与文件

| 路径 | 说明 |
| --- | --- |
| `Frontend/src-tauri/` | Tauri 2 外壳：窗口、Rust 进程编排、capabilities、icons、资源占位 |
| `Backend/TaskManagementBackend/desktop/` | 便携运行时管理器：MariaDB/Redis 生命周期、配置注入、退出监控 |
| `Backend/buildBackend.py` / `Backend/backendServer.spec` | PyInstaller onedir 打包后端（产物 `Backend/dist/runServer/runServer.exe`） |
| `scripts/setupRuntime.ps1` | 下载并裁剪便携 MariaDB 11.4 + Redis 到 `Runtime/` |
| `scripts/buildWindowsInstaller.ps1` | **Windows 一键构建**：前端 → 后端 → 运行时 → staging → NSIS 安装包 + 便携 zip |
| `scripts/buildInstallers.sh` | Linux AppImage/deb 与 macOS dmg 一键构建 |
| `packaging/verifyInstalledApp.ps1` | Windows 安装包安装/启动/登录/局域网/卸载全链路验收脚本 |
| `packaging/setupSystemRuntime.sh` | Linux/macOS 系统 MariaDB/Redis 初始化（建库建号） |
| `.github/workflows/build-installers.yml` | 三平台矩阵构建并上传安装包 artifact |

## 2. Windows 构建（推荐一键脚本）

前置：Node 24+、Rust 1.90+ MSVC、VS Build Tools（含 Windows SDK）、`Backend/.venv`（已装 requirements-dev）、WebView2（Win10+ 自带）。

```powershell
# 完整构建（首次会下载 MariaDB 约 93MB 与编译 Rust 依赖，耗时较长）
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/buildWindowsInstaller.ps1

# 跳过已完成的步骤快速重建
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/buildWindowsInstaller.ps1 -SkipFrontendBuild -SkipBackendBuild -SkipRuntimeSetup
```

构建产物（`release/`，已在 .gitignore 中忽略）：

| 产物 | 说明 |
| --- | --- |
| `任务管理系统_1.2.2_x64-setup.exe` | NSIS 安装包（当前用户安装，无需管理员权限；文件名随版本号自动生成） |
| `TaskManagementSystem-portable-1.2.2.zip` | 便携 zip（`TaskManagementSystem/任务管理系统.exe` + `resources/`，解压即用，可选） |

> 版本号说明：构建脚本自动读取 `Frontend/src-tauri/tauri.conf.json` 的 `productName`/ `version` 生成产物名，
> 发布新版本只需更新各工程版本号（tauri.conf.json / Cargo.toml / package.json / 后端 settings），无需修改打包脚本。
>
> 说明：`npm run tauri build` 本身可复现安装包，但 `Frontend/src-tauri/resources` 下的
> backend/runtime/frontend 三个目录必须先由 `scripts/buildWindowsInstaller.ps1` staging；
> 直接执行前请至少运行一次一键脚本（仓库内保留 .gitkeep 占位，未 staging 时编译可过但发布版无法启动后端）。

单独步骤命令：

```powershell
cd Frontend; npm run build                                   # 前端生产构建
Backend/.venv/Scripts/python.exe Backend/buildBackend.py      # 后端 PyInstaller 打包
powershell -File scripts/setupRuntime.ps1                     # 便携 MariaDB/Redis 准备
cd Frontend; npx tauri build --bundles nsis                   # Tauri NSIS 安装包
```

## 3. 安装版运行机制

### 3.1 目录结构

```
%LOCALAPPDATA%\任务管理系统\                    # currentUser 安装目录（NSIS）
  task-management-desktop.exe                   # Tauri 外壳（WebView2，沿用 Cargo 包名）
  uninstall.exe
  resources\
    backend\runServer.exe + _internal\...       # PyInstaller 后端（含前端 dist）
    runtime\mariadb\...                        # 裁剪版 MariaDB 11.4（约 42MB）
    runtime\redis\redis-server.exe             # 便携 Redis
    frontend\index.html + assets\...           # 前端静态资源（局域网访问）
```

应用数据目录：`%APPDATA%\TaskManagementSystem\`

```
runtimeConfig.json     # 本地配置：随机数据库密码、JWT 密钥、实际端口（首次启动生成）
logs\
  desktop.log          # Tauri 外壳日志（后端启动/退出过程）
  backend.log          # 后端与运行时管理器日志（uvicorn、MariaDB、Redis）
  mariadb.log          # MariaDB 服务日志（启动失败排查）
  backend-stdout.log?  # 后端标准输出（实际合并写入 backend.log）
mariadb-data\          # 内置 MariaDB 数据目录（首次启动自动初始化）
redis-data\            # 内置 Redis 数据目录
```

### 3.2 启动流程

1. Tauri 外壳以 `visible=false` 创建主窗口；
2. 外壳在 8765..8775 选择空闲 HTTP 端口，启动 `resources/backend/runServer.exe --manage-runtime --port <port>`；
3. 运行时管理器加载/生成本地配置 → 启动便携 MariaDB（首次初始化数据目录、建库建号）→ 启动便携 Redis；
4. 注入 `databaseUrl/redisUrl/jwtSecret/frontendDistPath/port` 环境变量后启动 FastAPI；
5. 外壳轮询 `http://127.0.0.1:<port>/api/v1/health`，就绪后显示主窗口；超时（180 秒）或后端提前退出时显示中文错误页；
6. 浏览器/局域网访问 `http://<本机IP>:<port>/` 由后端直接托管前端静态资源；
7. 关闭主窗口/退出应用 → 关闭后端标准输入触发 EOF 优雅停机 → 停止 Redis、MariaDB；超时 20 秒强制结束进程树。

### 3.3 端口约定与自动递增

| 服务 | 默认端口 | 冲突处理 |
| --- | --- | --- |
| 后端 HTTP | 8765 | 外壳在 8765..8775 自动递增并把实际端口传给前端 |
| MariaDB | 3307 | 运行时管理器自动递增寻找空闲端口，并写入 runtimeConfig.json |
| Redis | 6380 | 同上（Redis 不可用时后端降级内存缓存，不阻断启动） |

多实例启动时，若检测到已有实例的数据库/缓存可连接（配置匹配），会直接复用而不重复启动。

### 3.4 排障

- **窗口一直不出现**：查看 `%APPDATA%\TaskManagementSystem\logs\desktop.log` 与 `backend.log`；
  首次启动初始化 MariaDB 需要数十秒，属正常现象；
- **启动错误页**：按页面提示查看日志；常见原因是端口被占用、便携运行时缺失、数据目录无写权限；
- **忘记超级管理员密码**：默认 `superAdmin / SuperAdmin@123`（首次登录后请修改）；
- **重置数据**：关闭应用后删除 `%APPDATA%\TaskManagementSystem\mariadb-data` 与 `runtimeConfig.json`，下次启动重新初始化。

## 4. Windows 安装包验收

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/verifyInstalledApp.ps1
```

脚本自动完成：静默安装 → 检查安装产物/桌面快捷方式/内置资源 → 启动应用 → 等待窗口可见与后端健康 →
superAdmin 登录与 `/auth/me` → 局域网 IP 访问前端页面 → 关闭应用验证端口释放与优雅停机日志 → 静默卸载，
输出中文结果表并以退出码表示是否全部通过。可用 `-SkipInstall` / `-SkipUninstall` 调试已安装环境。

## 5. Linux 与 macOS

### 5.1 构建

```bash
# Linux（Ubuntu 22.04）：AppImage + deb
bash scripts/buildInstallers.sh

# macOS：dmg
bash scripts/buildInstallers.sh --bundles dmg
```

Linux 依赖：`libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev patchelf libssl-dev`；
macOS 需 Xcode Command Line Tools。后端由 PyInstaller 按当前平台打包（产物无扩展名 `runServer`），
前端与后端同样打入 Tauri resources。

### 5.2 运行时（不内置便携数据库）

Linux/macOS 安装包**不内置** MariaDB 与 Redis（体积与系统兼容性考虑），安装后需：

```bash
# Ubuntu/Debian
sudo apt-get install -y mariadb-server redis-server
sudo bash packaging/setupSystemRuntime.sh    # 创建 task_management 库与 taskadmin/taskadmin123 账号

# macOS
brew install mariadb redis
brew services start mariadb && brew services start redis
sudo bash packaging/setupSystemRuntime.sh
```

应用会自动探测系统服务端口：MySQL 优先 3307 再 3306，Redis 优先 6380 再 6379；
也可通过环境变量覆盖：`TASK_MANAGEMENT_DATABASE_URL` / `TASK_MANAGEMENT_REDIS_URL`。

## 6. CI

`.github/workflows/build-installers.yml` 在 GitHub Actions 三平台矩阵（windows-latest / ubuntu-22.04 / macos-latest）
执行构建并上传 artifact：Windows NSIS 安装包、Linux AppImage+deb、macOS dmg。
触发方式：手动 `workflow_dispatch` 或推送 `v*` 标签。CI 内不执行安装验收（无 GUI 环境），
Windows 安装验收请在本地运行 `packaging/verifyInstalledApp.ps1`。

## 7. 常见构建问题

| 问题 | 处理 |
| --- | --- |
| `cargo build` 报 tauri.conf.json 字段不识别 | 清空 `Frontend/src-tauri/target` 或执行 `cargo update` 对齐 tauri-build 版本 |
| `tauri build` 提示 resources 缺失 | 先执行 `scripts/buildWindowsInstaller.ps1` 完成 staging |
| PyInstaller 报缺少前端产物 | 先 `cd Frontend; npm run build` |
| 安装包体积过大 | 确认 `Runtime/mariadb` 为裁剪版（约 42MB，不应包含 `.pdb`/include/mysql-test） |
| 杀毒软件拦截 | NSIS 安装包未签名；企业环境需加白名单或自行签名 |