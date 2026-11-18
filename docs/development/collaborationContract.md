# v1.1 团队协作与子团队模块契约（唯一权威）

> 本轮新增功能：团队/子团队之间的协作关系、对接人、跨单位任务派发-确认-指派-双审核、子团队管理。
> JSON 字段 camelCase，数据库列 snake_case；接口前缀 `/api/v1`，统一使用既有 AppException 错误结构。

## 1. 数据模型新增

### 1.1 sub_teams 子团队（父团队内一层分组，复用父团队级别）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 子团队主键 |
| parent_team_id | INT FK teams.id CASCADE | 父团队 |
| name | VARCHAR(100) NOT NULL | 子团队名称（父团队内唯一） |
| description | TEXT NULL | 简介 |
| leader_user_id | INT FK users.id SET NULL NULL | 子负责人（必须是父团队成员） |
| created_by | INT FK users.id SET NULL NULL | 创建人 |
| created_at / updated_at | DATETIME | 时间 |

### 1.2 sub_team_members 子团队成员
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 主键 |
| sub_team_id | INT FK sub_teams.id CASCADE | 子团队 |
| user_id | INT FK users.id CASCADE | 成员（必须是父团队成员） |
| joined_at | DATETIME | 加入时间 |
| UNIQUE(sub_team_id, user_id) | | |

### 1.3 team_collaborations 协作关系（协作单位 = 团队 或 子团队）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 主键 |
| initiator_team_id | INT FK teams.id CASCADE | 发起方团队 |
| initiator_sub_team_id | INT FK sub_teams.id SET NULL NULL | 发起方子团队（为空表示团队本级） |
| target_team_id | INT FK teams.id CASCADE | 接收方团队 |
| target_sub_team_id | INT FK sub_teams.id SET NULL NULL | 接收方子团队（为空表示团队本级） |
| initiator_liaison_user_id | INT FK users.id SET NULL NULL | 发起方对接人（提交申请时指定） |
| target_liaison_user_id | INT FK users.id SET NULL NULL | 接收方对接人（接收方确认时指定） |
| status | ENUM('pending','active','rejected','ended') | 协作状态 |
| message | VARCHAR(500) NULL | 申请说明 |
| reject_comment | VARCHAR(500) NULL | 拒绝/结束原因 |
| created_by | INT FK users.id SET NULL NULL | 申请人 |
| created_at / updated_at | DATETIME | 时间 |

状态机：`pending`（申请中）→ 接收方管理员确认 `active` / 拒绝 `rejected`；`active` 可被任一方结束为 `ended`。
同一对协作单位之间只允许存在一条 `pending/active` 记录（服务层校验）。

### 1.4 notifications 站内通知（v1.1 新增，AI 与协作模块共用）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 主键 |
| user_id | INT FK users.id CASCADE NOT NULL | 接收人（索引 user_id, read_flag, created_at） |
| type | VARCHAR(50) NOT NULL | 通知类型标识 |
| title | VARCHAR(200) NOT NULL | 标题 |
| content | TEXT NULL | 内容 |
| task_id | INT FK tasks.id SET NULL NULL | 关联任务 |
| collaboration_id | INT FK team_collaborations.id SET NULL NULL | 关联协作 |
| read_flag | BOOLEAN NOT NULL DEFAULT FALSE | 是否已读 |
| created_at | DATETIME NOT NULL | 时间 |

通知类型（type）约定：
`collaborationApplied`、`collaborationConfirmed`、`collaborationRejected`、`collaborationEnded`、
`collaborationTaskReceived`、`collaborationTaskConfirmed`、`collaborationTaskRejected`、
`collaborationTaskTargetReview`、`collaborationTaskSourceReview`、`collaborationTaskArchived`、
`taskAutoAssigned`、`taskMatchReminder`、`taskAssignFailed`、`taskReviewResult`、`taskAssigned`。

