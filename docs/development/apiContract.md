# 后端接口契约（唯一权威）

> 基础路径：`/api/v1`；所有请求/响应 JSON 使用 camelCase；时间使用 ISO 8601 字符串（`2026-11-24T16:51:46`，本地时区 Asia/Shanghai）。
> 认证：除注册/登录/健康检查外，均需 `Authorization: Bearer <token>`。
> 统一响应：成功直接返回数据对象；分页返回 `{ "items": [], "total": 0, "page": 1, "pageSize": 20 }`。
> 统一错误：HTTP 状态码 + `{ "code": "ERROR_CODE", "message": "中文提示", "details": null }`。
> 错误码约定：`INVALID_CREDENTIALS`(401)、`TOKEN_EXPIRED`(401)、`FORBIDDEN`(403)、`NOT_FOUND`(404)、
> `CONFLICT`(409)、`VALIDATION_ERROR`(400)、`ACCOUNT_DISABLED`(403)、`TEAM_PENDING`(403)、`RATE_LIMITED`(429)、
> `DATABASE_ERROR`(500)、`INTERNAL_ERROR`(500)。

## 0. 通用数据结构

```typescript
interface UserBrief {            // 用户简要信息
  id: number; username: string; nickname: string; avatar: string | null;
  globalRole: 'superAdmin' | 'globalAdmin' | 'user';
}
interface SkillItem { id: number; name: string; category: string | null; proficiency: number; }
interface UserDetail extends UserBrief {  // 个人资料
  email: string | null; phone: string | null; bio: string | null;
  createdAt: string; skills: SkillItem[];
}
interface TeamMembership {       // 当前用户在团队中的身份
  teamId: number; teamName: string; teamStatus: 'pending'|'active'|'rejected';
  role: 'admin' | 'subAdmin' | 'member';
  levelId: number; levelName: string; levelOrder: number; canCreateTask: boolean;
  joinedAt: string;
}
interface CurrentUser { user: UserDetail; teams: TeamMembership[]; }
interface TeamBrief {
  id: number; name: string; description: string | null; status: 'pending'|'active'|'rejected';
  joinMethod: 'free'|'approval'|'inviteOnly'; createdBy: number | null;
  memberCount: number; createdAt: string;
}
interface TeamLevel { id: number; teamId: number; name: string; levelOrder: number; canCreateTask: boolean; memberCount: number; }
interface TeamMemberItem {
  id: number; userId: number; username: string; nickname: string; avatar: string | null;
  role: 'admin'|'subAdmin'|'member'; levelId: number; levelName: string; levelOrder: number;
  joinedAt: string; skills: SkillItem[];
}
interface TeamDetail extends TeamBrief {
  inviteCode: string | null; inviteExpiresAt: string | null;
  levels: TeamLevel[]; members: TeamMemberItem[];
  currentUserRole: 'admin'|'subAdmin'|'member'; currentUserLevelOrder: number;
}
interface TaskAssignmentItem {
  id: number; userId: number; username: string; nickname: string; avatar: string | null;
  status: 'pendingAcceptance'|'inProgress'|'pendingReview'|'archived';
  acceptedAt: string | null; submittedAt: string | null; reviewedAt: string | null;
  reviewedBy: number | null; reviewComment: string | null;
}
interface TaskItem {
  id: number; teamId: number; teamName: string;
  title: string; description: string | null;
  priority: 'low'|'medium'|'high'|'urgent';
  status: 'published'|'inProgress'|'pendingReview'|'archived'|'cancelled';
  assignmentMode: 'specific'|'levelRange';
  acceptanceMode: 'mandatory'|'optional';
  targetLevelMin: number | null; targetLevelMax: number | null;
  dueAt: string | null; createdBy: number | null; createdByName: string;
  createdAt: string; updatedAt: string; archivedAt: string | null;
  assignments: TaskAssignmentItem[];
  myAssignment: TaskAssignmentItem | null;
  canReview: boolean; canEdit: boolean;
  reviewCount: number;
}
interface ReviewRecord {
  id: number; taskId: number; assignmentId: number; reviewerId: number; reviewerName: string;
  result: 'approved'|'rejected'; comment: string | null; createdAt: string;
}
interface TaskDetail extends TaskItem { reviews: ReviewRecord[]; }
interface TodoItem {
  assignmentId: number; taskId: number; teamId: number; teamName: string; title: string;
  description: string | null; priority: string; taskStatus: string; assignmentStatus: string;
  dueAt: string | null; createdByName: string; acceptedAt: string | null;
  createdAt: string; overdue: boolean;
}
interface DashboardSummary {
  todoCount: number; pendingAcceptanceCount: number; inProgressCount: number;
  pendingReviewCount: number; archivedThisWeek: number; overdueCount: number; archivedTotal: number;
  byPriority: { priority: string; count: number }[];
  byStatus: { status: string; count: number }[];
  weeklyTrend: { date: string; created: number; completed: number }[];
  teamStats: { teamId: number; teamName: string; memberCount: number; openTaskCount: number; archivedTaskCount: number }[];
}
```

