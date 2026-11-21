# v1.2.x 真人式全功能测试与视觉验收报告

> 执行时间：2026-11-25 21:28 - 22:26（本地时间）
> 被测对象：Windows 安装版任务管理系统 **v1.2.2**（安装包实机安装；后端 health=1.2.2，LAN http://10.5.61.61:8765）
> 最终安装包：`release/任务管理系统_1.2.2_x64-setup.exe`（全新安装 16/16、便签 15/15、v1.0→v1.2.2 升级 24/24、桌面样式 21/21 通过）
> 测试方式：Windows UI Automation 驱动真实桌面应用 + Playwright(Edge) 真人式操作 LAN Web 界面 + HTTP API 数据准备与断言
> 测试数据：`scripts/seedQaAcceptanceData.py` 生成的 11 个账号 / 3 团队 / 15 任务 / 2 子团队 / 2 协作 / 3 协作任务 / 通知与 AI 配置
> 账号清单：[testAccounts.md](testAccounts.md)；数据摘要：[testDataSummary.md](testDataSummary.md)；执行脚本：`Frontend/qa/walkthrough.mjs`、`scripts/qaDesktopAcceptance.ps1`

## 1. 测试结果总览

| 测试套件 | 检查项 | 结果 |
| --- | --- | --- |
| 桌面端真人操作（UI Automation，qaMemberA1） | 登录、7 个侧边栏页面渲染、深浅色主题、便签窗打开/关闭/Esc/不卡死、退出清理 | **29 / 29 通过** |
| Web 全功能真人操作（Playwright，多角色） | 见第 2 节功能矩阵 | **33 / 33 通过** |
| 浏览器控制台 | 未预期错误 | 0（2 条为错误密码/禁用账号负向用例的预期 401/403） |
| 测试数据 API 校验 | 账号/团队/任务/协作/通知/AI 配置与统计 | 全部符合预期（脚本连续 4 次执行幂等） |

## 2. 功能矩阵与操作记录

| 功能域 | 实际操作 | 结果 |
| --- | --- | --- |
| 认证 | superAdmin/团队管理员/成员登录；错误密码提示；禁用账号拒绝；新用户注册；退出登录 | 通过 |
| 仪表盘 | 全局管理员/团队管理员/成员视角渲染；统计卡、优先级/状态分布、7 日趋势、团队统计、深色模式 | 通过 |
| 团队 | 团队列表、进入团队、概览/任务/子团队/协作/成员/级别/设置 7 个 Tab；入团申请审批；成员/级别展示 | 通过 |
| 团队管理 | 入团申请通过（qaApplicantAlpha 加入 QA Alpha Team）；管理后台团队认证（审计日志 admin.team.certification 记录 3 条） | 通过 |
| 任务 | 任务列表筛选/分页；发布任务（表单校验、AI 推荐、开启 AI 自动分配、发布成功并验证任务入库）；取消任务（自动创建的 QA 任务）；任务详情（状态、进度、审核区） | 通过 |
| 任务流转 | 成员接受待办 → 提交完成 → 任务进入待审核；发布者视角显示待审核数据 | 通过 |
| 待办/便签 | 待办列表筛选、接受/提交完成；桌面便签小窗打开、显示 4 条待办、主窗口不卡死、Close/Esc 关闭、重复打开 | 通过 |
| 协作 | 协作中心三个 Tab；接收方管理员确认待确认协作（pending→active，API 校验 pending=0/active=2）；协作目录；协作任务详情 | 通过 |
| 协作任务 | 接收方对接人 Process Collaboration Task：勾选执行人、填写意见、确认接单（API 校验 assignments=1）；接收方审核 Approve（进入 Initiator Review，审核历史 1 条） | 通过 |
| 通知 | 通知中心渲染、未读数、空态/已读状态 | 通过 |
| 个人资料 | 资料页渲染；编辑 Bio 并保存（toast 成功）；技能标签/团队与角色展示 | 通过 |
| 设置 | 系统设置、AI 配置（查看/保存/本地连通性测试）、字号 Large/Medium、深浅色主题、系统信息、LAN 地址 | 通过 |
| AI | AI 配置卡片、Test Connectivity（本地引擎可用/LLM 未配置）、AI Assignee Recommendation、开启 AI 自动分配发布任务并生成执行人 | 通过 |
| 管理后台 | 全局管理员进入 Admin Console；Overview/Users/Teams/Database/Audit 四个 Tab；团队认证操作 | 通过 |
| 局域网 | 通过 http://10.5.61.61:8765 访问登录页、登录、进入仪表盘 | 通过 |
| 响应式 | 900×800 窄屏：侧边栏收起、卡片单列、无横向溢出 | 通过 |
| 桌面客户端 | 桌面窗口登录、页面导航、主题切换、便签小窗、关闭主窗口后进程/内置后端/数据库/缓存退出 | 通过 |

