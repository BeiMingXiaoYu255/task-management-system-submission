# 任务管理系统（Task Management System）

一款黑白极简、轻量级的团队任务管理桌面软件。Tauri 2 桌面壳 + React/TypeScript 前端 + FastAPI 后端，
内置便携 MariaDB 与 Redis，开箱即用；支持局域网多设备协同。

> 当前版本：**v1.2.2**（v1.1.0 新增团队/子团队协作、跨团队任务双审核、AI 自动分配与站内通知中心；v1.1.1 新增系统设置中的 AI 配置与连通性测试；v1.2.0 界面全英文；v1.2.1 修复便签小窗打开后卡死/无法关闭的问题）
> v1.0 安装版可直接覆盖升级，数据库结构与用户数据自动迁移。

## 功能

- 用户注册登录、全局权限分级（超级用户 / 全局管理员 / 普通用户）、团队认证
- 团队管理：创建、加入方式（自由/审核/邀请码）、成员级别自定义、子管理员、转让、踢人、入团审核
- 任务管理：指定成员或级别范围发布、必须接受/选择性接受、优先级、截止时间
- 待办清单：自动生成个人待办、排序筛选、接受/完成、便签小窗
- 任务审核：成员提交完成 → 发布者审核 → 通过归档 / 驳回重做
- 个人资料：简介与技能标签，上级可查看下级非隐私信息
- 仪表盘：待办/本周完成/逾期统计、优先级与状态分布、一周趋势、团队维度
- 系统设置：浅色/深色主题（低饱和灰阶）、字号字体、修改密码、注销账号
- 管理后台：用户/团队管理、团队认证、数据库表直管（审计留痕）
- **v1.1 团队协作**：团队/子团队之间建立协作（双方管理员确认 + 指定对接人），跨团队任务由接收方对接人确认、
  指派执行人，经过「接收方对接人审核 → 发起方发布者审核」双审核后归档
- **v1.1 子团队**：父团队内一层分组、复用父团队级别，设子负责人；子团队可作为协作单位派发/承接任务
- **v1.1 AI 自动分配**：完整移植团队提供的 AI 模块——本地规则引擎（技能命中率 × 100 − 负载惩罚）、
  可选 LLM OpenAI 兼容链路（DeepSeek/GLM/OpenAI）、四种调度模式与自动回退、发布任务一键自动选人，
  无匹配时保留待指派并支持手动指派
- **v1.1.1 AI 配置（系统设置）**：全局管理员可在「设置 → AI 配置」中直接修改 LLM 地址/Key/模型、
  调度模式、匹配阈值与负载惩罚，并一键测试本地引擎/LLM 连通性（显示延迟与中文错误）；普通用户只读
- **v1.2.0 全英文界面**：所有页面、组件、提示、校验、枚举与通知/错误文案均改为英文；新增 AST 级中文字符检测脚本
  （`Frontend/checkEnglishUi.mjs` 与 `scripts/checkBackendEnglish.py`）保证无中文 UI 文案；代码注释与开发文档仍保留中文
- **v1.2.1 便签小窗修复**：修复桌面版点击 Sticky Notes 后应用卡死、便签窗无法关闭的问题
  （Tauri 窗口创建改异步 + 初始化路由修复 + 显式 Close 按钮/Esc 关闭）
- **v1.2.2 视觉验收改进**：修复 Toast 提示遮挡顶栏用户菜单、便签小窗 380px 宽度下头部拥挤换行；新增真人式全功能测试（Web 33 项、桌面 29 项）与 QA 测试数据脚本
- **v1.1 通知中心**：任务分配、协作申请/确认、双审核等事件自动通知，顶栏铃铛未读数轮询 + 通知中心
- 局域网访问：其他设备浏览器直接访问同一系统

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 桌面壳 | Tauri 2（Rust + 系统 WebView） |
| 前端 | React 18、TypeScript、Vite 5、React Router 6、原生 CSS Modules、SVG 图表 |
| 后端 | FastAPI、Python 3.11、SQLAlchemy 2、Pydantic 2、JWT、bcrypt |
| 数据库 | MariaDB 11（MySQL 协议兼容；安装包内置便携版） |
| 缓存 | Redis（登录限流 / token 黑名单；安装包内置便携版） |
| 打包 | PyInstaller + Tauri Bundler（NSIS / AppImage / dmg） |

