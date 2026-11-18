# 团队分工与文件所有权（协作纪律）

> 目标：多个智能体并行开发时互不覆盖文件。**只允许修改自己负责范围内的文件**；
> 需要修改公共文件（core/*、App.tsx、types/*、api/httpClient.ts、styles/tokens.css、main.py、models/*）
> 时必须先给 Lead 发送消息说明原因，由 Lead 修改或授权。

## 1. 公共基座（Lead 负责，其他成员只读）
- Backend：`runServer.py`、`TaskManagementBackend/main.py`、`config/`、`core/`（database/redisClient/security/exceptions/dependencies/permissions）、`models/`、`schemas/commonSchema.py`、`repositories/baseRepository.py`、`services/baseService.py`、`services/serializationService.py`、`services/initializationService.py`、`utils/`、`tests/conftest.py`、`pytest.ini`、`.env.example`。
- Frontend：`src/main.tsx`、`src/App.tsx`、`src/context/*`、`src/types/*`、`src/api/httpClient.ts`、`src/utils/*`、`src/styles/tokens.css`、`src/styles/global.css`、`vite.config.ts`、`tsconfig.json`、`package.json`、`index.html`、`src/vite-env.d.ts`。
- 根目录：`.gitignore`、`docs/development/*`、`README.md`、`scripts/startLocalRuntime.ps1`、`scripts/stopLocalRuntime.ps1`、`scripts/initializeDatabase.sql`。

## 2. 成员分工

### 账号与团队模块（backendAccountTeammate）
拥有文件：
- `Backend/TaskManagementBackend/controllers/`：authController.py、userController.py、teamController.py、adminController.py
- `Backend/TaskManagementBackend/schemas/`：authSchema.py、userSchema.py、teamSchema.py、adminSchema.py
- `Backend/TaskManagementBackend/repositories/`：userRepository.py、teamRepository.py、adminRepository.py
- `Backend/TaskManagementBackend/services/`：authService.py、userService.py、teamService.py、adminService.py、auditService.py
- `Backend/TaskManagementBackend/core/permissions.py`（可细化实现，**不得修改已有函数名/签名**；如需新增函数可追加）
- `Backend/tests/`：testAuthUser.py、testTeams.py、testAdmin.py
- 测试环境：`TEST_DATABASE_NAME=task_management_test_account`、`TEST_REDIS_DB=14`

### 任务与统计模块（backendTaskTeammate）
拥有文件：
- `controllers/`：taskController.py、todoController.py、dashboardController.py、settingController.py、aiController.py
- `schemas/`：taskSchema.py、todoSchema.py、dashboardSchema.py、settingSchema.py、aiSchema.py
- `repositories/`：taskRepository.py、todoRepository.py、dashboardRepository.py、settingRepository.py
- `services/`：taskService.py、todoService.py、dashboardService.py、settingService.py、aiService.py
- `Backend/tests/`：testTasks.py、testTodosDashboard.py、testSettingsAi.py
- 测试环境：`TEST_DATABASE_NAME=task_management_test_task`、`TEST_REDIS_DB=13`

### 前端基础与设计系统（frontendFoundationTeammate）
拥有文件：
- `Frontend/src/components/ui/`（全部通用组件与 CSS Modules）
- `Frontend/src/components/layout/`（AppShell、Sidebar、TopBar、AuthLayout 等）
- `Frontend/src/components/charts/`（SVG 图表）
- `Frontend/src/pages/auth/`（LoginPage、RegisterPage）
- 可创建 `Frontend/src/test/*`、组件测试 `*.test.tsx`
- 验收：`npx tsc --noEmit`、`npm run build` 通过；登录页可在浏览器使用。

### 前端业务页面（frontendWorkspaceTeammate）
拥有文件：
- `Frontend/src/components/task/`、`Frontend/src/components/team/`
- `Frontend/src/pages/teams/`、`Frontend/src/pages/tasks/`、`Frontend/src/pages/todos/`
- `Frontend/src/hooks/`（通用 hooks）
- 验收：`npx tsc --noEmit`、`npm run build` 通过；页面数据调用 api/* 中已有函数。

### 前端洞察与设置（frontendInsightTeammate）
拥有文件：
- `Frontend/src/pages/dashboard/`、`Frontend/src/pages/profile/`、`Frontend/src/pages/settings/`、`Frontend/src/pages/admin/`、`Frontend/src/pages/sticky/`
- `Frontend/src/components/dashboard/`、`components/profile/`、`components/settings/`、`components/admin/`（按需）
- 验收：`npx tsc --noEmit`、`npm run build` 通过；管理后台调用 api/adminApi.ts。

### 桌面与打包（desktopPackagerTeammate）
拥有文件：
- `Frontend/src-tauri/`（Tauri 2 工程、Rust 进程编排、capabilities、icons）
- `Backend/TaskManagementBackend/desktop/`（runtimeManager.py：托管便携 MariaDB + Redis）
- `Backend/buildBackend.py` / `backendServer.spec`（PyInstaller 打包）
- 根目录 `scripts/` 中除 startLocalRuntime.ps1、stopLocalRuntime.ps1、initializeDatabase.sql 之外的新脚本
- `.github/workflows/`、`packaging/`（NSIS 配置等）
- `Runtime/` 下载与整理（不进入 git）
- 验收：Windows NSIS 安装包产出；`npm run tauri build` 通过；Linux/macOS 构建脚本 + CI 可复现。

## 3. 集成规则
1. 接口以 `docs/development/apiContract.md` 为准；数据库以 `databaseContract.md` 为准；前端设计以 `frontendDesignContract.md` 为准。
2. 后端控制器必须先通过 `core/permissions.py` 校验权限；错误统一抛 `AppException`。
3. 前端页面必须使用 `components/ui` 已有组件（C 提供）与 `api/*` 已有函数；不允许直接 fetch。
4. 新增公共函数（utils/hooks/api/组件）需在完成汇报中列出，Lead 汇总。
5. 每个文件完成后运行测试；后端 `pytest tests -q`，前端 `npx tsc --noEmit`。
6. 不执行 git commit/push；不修改 docs/development 契约；不安装新依赖（需要时先问 Lead）。
7. 完成后向 Lead 发送消息：完成文件清单、测试命令与结果、遗留问题/需要 Lead 处理的事项。

## 4. 并行测试库约定
后端成员运行测试前在 PowerShell 设置：
```powershell
$env:TEST_DATABASE_NAME='task_management_test_account'   # 任务模块用 task_management_test_task
$env:TEST_REDIS_DB='14'                                  # 任务模块用 13
cd Backend; .\.venv\Scripts\python.exe -m pytest tests -q
```
本地开发运行时（MySQL 3307 / Redis 6380）由 Lead 托管，若不可用请通知 Lead。

## 5. v1.1 功能分工与文件所有权

> 公共基座（v1.1 新增）由 Lead 维护：models/collaborationModel.py、models/notificationModel.py、models/taskModel.py、
> core/migrationService.py、core/database.py、config/settings.py、services/notificationService.py、
> controllers/notificationController.py、services/aiAssignmentService.py（接口层）、services/taskService.py、
> services/todoService.py、repositories/taskRepository.py、schemas/taskSchema.py、schemas/notificationSchema.py、
> Frontend/src/types/*（v1.1 扩展）、Frontend/src/App.tsx、Frontend/src/main.tsx、styles/tokens.css。

### backend-collaboration（task-7）
拥有：controllers/collaborationController.py、subTeamController.py；schemas/collaborationSchema.py、subTeamSchema.py；
repositories/collaborationRepository.py、subTeamRepository.py；services/subTeamService.py、
collaborationService.py、collaborationTaskService.py、collaborationPermissionService.py；
tests/testSubTeams.py、testCollaborations.py、testCollaborationTasks.py。
测试环境：TEST_DATABASE_NAME=task_management_test_collab、TEST_REDIS_DB=9。

### backend-ai（task-8）
拥有：services/aiAssignmentService.py（完整实现）、localRecommendationEngine.py、llmRecommendationClient.py；
services/aiService.py（升级）、controllers/aiController.py（升级）、schemas/aiSchema.py（升级）；
tests/testAiAssignment.py、testAiLlm.py、testAiNotificationIntegration.py。
测试环境：TEST_DATABASE_NAME=task_management_test_ai、TEST_REDIS_DB=8。

### frontend-collaboration（task-9）
拥有：pages/collaborations/**、pages/notifications/**（与 frontend-ai 共同验收，文件由 frontend-ai 建）、
components/collaboration/**、components/subteam/**、TeamDetailPage 新增 Tab 组件、
components/task/TaskCard.tsx、TaskDetailPage 协作逻辑组件、ReviewPanel.tsx、
types/collaboration.ts、api/collaborationApi.ts、api/teamApi.ts（子团队接口）、
components/layout/navigationConfig.ts（新增「协作」导航）。
禁止修改：App.tsx（Lead 冻结）、components/ui/**、context/**、api/httpClient.ts、其他成员文件。

### frontend-ai（task-10）
拥有：components/notification/**、pages/notifications/**、components/task/TaskForm.tsx、TaskBasicFields.tsx、
TaskTargetSelector.tsx、AiRecommendPanel.tsx、components/layout/TopBar.tsx（通知铃铛接入）、
types/ai.ts、types/notification.ts、types/todo.ts（扩展）、api/aiApi.ts、api/notificationApi.ts、hooks/useNotificationPolling.ts。
禁止修改：App.tsx、components/ui/**、context/**、api/httpClient.ts、其他成员文件。

### desktop-packager（task-11，后置）
v1.1.0 版本号更新、Windows 安装包重建、安装包验收、文档打包版本信息；
本轮包构建在前后端全部完成并由 Lead 联调/E2E 通过后启动。

## 6. v1.1.1 AI 配置与连通性测试分工

> 目标：把 AI 配置与连通性测试放进「系统设置」页（本轮不重新打包安装包）。

| 角色 | 负责文件 |
| --- | --- |
| Lead | models/systemSettingModel.py、models/__init__.py、main.py 路由注册、docs 契约、Frontend/src/types/aiConfig.ts、集成/E2E 测试、文档汇总 |
| backend-ai（task-11） | controllers/aiConfigController.py、schemas/aiConfigSchema.py、services/aiConfigService.py、repositories/systemSettingRepository.py、tests/testAiConfig.py；改造 aiAssignmentService/localRecommendationEngine/llmRecommendationClient/aiService 使用有效配置及相关旧测试 |
| 前端子智能体 | components/settings/AiConfigSection.tsx(.module.css)、pages/settings/SettingsPage.tsx、api/settingApi.ts（追加 AI 配置接口） |
| 公共基座（只读，Lead 维护） | core/**、config/settings.py、models（除 SystemSetting 外）、taskService、notification*、Frontend/src/App.tsx、components/ui/**、context/**、api/httpClient.ts、styles/** |

测试环境：`TEST_DATABASE_NAME=task_management_test_ai`、`TEST_REDIS_DB=8`（backend-ai）；Lead 用 `task_management_test_lead`/`TEST_REDIS_DB=12` 跑全量。