## 3. 视觉验收

截图目录：`docs/screenshots/qa-acceptance/`（Web 端 40+ 张、桌面端 10 张），覆盖浅色/深色、数据丰富/空态、窄屏、弹窗、审批、协作任务等场景。

### 3.1 发现并修复的问题（源码）
1. **Toast 提示遮挡顶栏用户菜单**：成功/错误提示固定于右上角 top:20px，会覆盖 LAN/通知/主题/用户菜单。
   修复：提示容器下移至 top:76px（`ToastContext.module.css`），已通过浏览器截图复核。
2. **便签小窗 380px 宽度下头部拥挤**：标题、计数与 Refresh/Main Window/Close 挤在一行，计数换行。
   修复：头部改为两行布局（标题+计数一行、操作按钮一行），计数不换行（`StickyTodoPage.module.css`）；已通过浏览器 400px 截图复核。

> 说明：桌面窗口加载的是打包时内嵌在前端产物（Tauri embedded assets），热更新 `resources/frontend` 只影响 LAN 网页；
> 因此上述修复需要重新构建安装包（v1.2.2）才能在桌面客户端体现。浏览器侧修复已生效并截图。

### 3.2 其他视觉观察
- 空态/加载态/深色模式、表格与表单在 1440px 与 900px 下布局正常，无文字溢出或错位。
- 安装版验收脚本截图（desktop-*）中存在外部输入法/工具悬浮窗与窗口边缘截取内容，属于操作系统环境叠加，非应用 UI 问题。
- 测试过程中大量成功 toast 属操作反馈，非缺陷。

## 4. 测试数据状态说明（QA 操作后）
QA 操作会消耗部分"待处理"数据：待入团申请已通过、待确认协作已确认、协作任务已接单/接收方审核通过、成员待办已接受/提交、QA Gamma 团队已认证；另注册了若干 `qaWalk*` 临时账号、创建并取消了若干 QA 测试任务。
重新执行 `python scripts/seedQaAcceptanceData.py` 可补齐缺失数据；如需完全干净数据集，可清空应用数据目录后重装并重新执行种子脚本。

## 5. 未覆盖项
- 真实 LLM API 连通性/推荐/自动分配（缺少用户提供的真实 API 凭据；本地引擎与 mock 全链路已验证，见测试文档第 13 章）。
- 修改密码/注销账号的界面提交（涉及账号数据销毁，未在验收账号上执行；接口与安全测试见测试文档）。
- Linux/macOS 实机；安装包代码签名。

## 6. 复现步骤
```powershell
# 1. 安装并启动应用（安装版）
# 2. 创建 QA 测试数据
python scripts/seedQaAcceptanceData.py --base-api http://127.0.0.1:8765
# 3. Web 真人式全功能测试 + 截图
cd Frontend; node qa/walkthrough.mjs
# 4. 桌面端真人操作测试 + 截图
powershell -File scripts/qaDesktopAcceptance.ps1 -Username qaMemberA1 -Password Qa@123456
```
