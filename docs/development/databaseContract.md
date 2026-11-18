# 数据库契约（唯一权威）

> 所有后端模型、仓储、前端类型都必须以本文件为准。字段在数据库中使用 snake_case，
> 在 API JSON 中使用 camelCase（Pydantic 使用 alias 或直接 camelCase 字段名）。
> 数据库引擎：MariaDB 11.x / MySQL 8.x；字符集 utf8mb4；排序规则 utf8mb4_unicode_ci。
> 缓存：Redis（可选内存兜底，见 `core/redisClient.py`）。

## 1. 表结构

### 1.1 users 用户表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 用户主键 |
| username | VARCHAR(50) | UNIQUE NOT NULL | 登录名，3-30 位字母数字下划线 |
| password_hash | VARCHAR(100) | NOT NULL | bcrypt 哈希 |
| nickname | VARCHAR(50) | NOT NULL | 昵称 |
| email | VARCHAR(100) | NULL, UNIQUE | 邮箱 |
| phone | VARCHAR(30) | NULL | 手机号（非隐私外仅本人/全局管理员可见） |
| bio | TEXT | NULL | 个人简介 |
| avatar | VARCHAR(255) | NULL | 头像路径/URL，可为空 |
| global_role | ENUM('superAdmin','globalAdmin','user') | NOT NULL DEFAULT 'user' | 全局角色，superAdmin 全库唯一 |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | 是否启用（注销/封禁） |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |

### 1.2 teams 团队表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 团队主键 |
| name | VARCHAR(100) | NOT NULL | 团队名称 |
| description | TEXT | NULL | 团队简介 |
| join_method | ENUM('free','approval','inviteOnly') | NOT NULL DEFAULT 'inviteOnly' | 加入方式：自由加入/申请审核/仅邀请码 |
| invite_code | VARCHAR(32) | NULL, UNIQUE | 当前邀请码 |
| invite_expires_at | DATETIME | NULL | 邀请码过期时间 |
| invite_max_uses | INT | NOT NULL DEFAULT 0 | 0 表示不限制次数 |
| invite_used_count | INT | NOT NULL DEFAULT 0 | 已使用次数 |
| status | ENUM('pending','active','rejected') | NOT NULL DEFAULT 'pending' | 团队认证状态，全局管理员/超级用户审核 |
| created_by | INT | FK users.id, NOT NULL | 创建者（即首任团队管理员） |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |

> 创建团队后创建者自动成为 team_members.role='admin' 并自动生成 3 个默认级别：
> 高级成员(3)、中级成员(2)、初级成员(1)，创建者成员级别=3（最高级）。

### 1.3 team_levels 团队级别表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 级别主键 |
| team_id | INT | FK teams.id ON DELETE CASCADE | 所属团队 |
| name | VARCHAR(50) | NOT NULL | 级别名称（团队管理员自定义） |
| level_order | INT | NOT NULL | 级别数值，数值越大级别越高，团队内唯一 |
| can_create_task | BOOLEAN | NOT NULL DEFAULT TRUE | 该级别是否允许发布任务 |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |

### 1.4 team_members 团队成员表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| team_id | INT | FK teams.id ON DELETE CASCADE | 团队 |
| user_id | INT | FK users.id ON DELETE CASCADE | 用户 |
| role | ENUM('admin','subAdmin','member') | NOT NULL DEFAULT 'member' | 团队角色；admin 唯一 |
| level_id | INT | FK team_levels.id, NOT NULL | 成员级别 |
| joined_at | DATETIME | NOT NULL | 加入时间 |
| UNIQUE(team_id, user_id) | | | 一人一团队一条记录 |

### 1.5 team_join_requests 入团申请表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| team_id | INT | FK teams.id ON DELETE CASCADE | 团队 |
| user_id | INT | FK users.id ON DELETE CASCADE | 申请人 |
| message | VARCHAR(255) | NULL | 申请留言 |
| status | ENUM('pending','approved','rejected') | NOT NULL DEFAULT 'pending' | 状态 |
| handled_by | INT | FK users.id, NULL | 处理人 |
| created_at / handled_at | DATETIME | | 时间 |