### 1.5 tasks 表新增列（v1.0 已有表，需迁移）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| sub_team_id | INT NULL | 任务所属子团队（团队内任务分组/子团队任务视图） |
| source_team_id | INT NULL | 协作任务发起方团队（普通任务为空） |
| source_sub_team_id | INT NULL | 协作任务发起方子团队 |
| target_team_id | INT NULL | 协作任务接收方团队 |
| target_sub_team_id | INT NULL | 协作任务接收方子团队 |
| collaboration_id | INT NULL | 所属协作关系 |
| collaboration_phase | VARCHAR(32) NULL | pendingConfirmation/executing/targetReview/sourceReview/rejected |
| collaboration_comment | TEXT NULL | 接收方对接人确认/拒绝意见 |
| auto_assigned | BOOLEAN NOT NULL DEFAULT FALSE | 是否由 AI 自动分配产生 |
| required_skill_names | TEXT NULL | AI 分配所需技能标签（逗号分隔、小写） |

### 1.6 task_assignments 表新增列（v1.0 已有表，需迁移）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| review_stage | VARCHAR(16) NULL | 双审核阶段：target / source（普通任务为空） |
| target_reviewed_at | DATETIME NULL | 接收方对接人审核时间 |
| target_reviewer_id | INT NULL | 接收方对接人 |
| target_review_comment | TEXT NULL | 接收方审核意见 |
| assignment_source | VARCHAR(16) NOT NULL DEFAULT 'manual' | manual / ai / collaboration |

> v1.0 → v1.1 迁移：服务启动时由 `core/migrationService.py` 自动创建新表并为已有表补齐新列（幂等），
> 不修改现有枚举字段，避免 MySQL ENUM 迁移风险；所有列均为可空或带默认值，旧数据可直接使用。

## 2. 协作流程

### 2.1 建立协作关系
1. 发起方单位管理员（团队 = 团队管理员；子团队 = 子负责人，父团队管理员亦可）提交申请：
   选择接收方单位（团队或其一层的子团队）、指定己方对接人（必须是发起方单位成员）、填写申请说明；
2. 接收方单位管理员确认并指定接收方对接人（必须是接收方单位成员）→ 协作生效；也可拒绝并填写原因；
3. 双方在「协作」页面可查看协作列表；任意一方管理员可结束协作（已派发未完成任务不受影响，仍按原流程完成）。

### 2.2 跨单位任务（协作任务）
1. 发起方单位管理员/对接人发布协作任务：标题、描述、优先级、截止时间、接受方式（必须接受/选择性接受）；
2. 接收方对接人确认：可填写意见；确认时必须从接收方单位成员中指定 1-N 名执行人；
   拒绝则任务取消（`collaboration_phase=rejected`，通知发起方）；
3. 执行人完成提交 → 进入「接收方对接人审核」（`review_stage=target`，任务 `collaboration_phase=targetReview`）；
4. 接收方对接人审核通过 → 进入「发起方审核」（`review_stage=source`，`collaboration_phase=sourceReview`）；
   驳回 → 回到执行中（`review_stage=NULL`，`collaboration_phase=executing`），记录审核意见；
5. 发起方（任务发布者；发布者注销时为发起方单位管理员）审核通过 → 待办归档，全部归档后任务归档；
   驳回 → 回到执行中；
6. 协作任务在双方团队任务列表中展示（带来源/接收单位标签）；协作任务详情路由仍使用接收方团队 ID（`task.teamId = targetTeamId`）。

### 2.3 子团队
- 父团队管理员创建/编辑/删除子团队，任命子负责人，维护成员（成员必须是父团队成员）；
- 子负责人可编辑子团队信息、维护成员、以子团队名义发起协作、在子团队内发布任务、确认发往子团队的协作任务、审核子团队任务；
- 子团队任务视图：父团队任务列表中可按子团队筛选；子团队任务仅子团队成员与父团队管理员可见；
- 子团队任务创建：`POST /teams/{teamId}/tasks` 增加可选 `subTeamId`，发布者需为该子团队成员或父团队管理员/子管理员。

