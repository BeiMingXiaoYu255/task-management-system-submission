# 前端设计契约（唯一权威）

> 技术栈：React 18 + TypeScript + Vite 5 + React Router 6 + 原生 CSS Modules。
> **不引入任何 UI 组件库 / 图标库 / 图表库 / 状态管理库**；图标用内联 SVG 组件，图表用 SVG 手写。
> 目标：极简黑白、无多余装饰、组件可复用、每个文件 ≤300 行。

## 1. 目录结构（Frontend/src）
```
src/
  main.tsx                 # 应用入口（Lead 冻结）
  App.tsx                  # 路由表（Lead 冻结，页面实现者不得修改路由路径）
  styles/
    tokens.css             # 设计变量（Lead 冻结：颜色/间距/字号/圆角/阴影）
    global.css             # 全局重置与基础样式（Lead 冻结）
  types/                   # 类型定义，与接口契约一一对应
    common.ts  auth.ts  user.ts  team.ts  task.ts  todo.ts  dashboard.ts  setting.ts  admin.ts  ai.ts
  api/
    httpClient.ts          # fetch 封装（Lead 冻结：request<T>、ApiError、token 管理）
    authApi.ts  userApi.ts  teamApi.ts  taskApi.ts  todoApi.ts
    dashboardApi.ts  settingApi.ts  adminApi.ts  aiApi.ts  systemApi.ts
  context/
    AuthContext.tsx        # 当前用户、登录/登出、刷新 me
    ThemeContext.tsx       # 主题/字号/字体，写入 data-theme + data-font-size
    ToastContext.tsx       # 全局轻提示
  components/
    ui/                    # 通用组件（Button/Input/...）
    layout/                # AppShell/Sidebar/TopBar/AuthLayout
    charts/                # BarChart/LineChart/DonutChart（SVG）
    task/                  # TaskCard/TaskForm/TaskDetailPanel/TaskFilterBar/...
    team/                  # TeamCard/MemberTable/LevelManager/InviteDialog/...
  pages/
    auth/  teams/  tasks/  todos/  dashboard/  profile/  settings/  admin/  sticky/
  hooks/                   # useDebounce/usePagination/useAsync 等
  utils/                   # 时间格式化/优先级映射/校验
```

## 2. 设计语言（黑白极简）
- 只用黑、白、灰阶（无彩色强调色）。优先级/状态用**灰度深浅 + 边框样式 + 文字**区分，禁止彩色。
- 直角或微圆角（≤4px），细边框（1px），无渐变、无阴影（弹层允许极淡阴影）。
- 排版驱动层级：字重 400/500/650、字号档位 12/13/14/16/20/28、行高 1.5。
- `tokens.css` 变量（Lead 已定义，禁止改语义，允许追加）：
  --color-bg / --color-surface / --color-surface-raised / --color-text / --color-text-secondary /
  --color-text-tertiary / --color-border / --color-border-strong / --color-hover / --color-active /
  --color-inverse-bg / --color-inverse-text / --color-danger（低饱和暗红 #8a3a3a 仅用于危险操作文字/边框）
- 主题：`html[data-theme='dark']`；夜间底色 #141414、表面 #1c1c1c、文字 #e8e8e8、边框 #2e2e2e，全部低饱和灰阶。
- 字号：`html[data-font-size='small'|'medium'|'large']` 调整根字号（13/14/15px）。
- 字体：`html[data-font-family='system'|'serif'|'sans'|'monospace']`。
- 布局：AppShell = 左侧 220px 侧边栏（可折叠至 56px）+ 顶部 56px 工具栏 + 内容区（最大宽 1200px，内边距 24px）。
- 响应式：≤900px 时侧边栏抽屉化，内容单列。局域网手机可访问，必须可用。