### 1.6 tasks 任务表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 任务主键 |
| team_id | INT | FK teams.id ON DELETE CASCADE | 所属团队 |
| title | VARCHAR(200) | NOT NULL | 任务标题 |
| description | TEXT | NULL | 任务描述 |
| priority | ENUM('low','medium','high','urgent') | NOT NULL DEFAULT 'medium' | 优先级 |
| status | ENUM('published','inProgress','pendingReview','archived','cancelled') | NOT NULL DEFAULT 'published' | 任务聚合状态 |
| assignment_mode | ENUM('specific','levelRange') | NOT NULL | 指定成员/级别范围 |
| acceptance_mode | ENUM('mandatory','optional') | NOT NULL DEFAULT 'mandatory' | 必须接受/选择性接受 |
| target_level_min | INT | NULL | 范围模式的最低级别值 |
| target_level_max | INT | NULL | 范围模式的最高级别值 |
| due_at | DATETIME | NULL | 截止时间 |
| created_by | INT | FK users.id ON DELETE SET NULL, NULL | 发布者 |
| archived_at | DATETIME | NULL | 归档时间 |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |

### 1.7 task_assignments 任务分配/待办表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| task_id | INT | FK tasks.id ON DELETE CASCADE | 任务 |
| user_id | INT | FK users.id ON DELETE CASCADE | 执行人 |
| status | ENUM('pendingAcceptance','inProgress','pendingReview','archived') | NOT NULL | 个人任务状态 |
| accepted_at | DATETIME | NULL | 接受/自动接受时间 |
| submitted_at | DATETIME | NULL | 提交完成时间 |
| reviewed_at | DATETIME | NULL | 审核时间 |
| reviewed_by | INT | FK users.id ON DELETE SET NULL | 审核人（任务发布者） |
| review_comment | TEXT | NULL | 最近一次审核意见 |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |
| UNIQUE(task_id, user_id) | | | 一个任务对同一人只有一条待办 |

### 1.8 task_reviews 审核记录表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| task_id | INT | FK tasks.id ON DELETE CASCADE | 任务 |
| assignment_id | INT | FK task_assignments.id ON DELETE CASCADE | 对应待办 |
| reviewer_id | INT | FK users.id ON DELETE SET NULL | 审核人 |
| result | ENUM('approved','rejected') | NOT NULL | 审核结果 |
| comment | TEXT | NULL | 审核意见 |
| created_at | DATETIME | NOT NULL | 时间 |

### 1.9 skill_tags 技能标签表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| name | VARCHAR(50) | UNIQUE NOT NULL | 标签名 |
| category | VARCHAR(50) | NULL | 分类（如 前端/后端/设计） |
| created_at | DATETIME | NOT NULL | 时间 |

### 1.10 user_skills 用户技能表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| user_id | INT | FK users.id ON DELETE CASCADE | 用户 |
| skill_tag_id | INT | FK skill_tags.id ON DELETE CASCADE | 标签 |
| proficiency | TINYINT | NOT NULL DEFAULT 3 | 熟练度 1-5 |
| UNIQUE(user_id, skill_tag_id) | | | |

### 1.11 user_settings 用户设置表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| user_id | INT | FK users.id ON DELETE CASCADE, UNIQUE | 用户 |
| theme | ENUM('light','dark') | NOT NULL DEFAULT 'light' | 主题 |
| font_size | ENUM('small','medium','large') | NOT NULL DEFAULT 'medium' | 字号 |
| font_family | VARCHAR(50) | NOT NULL DEFAULT 'system' | 字体族：system/serif/sans/monospace |
| created_at / updated_at | DATETIME | NOT NULL | 自动维护 |

### 1.12 audit_logs 审计日志表
| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INT AUTO_INCREMENT | PK | 主键 |
| user_id | INT | FK users.id ON DELETE SET NULL | 操作人 |
| action | VARCHAR(100) | NOT NULL | 动作标识，如 admin.database.execute |
| detail | TEXT | NULL | 明细 JSON 文本 |
| ip | VARCHAR(50) | NULL | 来源 IP |
| created_at | DATETIME | NOT NULL | 时间 |