## 快速开始（开发环境）

```powershell
# 1. 启动本地 MySQL(3307) 与 Redis(6380) 开发运行时
.\scripts\startLocalRuntime.ps1

# 2. 后端
cd Backend
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn runServer:app --host 0.0.0.0 --port 8765 --reload

# 3. 前端（另开终端）
cd Frontend
npm install
npm run dev
# 浏览器打开 http://127.0.0.1:5173

# 4. 可选：写入演示数据
cd Backend
.\.venv\Scripts\python.exe scripts\seedDemoData.py
```

内置超级用户：`superAdmin` / `SuperAdmin@123`（首次登录后请修改密码）。
演示账号：`demoAdmin` / `developerA` / `designerB` / `testerC` / `productManager`，密码均为 `Demo@123456`。
演示数据包含 2 个团队、3 个子团队、3 条协作关系（含待确认）、协作任务与 AI 自动分配示例、演示通知。
AI 默认使用本地规则引擎；如需 LLM 排序，推荐在「设置 → AI 配置」中填写并测试连通性，也支持环境变量
`llmBaseUrl`、`llmApiKey`、`llmModel`（详见 docs/development/aiModuleContract.md）。

## 构建与安装

Windows 一键构建（前端 → 后端 PyInstaller → 便携 MariaDB/Redis → NSIS 安装包 + 便携 zip）：

```powershell
.\scripts\buildWindowsInstaller.ps1
```

已构建产物（`release/`）：

| 产物 | 大小 | 说明 |
| --- | --- | --- |
| `任务管理系统_1.2.2_x64-setup.exe` | 31.13 MB | Windows NSIS 安装包（内置便携 MariaDB/Redis/后端/前端，开箱即用） |
| `TaskManagementSystem-portable-1.2.2.zip` | 40.57 MB | Windows 便携版（解压即运行） |
| `任务管理系统.exe` | 8.90 MB | Tauri 桌面主程序 |
| `任务管理系统_1.0.0_x64-setup.exe` | 30.95 MB | 旧版本（保留用于升级验证） |

实机验收（详见 [测试文档](docs/测试文档.md)）：全新安装 16/16、便签小窗 15/15、便携版 16/16、
v1.0→v1.2.2 覆盖升级 24/24、桌面新样式检查 21/21；另完成真人式全功能测试（Web 33/33、桌面 29/29）与视觉验收，
测试数据账号见 [docs/qa/testAccounts.md](docs/qa/testAccounts.md)，报告见 [docs/qa/qaAcceptanceReport.md](docs/qa/qaAcceptanceReport.md)。
Linux/macOS 构建脚本与 GitHub Actions 三平台 CI 见 `scripts/buildInstallers.sh` 与 `.github/workflows/build-installers.yml`。

## 文档

- [项目开发文档](docs/项目开发文档.md)
- [测试文档](docs/测试文档.md)
- [接口文档](docs/接口文档.md)
- [安装说明](docs/项目安装说明.md)
- [界面截图](docs/界面截图.md)
- 开发契约：`docs/development/`

## 目录结构

```
Backend/     FastAPI 后端（MVC 分层）
Frontend/    React 前端 + Tauri 2 桌面壳
docs/        开发文档 / 测试文档 / 接口文档 / 安装说明 / 开发契约
scripts/     本地运行时、种子数据、构建脚本
packaging/   安装包配置与 CI
release/     安装包产物（构建后生成）
```

## 测试

```powershell
cd Backend; .\.venv\Scripts\python.exe -m pytest tests -q      # v1.2.0 全量 136 个用例
cd Frontend; npx tsc --noEmit; npm run build; npm test         # 类型检查 / 构建 / 14 个单元测试
cd Frontend; npx playwright test                               # 浏览器端到端 21 个用例（需后端 8765 托管 dist）
cd Frontend; node qa/walkthrough.mjs                           # 真人式全功能测试 + 截图（需 QA 测试数据）
```

## 许可证

内部项目，仅用于团队协作与学习用途。