## 3. 路由表（Lead 冻结）
| 路径 | 页面文件 | 权限 | 说明 |
| --- | --- | --- | --- |
| /login | pages/auth/LoginPage.tsx | 公开 | 登录 |
| /register | pages/auth/RegisterPage.tsx | 公开 | 注册 |
| / | 重定向 | 登录 | → /dashboard |
| /dashboard | pages/dashboard/DashboardPage.tsx | 登录 | 仪表盘 |
| /teams | pages/teams/TeamListPage.tsx | 登录 | 我的团队 + 创建/加入 |
| /teams/:teamId | pages/teams/TeamDetailPage.tsx | 成员 | 详情（内部 tab：概览/任务/成员/级别/设置） |
| /teams/:teamId/tasks/:taskId | pages/tasks/TaskDetailPage.tsx | 成员 | 任务详情 |
| /todos | pages/todos/TodoListPage.tsx | 登录 | 我的待办（排序/筛选） |
| /tasks | pages/tasks/TaskCenterPage.tsx | 登录 | 我发布的/我参与的 任务 |
| /profile | pages/profile/ProfilePage.tsx | 登录 | 个人资料 + 技能标签 |
| /settings | pages/settings/SettingsPage.tsx | 登录 | 主题/字体/密码/注销 |
| /admin | pages/admin/AdminPage.tsx | globalAdmin/superAdmin | 管理后台（tab：概览/用户/团队/数据库/审计） |
| /sticky | pages/sticky/StickyTodoPage.tsx | 登录 | 便签待办小窗（无侧边栏） |
| * | NotFoundPage | - | 404 |

## 4. 通用组件 API（实现者必须遵守；调用方按此使用）
```typescript
// ui/Button.tsx
<Button variant?: 'primary'|'secondary'|'ghost'|'danger'; size?: 'small'|'medium'|'large';
        loading?: boolean; disabled?: boolean; block?: boolean; htmlType?: 'button'|'submit';
        onClick?: () => void; children: ReactNode; className?: string; title?: string; type? ...
// ui/Input.tsx
<Input label?: string; error?: string; hint?: string; value; onChange; placeholder?; type?; disabled?; autoFocus?; onKeyDown?; />
// ui/Textarea.tsx  <Textarea label? error? value onChange rows? placeholder? maxLength? />
// ui/Select.tsx   <Select label? error? value: string|number; onChange:(v)=>void; options: {value:string|number;label:string}[]; placeholder?; disabled? />
// ui/Checkbox.tsx <Checkbox checked onChange label? disabled? />
// ui/RadioGroup.tsx <RadioGroup value onChange options: {value,label,description?}[] />
// ui/Modal.tsx    <Modal open title? onClose footer?: ReactNode size?: 'small'|'medium'|'large' children />
// ui/ConfirmDialog.tsx <ConfirmDialog open title description confirmText? danger? loading? onConfirm onCancel />
// ui/Card.tsx     <Card title? actions? padding? children className? />
// ui/Badge.tsx    <Badge variant?: 'default'|'outline'|'solid' size?: 'small'|'medium'>{children}</Badge>
// ui/Tag.tsx      <Tag label closable? onClose? />
// ui/Avatar.tsx   <Avatar name src? size?: 'small'|'medium'|'large' />
// ui/Table.tsx    <Table columns: {key,title,width?,align?,render:(row)=>ReactNode}[] rows: T[] rowKey:(row)=>string|number emptyText? loading? onRowClick? />
// ui/Pagination.tsx <Pagination page pageSize total onChange:(page)=>void />
// ui/Tabs.tsx     <Tabs items: {key,label,disabled?}[] activeKey onChange />
// ui/EmptyState.tsx <EmptyState title description? action?: ReactNode />
// ui/Spinner.tsx  <Spinner size?: 'small'|'medium' />
// ui/PageHeader.tsx <PageHeader title description? actions?: ReactNode />
// ui/Toast (context) useToast(): { showToast: (message: string, type?: 'success'|'error'|'info') => void }
// ui/Dropdown.tsx <Dropdown trigger: ReactNode items: {key,label,danger?,onClick}[] />
// ui/ProgressBar.tsx <ProgressBar value: number max?: number />
```
```typescript
// layout/AppShell.tsx  默认导出 AppShell：渲染 Sidebar/TopBar/<Outlet/>，内部使用 AuthContext。
// layout/AuthLayout.tsx 登录注册页左右分栏布局。
// charts/LineChart.tsx  <LineChart data: {label:string;values:number[]}[] labels: string[] height? />
// charts/BarChart.tsx   <BarChart data: {label:string;value:number}[] height? />
// charts/DonutChart.tsx <DonutChart data: {label:string;value:number}[] size? centerLabel? />
// task/PriorityBadge.tsx <PriorityBadge priority />
// task/StatusBadge.tsx   <StatusBadge status />  // 支持 task/assignment 两套枚举自动映射
```