## 2. 任务状态机
```
发布任务
  ├─ mandatory: 分配记录直接 inProgress（accepted_at=now）
  └─ optional : 分配记录 pendingAcceptance → 成员接受 inProgress / 拒绝则删除该分配
执行人提交完成 inProgress → pendingReview
审核通过 pendingReview → archived（任务全部归档 → task.archived + status=archived）
审核驳回 pendingReview → inProgress（记录 review，填入 review_comment）
任务取消：task.status=cancelled（发布者/团队管理员，仅未归档时）
```
- 任务聚合状态由后端服务每次分配变化后重算。
- 待办列表 = 当前用户所有 status != archived 的 task_assignments（含 archived 需筛选参数）。
- 只有任务发布者可以审核；发布者被注销时由团队管理员审核。

## 3. 权限规则（后端服务层强制校验）
1. 全局角色：superAdmin（内置唯一，初始化种子账号）> globalAdmin（由 superAdmin 设置）> user。
2. superAdmin / globalAdmin 可访问 /admin 下全部接口；superAdmin 额外可设置 globalAdmin。
3. 团队管理员（role=admin）唯一，可转让；可设置/撤销 subAdmin；可管理级别、团队资料、踢人、审核入团、生成邀请码、审核任务。
4. subAdmin：可审核入团、生成邀请码、踢出比自己级别低的成员、改变比自己级别低的成员级别。
5. 发布任务：仅团队管理员/子管理员或 `can_create_task=true` 的级别成员；不能给同级或更高级别成员布置任务（管理员/子管理员不受此限制，子管理员不可给管理员布置任务）。
6. 任务分配范围 = 级别 levelOrder 在 [targetLevelMin, targetLevelMax] 内的成员；指定成员模式则逐个校验级别规则。
7. 审核：默认任务发布者；发布者注销后由团队管理员。
8. 团队认证：新建团队 status=pending，总管理员/超级用户在管理后台审核为 active；pending 团队仅创建者可见，不可邀请他人。
9. 注销账号：软删除 is_active=false，username 加后缀释放，删除相关团队成员关系与入团申请；作为发布者的任务保留（createdBy=null），其待办删除；作为团队管理员需先转让或团队无其他成员时直接删除团队。
10. 全局管理员/超级用户数据库直管：仅允许 SELECT/INSERT/UPDATE/DELETE 单条语句，禁止 DDL、多语句、事务控制与文件操作；全部操作写审计日志。

## 4. v1.1 新增表与字段

> 详细定义见 `docs/development/collaborationContract.md` 第 1 节；v1.0 → v1.1 由
> `core/migrationService.py` 在启动时自动幂等升级（只加表/列/索引，不改既有枚举与数据）。

| 对象 | 说明 |
| --- | --- |
| 新表 `sub_teams` | 子团队（父团队内一层分组，子负责人、名称、简介） |
| 新表 `sub_team_members` | 子团队成员（必须是父团队成员，子团队内唯一） |
| 新表 `team_collaborations` | 团队/子团队协作关系（双方团队与子团队、双方对接人、状态 pending/active/rejected/ended） |
| 新表 `notifications` | 站内通知（接收人、类型、标题、内容、关联任务/协作、已读标记） |
| `tasks` 新增列 | sub_team_id、source_team_id、source_sub_team_id、target_team_id、target_sub_team_id、collaboration_id、collaboration_phase、collaboration_comment、auto_assigned、required_skill_names |
| `task_assignments` 新增列 | review_stage、target_reviewed_at、target_reviewer_id、target_review_comment、assignment_source |

> 协作任务约定：`tasks.team_id` 存放接收方团队（便于接收方任务列表与权限），
> `source_team_id` 存放发起方团队；普通任务的协作字段为空。

## 5. v1.1.1 新增表

### 5.1 system_settings 系统级键值配置
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 主键 |
| config_key | VARCHAR(100) UNIQUE NOT NULL | 配置键（AI 配置使用 ai.* 前缀） |
| config_value | TEXT NULL | 配置值 |
| updated_by | INT FK users SET NULL | 最后修改人 |
| created_at / updated_at | DATETIME | 时间 |

> 由 `Base.metadata.create_all` 自动创建（新表），v1.0/v1.1 数据库无需手动迁移；AI 配置默认回退环境变量，
> 在系统设置页保存后以数据库值为准。
