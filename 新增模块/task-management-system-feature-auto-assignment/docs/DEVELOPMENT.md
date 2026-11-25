# 开发文档 · 队友接手指南

> **读法**：第 1 节让你把项目跑起来；第 2、3 节是干活时随时查的速查表；
> 第 4 节教你怎么在我的代码上加东西；第 5 节是 5 条硬规矩。
> 总览见 [README.md](../README.md)。用户/分配/通知模块是 @Glenasak 写的，任务 CRUD 是队友的——两边都没被破坏。

---

## 1. 三分钟跑起来

```bash
# 前提：JDK 17+、Maven 3.6+、本机 MySQL 8（3306，root）
git clone https://github.com/BeiMingXiaoYu255/task-management-system.git
cd task-management-system
mvn spring-boot:run          # 自动建库建表插演示数据，无需手动建任何东西
```

- 页面：<http://localhost:8080/index.html>　接口根：<http://localhost:8080/api>
- 你的 MySQL 密码不是 `2550505`？用环境变量覆盖：`DB_USERNAME=root`、`DB_PASSWORD=你的密码`
- 跑测试（**不需要 MySQL**）：`mvn clean test`

**演示账号**（`db/data.sql` 自动插入）：

| 用户名 | 密码 | 角色 | 技能标签 |
| --- | --- | --- | --- |
| boss | boss123 | BOSS（发布任务） | — |
| alice / bob / carol | employee123 | EMPLOYEE（承接任务） | java,python,mysql / javascript,css,html / python,c++ |

---

## 2. 数据库速查（4 张表）

全部由 `db/schema.sql` 自动创建，**幂等**：重复启动不报错不重复插数。
列名下划线 ↔ Java 驼峰自动映射（`assignee_id → assigneeId`）。枚举存字符串名。

| 表 | 一句话 | 关键列 |
| --- | --- | --- |
| **task** | 任务（已有模块 + 我加的分配列） | `required_skills`（逗号分隔小写标签）、`assignee_id`、`assign_status`（UNASSIGNED/AUTO/MANUAL）、`publisher_id` |
| **user** | 用户 | `username`（唯一）、`password`（**BCrypt 摘要**，接口永不返回）、`role`（BOSS/EMPLOYEE） |
| **user_skill** | 用户技能标签 | `user_id` + `skill_name`（小写，联合唯一） |
| **notification** | 站内通知 | `user_id`、`task_id`、`title`、`content`、`read_flag`（0/1） |

> 改表结构的规矩见第 5 节第 3 条；老库怎么自动补列看 `schema.sql` 末尾的动态 ALTER 块（不用删库重建）。

---

## 3. 接口速查

统一响应 `{ code, message, data }`：`code=0` 成功，非 0 = HTTP 状态码（404 不存在、401 密码错、403 非老板、409 重名）。
分页 `data = { records, total, page, size }`。

### 任务（队友已有，没动）
| 方法 路径 | 用途 |
| --- | --- |
| GET `/api/tasks?keyword=&status=&priority=&page=&size=` | 分页查询 |
| GET / POST / PUT / DELETE `/api/tasks` 系列 | 详情 / 新建 / 修改 / 删除 |
| PATCH `/api/tasks/{id}/status?status=DONE` | 改状态 |

### 用户（我写的）
| 方法 路径 | 用途 | 注意 |
| --- | --- | --- |
| POST `/api/users/register` | 注册 `{username, password(6-100), nickname?, role?, skills?}` | role 不传默认 EMPLOYEE；重名 409 |
| POST `/api/users/login` | 登录，成功返回 `{id, role, skills...}` | **前端把 id 存下来当 userId 用** |
| GET `/api/users?role=EMPLOYEE&skill=java` | 按角色/技能查人 | |
| PUT `/api/users/{id}/skills` | 全量覆盖技能标签 `{skills:[...]}` | 空数组=清空 |

### 发布 + 自动分配（我写的，核心流程）
```bash
curl -X POST http://localhost:8080/api/tasks/publish -H "Content-Type: application/json" \
  -d '{"publisherId":1,"title":"开发登录接口","priority":"HIGH","requiredSkills":["java","python"]}'
```
| 你要做的 | 系统行为 |
| --- | --- |
| 老板调 publish（`publisherId` 必须是 BOSS） | 创建任务 → 自动选人 → 写回 `assignee_id` → 发通知，一个事务全做完 |
| 想知道分给谁了 | 看响应里 `data.assigneeId` / `data.assignStatus`（AUTO=算法分的，UNASSIGNED=没人匹配） |