## 5. 数据与状态约定
- 认证：AuthContext 暴露 `{ user: CurrentUser | null, loading, login(username,password), logout(), refreshMe(), hasTeamRole(teamId, role) }`。
- 主题：ThemeContext 暴露 `{ theme, fontSize, fontFamily, setTheme, loadFromSettings, applySettings }`，登录后 GET /settings 并应用。
- 所有请求通过 `request<T>()`；错误抛 `ApiError { code, message, status }`，页面用 try/catch + toast 展示中文 message。
- 排序/分页参数与接口契约一致；列表页默认 pageSize=20。
- 时间显示统一用 utils 中 `formatDateTime/formatRelativeTime/formatDate`；空值显示 “—”。
- 所有交互必须有 loading 态与错误态；表单校验前端先行，错误文案中文。
- 图表必须使用 CSS 变量取色（黑/白/灰阶），随主题自动切换。

## 6. Tauri 桌面环境适配
- 检测 `window.__TAURI_INTERNALS__` 存在时：API 基地址通过 `invoke<string>('getApiBaseUrl')` 获取；否则浏览器同源。
- 提供 `openStickyWindow()`（invoke）在桌面模式下打开 /sticky 独立小窗；浏览器模式用 `window.open('/sticky', 'sticky', 'width=360,height=560')` 兜底。
- 顶栏显示“局域网地址”复制按钮（GET /system/network）。

## 7. v1.1 新增页面与组件（团队协作 + AI 通知）

### 7.1 新增路由
| 路径 | 页面文件 | 权限 | 说明 |
| --- | --- | --- | --- |
| /collaborations | pages/collaborations/CollaborationCenterPage.tsx | 登录 | 协作中心：我的协作 / 待我确认 / 团队目录 |
| /collaborations/:collaborationId | pages/collaborations/CollaborationDetailPage.tsx | 参与单位成员 | 协作详情、对接人、协作任务列表与新建任务 |
| /collaboration-tasks/:taskId | pages/collaborations/CollaborationTaskDetailPage.tsx | 参与单位成员 | 协作任务详情、接单指派、双审核 |
| /notifications | pages/notifications/NotificationCenterPage.tsx | 登录 | 通知中心分页与全部已读 |

团队详情页新增 Tab：「子团队」（TeamSubTeamsTab）与「协作」（TeamCollaborationsTab）；
侧边栏导航新增「协作」（路径 /collaborations）；顶栏新增通知铃铛组件（NotificationBell，下拉最近通知 + 未读数轮询）。

### 7.2 新增前端文件所有权
- `types/collaboration.ts`、`types/notification.ts`、`types/task.ts`（v1.1 字段扩展）、`types/ai.ts`（升级）、`types/todo.ts`（扩展）
- `api/collaborationApi.ts`、`api/notificationApi.ts`、`api/aiApi.ts`（升级）、`api/taskApi.ts`（新增 manualAssign）
- `components/collaboration/**`、`components/subteam/**`、`components/task/TaskCard.tsx`、`TaskDetailPage.tsx`、`ReviewPanel.tsx` 等协作相关改造
- `components/notification/**`、`components/task/TaskForm.tsx`、`TaskBasicFields.tsx`、`TaskTargetSelector.tsx`、`AiRecommendPanel.tsx` 等 AI/通知相关改造
- 页面：`pages/collaborations/**`、`pages/notifications/**`、`pages/teams/TeamDetailPage.tsx`（新增 Tab）、`pages/tasks/TaskDetailPage.tsx`（协作任务跳转）

## 8. v1.1.1 系统设置 · AI 配置

- `pages/settings/SettingsPage.tsx` 新增「AI 配置」卡片（位于外观设置、账号安全之后，系统信息之前）。
- 新增 `components/settings/AiConfigSection.tsx` + 同名 CSS Module；所有登录用户可查看，非管理员只读。
- 新增 `types/aiConfig.ts`、`api/settingApi.ts` 追加 `getAIConfig / updateAIConfig / testAIConfigConnection`。
- 表单字段：调度模式（下拉）、LLM Base URL、对话路径、模型、API Key（密码框，留空保持，可清除）、超时秒数、
  候选上限、匹配阈值、负载惩罚；按钮「保存配置」「测试连通性」。
- 测试结果区展示：本地引擎可用性、LLM 是否配置/是否成功/延迟/中文错误信息；测试使用当前表单草稿，不要求先保存。
- 仅 `globalAdmin / superAdmin` 可编辑；其他用户展示只读状态与提示。