## 3. 权限规则（服务层强制）

| 操作 | 允许角色 |
| --- | --- |
| 管理子团队（增删改、任免负责人、维护成员） | 父团队管理员；子负责人可改名称/简介/成员 |
| 发起协作申请 | 发起单位管理员（团队 admin；子团队 leader；父团队 admin） |
| 确认/拒绝协作申请 | 接收单位管理员（同上） |
| 结束协作 | 任一单位管理员 |
| 发布协作任务 | 发起单位管理员或发起方对接人 |
| 确认协作任务并指派执行人 | 接收方对接人（必须是接收方单位成员） |
| 接收方审核 | 接收方对接人 |
| 发起方审核 | 任务发布者（或发起单位管理员，发布者注销时） |
| 查看协作任务 | 发起方/接收方单位成员（团队本级：全体团队成员；子团队：子团队成员 + 父团队管理员） |
| 查看协作关系 | 双方单位成员及以上角色 |

单位成员解析：
- 团队本级单位成员 = 该团队全部成员；
- 子团队单位成员 = 该子团队成员（且必为父团队成员）；
- 对接人/子负责人必须属于对应单位。

## 4. REST 接口

### 4.1 子团队 `/teams/{teamId}/sub-teams`
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /teams/{teamId}/sub-teams | 团队成员 | 子团队列表（含负责人、成员数） |
| POST | /teams/{teamId}/sub-teams | 团队管理员 | `{ name, description?, leaderUserId, memberUserIds?: number[] }` → SubTeamDetail |
| GET | /teams/{teamId}/sub-teams/{subTeamId} | 团队成员 | 子团队详情（含成员） |
| PUT | /teams/{teamId}/sub-teams/{subTeamId} | 管理员/子负责人 | `{ name?, description?, leaderUserId? }` |
| DELETE | /teams/{teamId}/sub-teams/{subTeamId} | 团队管理员 | 删除子团队（其任务 subTeamId 置空） |
| PUT | /teams/{teamId}/sub-teams/{subTeamId}/members | 管理员/子负责人 | `{ userIds: number[] }` 覆盖式设置成员 |
| GET | /teams/{teamId}/sub-teams/{subTeamId}/tasks | 子团队成员/团队管理员 | 子团队任务分页（复用 TaskItem 结构） |

### 4.2 协作 `/collaborations`
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /collaboration/directory | 登录用户 | 可申请协作的团队/子团队目录（仅 active 团队；含成员数、子团队与负责人） |
| POST | /collaborations | 单位管理员 | `{ initiatorTeamId, initiatorSubTeamId?, targetTeamId, targetSubTeamId?, initiatorLiaisonUserId, message? }` → CollaborationItem（pending） |
| GET | /collaborations | 登录用户 | 与我相关（我管理的单位或我作为对接人）的分页列表，query: status/page/pageSize |
| GET | /collaborations/{collaborationId} | 参与单位成员 | 协作详情 |
| POST | /collaborations/{id}/confirm | 接收单位管理员 | `{ approved, targetLiaisonUserId?, comment? }` → CollaborationItem |
| POST | /collaborations/{id}/end | 任一单位管理员 | `{ comment? }` → CollaborationItem（active→ended） |
| POST | /collaborations/{id}/tasks | 发起单位管理员/发起方对接人 | 创建协作任务（body 同任务创建基础字段，无分配对象字段） |
| GET | /collaborations/{id}/tasks | 参与单位成员 | 协作任务分页 |
| GET | /collaboration-tasks/{taskId} | 参与单位成员 | 协作任务详情（含双审核信息与权限标记） |
| POST | /collaboration-tasks/{taskId}/confirm | 接收方对接人 | `{ approved, assigneeUserIds?, comment? }` → CollaborationTaskItem |
| POST | /collaboration-tasks/{taskId}/target-review | 接收方对接人 | `{ assignmentUserId, approved, comment? }` → CollaborationTaskItem |
| POST | /collaboration-tasks/{taskId}/source-review | 任务发布者/发起单位管理员 | `{ assignmentUserId, approved, comment? }` → CollaborationTaskItem |