## 1. 认证模块 `/auth`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /auth/register | 公开 | 注册普通用户 |
| POST | /auth/login | 公开 | 登录，返回 token |
| GET | /auth/me | 登录 | 当前用户 + 团队身份列表 |
| POST | /auth/logout | 登录 | 注销 token（Redis 黑名单） |
| PUT | /auth/password | 登录 | 修改密码（需旧密码），成功后旧 token 失效 |

请求/响应：
- `POST /auth/register` body: `{ username, password, nickname, email? }` → 201 `{ token, user: CurrentUser }`
- `POST /auth/login` body: `{ username, password }` → 200 `{ token, user: CurrentUser }`

## 2. 用户与个人资料 `/users`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /users/me | 登录 | 个人资料 |
| PUT | /users/me | 登录 | 修改昵称/邮箱/手机号/简介 |
| PUT | /users/me/skills | 登录 | 覆盖式保存技能：`{ skills: [{ skillTagId, proficiency }] }` |
| POST | /users/me/skills/tags | 登录 | 新建技能标签（不存在则创建）`{ name, category? }` → SkillItem |
| GET | /skill-tags | 登录 | 全部技能标签（可按 keyword 过滤） |
| GET | /users/{userId}/profile | 登录 | 查看他人资料；权限：本人、全局管理员、同团队且级别更高/管理员。email/phone 仅本人与全局管理员可见 |
| GET | /users/{userId}/public-profile | 登录 | 同团队可查看的公开资料（昵称/简介/技能/团队） |

## 3. 团队模块 `/teams`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /teams | 登录 | 创建团队，创建者自动成为 admin；团队默认 pending |
| GET | /teams | 登录 | 我加入的团队列表（含 pending 自己创建的） |
| GET | /teams/{teamId} | 成员 | 团队详情（级别、成员） |
| PUT | /teams/{teamId} | admin | 修改名称/简介/加入方式 |
| DELETE | /teams/{teamId} | admin | 解散团队（需二次确认参数 `confirmName`=团队名） |
| POST | /teams/{teamId}/transfer | admin | 转让团队管理员 `{ newAdminUserId }`，自己降为 member |
| POST | /teams/join | 登录 | 加入团队 `{ teamId?, inviteCode?, message? }`；free 直接加入、approval 建立申请、inviteOnly 校验邀请码；响应 `{ status: 'joined'|'pending', teamId, teamName, message }` |
| POST | /teams/{teamId}/leave | 成员（非 admin） | 退出团队 |
| GET | /teams/{teamId}/members | 成员 | 成员列表 |
| DELETE | /teams/{teamId}/members/{userId} | admin/subAdmin | 踢出成员；admin 可踢任何人，subAdmin 仅可踢级别更低者；不能踢自己/管理员 |
| PUT | /teams/{teamId}/members/{userId}/role | admin | 设置/撤销子管理员 `{ role: 'subAdmin'|'member' }` |
| PUT | /teams/{teamId}/members/{userId}/level | admin/subAdmin | 调整成员级别 `{ levelId }`；subAdmin 不能调整同级或更高级别者 |
| GET | /teams/{teamId}/levels | 成员 | 级别列表 |
| POST | /teams/{teamId}/levels | admin | 新建级别 `{ name, levelOrder, canCreateTask }` |
| PUT | /teams/{teamId}/levels/{levelId} | admin | 修改级别 |
| DELETE | /teams/{teamId}/levels/{levelId} | admin | 删除级别（须无成员使用） |
| POST | /teams/{teamId}/invite-code | admin/subAdmin | 生成邀请码 `{ expiresInHours?, maxUses? }` → TeamDetail |
| GET | /teams/{teamId}/join-requests | admin/subAdmin | 待处理入团申请 |
| PUT | /teams/{teamId}/join-requests/{requestId} | admin/subAdmin | `{ action: 'approve'|'reject' }` |
| GET | /teams/{teamId}/members/candidates | admin/subAdmin | 任务可选成员（含级别、技能，辅助发布任务） |