**选人规则**：`得分 = 技能命中率×100 − 未完成任务数×5`；零交集直接排除；低于 50 分视为无匹配。
**没人匹配时**：任务留在 UNASSIGNED，老板收到"分配失败"通知 → 前端可让老板手动指派（把 `assignee_id` 和 `assign_status=MANUAL` 更新掉即可）。

**四调度模式**（`application.yml` → `assignment.dispatch-mode`，可用环境变量 `ASSIGNMENT_DISPATCH_MODE` 覆盖）：

| 模式 | 行为 |
| --- | --- |
| LOCAL_ONLY | 只用规则引擎 |
| LOCAL_FIRST（默认） | 规则优先，没匹配或出错 → 自动用 LLM |
| LLM_FIRST | LLM 优先，失败/没匹配 → 自动用规则 |
| LLM_ONLY | 只用 LLM，不可用就直接 UNASSIGNED |

**LLM 配置**（不配也能跑，只是没有备用路；key 别提交进仓库）：
```bash
export LLM_BASE_URL=https://api.deepseek.com        # 智谱GLM: https://open.bigmodel.cn/api/paas/v4
export LLM_API_KEY=sk-xxx
export LLM_MODEL=deepseek-chat                       # glm-4-flash / gpt-4o-mini
```

### 通知（我写的，前端轮询）
| 方法 路径 | 用途 |
| --- | --- |
| GET `/api/notifications?userId=2&unreadOnly=false&page=1&size=10` | 分页查通知（时间倒序） |
| GET `/api/notifications/unread-count?userId=2` | 未读角标 |
| PATCH `/api/notifications/{id}/read?userId=2` | 单条已读（只能标自己的） |
| PATCH `/api/notifications/read-all?userId=2` | 全部已读 |

通知是系统自动发的（分配成功→人选+候选人；没匹配→老板），**前端只管每 10~30 秒轮询一次**。

---

## 4. 在我的代码上加东西

**加一张表 + 一套接口**（以"评论"为例，5 步照抄现有模块的样式）：

1. `db/schema.sql` 加 `CREATE TABLE IF NOT EXISTS comment ...`（**必须幂等**）
2. `entity/Comment.java`（`@Data`，字段注释写清楚）
3. `mapper/CommentMapper.java` + `resources/mapper/CommentMapper.xml`（SQL 只写在 XML 里）
4. `dto/CommentCreateRequest.java`（校验注解）+ `vo/CommentVO.java`（`from()` 静态转换）
5. `service/CommentService(+Impl)` 写业务 → `controller/CommentController` 只做转发和包 `ApiResponse`
6. `src/test` 同包路径补两层测试（Service 用 Mockito 模拟 Mapper；Controller 用 `@WebMvcTest`，照抄 `UserServiceImplTest` / `UserControllerTest` 的模板）

**加一条推荐链路**（比如以后接向量检索）：实现 `service/assignment/RecommendationRoute` 接口，
再到 `AssignmentServiceImpl.dispatch` 的 switch 加一个分支——回退和通知逻辑自动复用。

**联调时接口不够用？** 不要自己 mock，把你要的请求/响应格式发到群里，我加接口，契约以本文档和 README 为准。

---

## 5. 五条硬规矩

1. **分层不越界**：controller 只转发；业务在 service；SQL 只在 mapper XML；dto 进、vo 出，entity 不出接口。
2. **响应统一 `ApiResponse`**，错误用 `BusinessException(code, message)` 抛，全局异常处理器接住。
3. **`schema.sql` 只许加不许改**：新表用 `IF NOT EXISTS`；给已有表加列必须用文件末尾的"INFORMATION_SCHEMA 判断 + 动态 ALTER"写法，否则别人的库启动直接炸。
4. **commit 用 Conventional Commits**（`feat(user): xxx` / `fix: xxx`），**不要加任何 AI 署名或 Co-author**。
5. **提交前 `mvn clean test` 必须全绿**，不改挂别人模块的测试。

## 已知边界（不用大惊小怪）

- 认证是课程级简化：接口用 `userId` 参数标身份，没有 JWT——以后升级不影响接口结构；
- LLM 返回有随机性，自动化测试全部用 mock；配好 key 后想真实验证：发布一个 `requiredSkills:["rust"]` 的任务（没人匹配 → 看回退到 LLM，响应 `assignStatus=AUTO` 即通）；
- `required_skills` 是逗号串不是子表，够本课程用；以后要按标签统计再迁移（方案写在 schema.sql 注释里）。