### 4.3 通知 `/notifications`
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /notifications?unreadOnly=&page=&pageSize= | 当前用户通知分页（时间倒序） |
| GET | /notifications/unread-count | `{ count: number }` 未读数 |
| PUT | /notifications/{notificationId}/read | 标记单条已读（仅本人，404 不存在/非本人） |
| PUT | /notifications/read-all | 全部标记已读 |

## 5. 前端新增路由与页面
| 路径 | 页面 | 权限 | 说明 |
| --- | --- | --- | --- |
| /collaborations | 协作中心 | 登录 | Tab：我的协作 / 协作申请（待确认）/ 团队目录；申请协作、确认/拒绝、结束、进入协作详情 |
| /collaborations/:collaborationId | 协作详情 | 参与单位成员 | 协作信息、对接人、任务列表、新建协作任务 |
| /collaboration-tasks/:taskId | 协作任务详情 | 参与单位成员 | 任务信息、接收方确认/指派、执行进度、双审核操作与记录 |
| /notifications | 通知中心 | 登录 | 通知分页列表、全部已读；顶栏铃铛下拉展示最近通知与未读数（每 20 秒轮询） |

团队详情页新增两个 Tab：「子团队」（列表/创建/编辑/成员管理入口）与「协作」（该团队的协作关系与申请入口）；
侧边栏新增导航「协作」。

## 6. 响应结构（前端 types/collaboration.ts 对齐）
```typescript
interface SubTeamItem { id: number; parentTeamId: number; name: string; description: string | null;
  leaderUserId: number | null; leaderNickname: string | null; memberCount: number; createdAt: string; myRole: 'admin'|'leader'|'member'|null }
interface SubTeamMemberItem { userId: number; username: string; nickname: string; avatar: string|null; levelName: string; levelOrder: number; isLeader: boolean }
interface SubTeamDetail extends SubTeamItem { members: SubTeamMemberItem[] }
interface CollaborationUnit { teamId: number; teamName: string; subTeamId: number|null; subTeamName: string|null; unitName: string }
interface CollaborationItem { id: number; initiatorUnit: CollaborationUnit; targetUnit: CollaborationUnit;
  initiatorLiaisonUserId: number|null; initiatorLiaisonNickname: string|null;
  targetLiaisonUserId: number|null; targetLiaisonNickname: string|null;
  status: 'pending'|'active'|'rejected'|'ended'; message: string|null; rejectComment: string|null;
  createdByName: string; createdAt: string; updatedAt: string;
  canConfirm: boolean; canEnd: boolean; canCreateTask: boolean; myUnitRole: 'initiator'|'target'|'both'|null }
interface CollaborationDirectoryItem { teamId: number; teamName: string; description: string|null; memberCount: number;
  subTeams: { subTeamId: number; name: string; memberCount: number; leaderNickname: string|null }[] }
interface CollaborationTaskItem extends TaskItem { collaborationId: number;
  sourceUnit: CollaborationUnit; targetUnit: CollaborationUnit;
  collaborationPhase: 'pendingConfirmation'|'executing'|'targetReview'|'sourceReview'|'rejected';
  collaborationComment: string|null;
  canConfirmTask: boolean; canTargetReview: boolean; canSourceReview: boolean }
interface CollaborationTaskDetail extends CollaborationTaskItem { reviews: ReviewRecord[] }
```
> 协作任务的 `task.reviewStage` 通过 assignment.reviewStage 暴露；assignment 结构在 v1.0 字段基础上追加
> `reviewStage: 'target'|'source'|null; targetReviewedAt: string|null; targetReviewerId: number|null; targetReviewComment: string|null; assignmentSource: 'manual'|'ai'|'collaboration'`。