## 4. 任务模块 `/teams/{teamId}/tasks` 与 `/tasks`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /teams/{teamId}/tasks | 有发布权限 | 发布任务 |
| GET | /teams/{teamId}/tasks | 成员 | 团队任务分页列表，query: status/priority/keyword/createdBy/assigneeId/sortBy(createdAt|dueAt|priority)/sortOrder/page/pageSize |
| GET | /teams/{teamId}/tasks/{taskId} | 成员 | 任务详情（含审核记录） |
| PUT | /teams/{teamId}/tasks/{taskId} | 发布者/团队管理员 | 修改任务（含标题/描述/优先级/截止/接受方式），未归档时允许 |
| POST | /tasks/{taskId}/cancel | 发布者/团队管理员 | 取消任务 |
| POST | /tasks/{taskId}/acceptance | 被分配者 | 接受可选任务（mandatory 任务自动接受） |
| POST | /tasks/{taskId}/decline | 被分配者 | 拒绝可选任务（mandatory 拒绝返回 400） |
| POST | /tasks/{taskId}/submit | 被分配者 | 标记完成，进入待审核 |
| POST | /tasks/{taskId}/review | 发布者/团队管理员 | `{ assignmentUserId, approved, comment? }` 审核；驳回回到 inProgress |
| GET | /tasks | 登录 | 我的任务中心分页列表，query: role=created\|assigned、teamId、status、priority、keyword、页参数；返回 PageResult<TaskItem> |
| GET | /tasks/{taskId} | 参与者/发布者/成员 | 任务详情（同团队） |

创建任务 body：
```typescript
{
  title: string;                    // 必填 2-200 字
  description?: string;
  priority: 'low'|'medium'|'high'|'urgent';
  dueAt?: string | null;            // ISO 时间
  assignmentMode: 'specific' | 'levelRange';
  acceptanceMode: 'mandatory' | 'optional';
  targetUserIds?: number[];         // specific 必填，1-100 人
  targetLevelMin?: number;          // levelRange 必填
  targetLevelMax?: number;
}
```
> 发布者校验：团队管理员/子管理员，或级别 canCreateTask=true 且目标成员全部级别低于自己。
> 可选任务被分配者拒绝后从任务移除；全部拒绝且无执行人时任务自动取消（cancelled）。

## 5. 待办清单 `/todos`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /todos | 登录 | 我的待办分页，query: status(不传=全部未归档)/priority/teamId/keyword/sortBy(priority|dueAt|createdAt)/sortOrder/includeArchived(bool)/page/pageSize |
| GET | /todos/stats | 登录 | `{ total, pendingAcceptance, inProgress, pendingReview, archived, overdue }` |

## 6. 仪表盘 `/dashboard`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /dashboard/summary?teamId= | 登录 | DashboardSummary（teamId 可选，缺省聚合全部团队） |

## 7. 系统设置 `/settings`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /settings | 登录 | `{ theme, fontSize, fontFamily }`（不存在时返回默认并自动创建） |
| PUT | /settings | 登录 | 修改界面设置 |
| PUT | /settings/password | 登录 | 同 /auth/password（前端可调用任一） |
| DELETE | /settings/account | 登录 | 注销账号 `{ password }` 二次确认 |

## 8. AI 辅助（预留接口，当前使用启发式推荐实现） `/ai`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /teams/{teamId}/ai/recommend-assignees | 有发布权限 | 根据标题/描述/优先级/级别范围/技能标签推荐成员 |
| GET | /ai/status | 登录 | 返回 `{ provider: 'heuristic', available: true, description }`，后续接入大模型时替换 provider |

推荐响应：
```typescript
interface RecommendItem {
  userId: number; nickname: string; levelName: string; levelOrder: number;
  score: number;                    // 0-100
  reasons: string[];                // 中文推荐理由
  matchedSkills: string[];
}
```

## 9. 管理后台 `/admin`（globalAdmin/superAdmin）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /admin/users | 管理员 | 用户分页：keyword/globalRole/isActive |
| PUT | /admin/users/{userId}/global-role | **superAdmin** | `{ globalRole: 'globalAdmin'|'user' }` 设置全局管理员 |
| PUT | /admin/users/{userId}/status | 管理员 | `{ isActive }` 启用/禁用 |
| GET | /admin/teams | 管理员 | 团队分页：status/keyword |
| PUT | /admin/teams/{teamId}/certification | 管理员 | `{ approved }` 团队认证通过/驳回 |
| GET | /admin/database/tables | 管理员 | 数据库表清单：`[{ tableName, rowCount }]` |
| GET | /admin/database/tables/{tableName}/rows?page&pageSize | 管理员 | 表数据浏览（只读，敏感列脱敏）：`{ tableName, columns, rows, total, page, pageSize }` |
| POST | /admin/database/execute | 管理员 | `{ sql, confirm: true }` 执行单条 DML，响应 `{ executed, statementType, affectedRows, rows }`（SELECT 返回行数据） |
| GET | /admin/audit-logs | 管理员 | 审计日志分页 |
| GET | /admin/overview | 管理员 | `{ userCount, teamCount, pendingTeamCount, taskCount, activeUserCount, databaseName }` |

## 10. 系统 `/system`

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /health | 公开 | `{ status: 'ok', version, database: 'connected', redis: 'connected'|'memory' }` |
| GET | /system/network | 登录 | `{ lanUrls: string[], port, version }` 局域网访问地址 |
| GET | /system/info | 登录 | `{ version, appName, databaseType, redisMode }` |

## 10.5 字段命名与排序说明
- 列表接口默认按创建时间倒序；任务排序 `sortBy` 支持 createdAt/dueAt/priority，优先级排序使用权重（urgent > high > medium > low）。
- 待办列表默认仅返回未归档分配记录；`includeArchived=true` 时包含已归档。
- 所有 ID 使用整数；时间字段为不带时区后缀的本地时间字符串。
- 分页 `pageSize` 上限 100，默认 20。

## 11. 前端调用约定
- API 基地址：桌面应用 `http://127.0.0.1:8765/api/v1`；浏览器/局域网为同源 `/api/v1`。
- token 存 localStorage key `tms.token`；401 时清除并跳转 /login。
- 登录失败次数限制：同一 IP+用户名 5 分钟内最多 10 次（Redis 计数），超限 429。

## 12. 初始化种子账号
- 超级用户：用户名 `superAdmin`，初始密码 `SuperAdmin@123`（首次登录后提示修改；可通过环境变量覆盖）。
- 演示数据（可选）：`python scripts/seedDemoData.py` 创建 3 个用户、2 个团队、若干任务。

## 13. v1.1 新增接口与字段（详细契约见 collaborationContract.md / aiModuleContract.md）

### 13.1 子团队
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /teams/{teamId}/sub-teams | 团队成员 | 子团队列表 |
| POST | /teams/{teamId}/sub-teams | 团队管理员 | 创建子团队（名称/简介/子负责人/初始成员） |
| GET | /teams/{teamId}/sub-teams/{subTeamId} | 团队成员 | 子团队详情（含成员） |
| PUT | /teams/{teamId}/sub-teams/{subTeamId} | 管理员/子负责人 | 修改子团队 |
| DELETE | /teams/{teamId}/sub-teams/{subTeamId} | 团队管理员 | 删除子团队 |
| PUT | /teams/{teamId}/sub-teams/{subTeamId}/members | 管理员/子负责人 | 覆盖式设置成员 |
| GET | /teams/{teamId}/sub-teams/{subTeamId}/tasks | 子团队成员/管理员 | 子团队任务分页 |

### 13.2 协作
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /collaboration/directory | 可申请协作的团队/子团队目录 |
| POST | /collaborations | 发起协作申请（pending） |
| GET | /collaborations | 与我相关的协作分页 |
| GET | /collaborations/{collaborationId} | 协作详情 |
| POST | /collaborations/{collaborationId}/confirm | 接收方管理员确认/拒绝并指定对接人 |
| POST | /collaborations/{collaborationId}/end | 结束协作 |
| POST | /collaborations/{collaborationId}/tasks | 创建协作任务 |
| GET | /collaborations/{collaborationId}/tasks | 协作任务分页 |
| GET | /collaboration-tasks/{taskId} | 协作任务详情（含权限标记与审核记录） |
| POST | /collaboration-tasks/{taskId}/confirm | 接收方对接人确认接单并指派执行人 |
| POST | /collaboration-tasks/{taskId}/target-review | 接收方对接人审核 |
| POST | /collaboration-tasks/{taskId}/source-review | 发起方发布者最终审核 |

### 13.3 通知
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /notifications?unreadOnly=&page=&pageSize= | 当前用户通知分页 |
| GET | /notifications/unread-count | 未读数 |
| PUT | /notifications/{notificationId}/read | 单条已读 |
| PUT | /notifications/read-all | 全部已读 |

### 13.4 任务接口扩展
- `POST /teams/{teamId}/tasks` 请求新增：`subTeamId?`、`autoAssign?: boolean = false`、`requiredSkillNames?: string[]`
- 任务响应新增字段：`subTeamId/subTeamName/sourceTeamId/sourceTeamName/sourceSubTeamId/sourceSubTeamName/targetTeamId/targetTeamName/targetSubTeamId/targetSubTeamName/collaborationId/collaborationPhase/collaborationComment/autoAssigned/requiredSkillNames/canAssign`
- 分配项响应新增字段：`reviewStage/targetReviewedAt/targetReviewerId/targetReviewComment/assignmentSource`
- 新增 `POST /tasks/{taskId}/assignments`：`{ userIds: number[] }` 为无执行人任务手动指派
- `POST /tasks/{taskId}/submit` 对协作任务会进入接收方审核阶段；`POST /tasks/{taskId}/review` 仅用于普通任务
- `GET /tasks/{taskId}` 与 `GET /teams/{teamId}/tasks/{taskId}` 允许协作任务参与方与子团队成员按可见性规则访问
- `GET /todos` 响应项新增：`collaborationId/collaborationPhase/sourceTeamName/targetTeamName/reviewStage`

### 13.5 AI 接口
- `GET /ai/status` 扩展为返回 dispatchMode/localAvailable/llmConfigured/llmModel/matchThreshold/workloadPenalty 等字段
- `POST /teams/{teamId}/ai/recommend-assignees` 响应由数组改为 `{ route, reason, candidates }`；请求新增 `requiredSkillNames?`、`maxCandidates?`

### 13.6 协作单位成员接口（前端选择对接人/指派执行人使用）
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /collaborations/units/members?teamId=&subTeamId= | 团队成员 | 返回单位（团队或子团队）候选成员列表：`[{ userId, username, nickname, avatar, levelName, levelOrder, role }]`；teamId 必填，subTeamId 可选（为空表示团队本级） |

## 14. v1.1.1 AI 配置接口（系统设置）

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /settings/ai-config | 登录用户 | 读取有效 AI 配置（apiKey 掩码，非管理员 canEdit=false） |
| PUT | /settings/ai-config | globalAdmin/superAdmin | 部分更新 AI 配置（含 LLM 地址/模型/Key、调度模式、阈值等），写审计日志 |
| POST | /settings/ai-config/test | globalAdmin/superAdmin | 测试本地规则引擎与 LLM 连通性（支持草稿配置，不保存） |

详细字段与行为见 `docs/development/aiModuleContract.md` 第 9 节。
