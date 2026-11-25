# 任务管理系统（task-management-system）

课程设计项目：轻量级任务管理系统。采用 **Spring Boot 3 + Spring MVC + MyBatis + MySQL**，
前后端分离：后端提供 REST 接口（统一返回 `{ code, message, data }`），
`src/main/resources/static` 下附带一个原生 JS 演示页面，方便直接联调；
后续可以用 Vue / React 单独实现前端，后端接口契约不变。

> 团队协作请看 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)：数据库设计、接口契约、
> 智能分配规则与 LLM 配置、新模块扩展指南都在那里。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 运行环境 | JDK 17+（开发机 JDK 21）、Maven 3.6+ |
| Web 框架 | Spring Boot 3.2.4 / Spring MVC 6.1 |
| 持久层 | MyBatis 3.0.3（XML 映射）+ MySQL 8.0 |
| 参数校验 | Jakarta Bean Validation（Hibernate Validator） |
| 测试 | JUnit 5 + Mockito + MockMvc |
| 其他 | Lombok、内嵌 Tomcat、Jackson |

## 目录结构（MVC 分层）

```text
task-management-system/
├── pom.xml
├── README.md
└── src
    ├── main
    │   ├── java/cn/edu/cjlu/taskmanagement
    │   │   ├── TaskManagementApplication.java   # 启动类
    │   │   ├── controller/                      # 【C】接口层：接收请求、参数校验、包装响应
    │   │   │   └── TaskController.java
    │   │   ├── service/                         # 业务层：业务规则、默认值、分页边界
    │   │   │   ├── TaskService.java
    │   │   │   └── impl/TaskServiceImpl.java
    │   │   ├── mapper/                          # 持久层：只做数据库操作
    │   │   │   └── TaskMapper.java
    │   │   ├── entity/                          # 【M】数据库实体与枚举
    │   │   │   ├── Task.java
    │   │   │   ├── TaskStatus.java
    │   │   │   └── TaskPriority.java
    │   │   ├── dto/                             # 请求参数对象（带校验注解）
    │   │   ├── vo/                              # 返回给前端的视图对象
    │   │   ├── common/                          # 统一响应、分页、全局异常处理
    │   │   └── config/                          # MyBatis 扫描、跨域配置
    │   └── resources
    │       ├── application.yml                  # 数据源、MyBatis、Jackson 配置
    │       ├── db/schema.sql                    # 建表脚本（幂等）
    │       ├── db/data.sql                      # 示例数据（幂等）
    │       ├── mapper/TaskMapper.xml            # SQL 映射
    │       └── static/                          # 【V】演示前端（HTML/CSS/JS）
    └── test/java/cn/edu/cjlu/taskmanagement
        ├── controller/TaskControllerTest.java   # MockMvc 切片测试
        └── service/impl/TaskServiceImplTest.java# Mockito 单元测试
```

分层调用关系：`controller → service → mapper → MySQL`，
数据在各层之间用 `dto`（入参）/ `entity`（持久化）/ `vo`（出参）区分，避免互相污染。

## 环境要求

- **JDK 17+**（`pom.xml` 中 `java.version=17`）
- **Maven 3.6+**
- **MySQL 8.0**，本机 3306 端口已启动即可

## 数据库配置

默认连接 `localhost:3306`，用户 `root`，密码 `2550505`（本机开发机的 MySQL 密码）：

```yaml
# src/main/resources/application.yml
url: jdbc:mysql://localhost:3306/task_management?...&createDatabaseIfNotExist=true
username: ${DB_USERNAME:root}
password: ${DB_PASSWORD:2550505}
```

- 数据库 `task_management` **不需要手动创建**：JDBC 参数 `createDatabaseIfNotExist=true` 会自动建库；
- 表结构和示例数据由 `db/schema.sql`、`db/data.sql` 在每次启动时自动执行，
  两个脚本都是幂等的（`CREATE TABLE IF NOT EXISTS` / `INSERT IGNORE`），重启不会重复插入；
- 修改账号密码请用环境变量，不要把真实密码写进仓库：

```powershell
$env:DB_USERNAME = "root"
$env:DB_PASSWORD = "你的密码"
```

## 启动

```bash
# 1. 编译并运行单元测试（不需要数据库）
mvn clean test

# 2. 打包
mvn clean package

# 3. 启动（二选一）
mvn spring-boot:run
java -jar target/task-management-system-1.0.0.jar
```

启动后：

- 演示页面：<http://localhost:8080/index.html>
- 接口根路径：<http://localhost:8080/api/tasks>

## 接口清单

统一响应体：`{ "code": 0, "message": "success", "data": ... }`，`code != 0` 即失败，HTTP 状态码同步。

| 方法 | 路径 | 说明 | 请求参数 |
| --- | --- | --- | --- |
| GET | `/api/tasks` | 分页查询 | `keyword`（标题/描述模糊）、`status`、`priority`、`page`、`size` |
| GET | `/api/tasks/{id}` | 查询详情 | — |
| POST | `/api/tasks` | 新建任务 | JSON：`title`（必填）、`description`、`priority`、`dueDate` |
| PUT | `/api/tasks/{id}` | 全量修改 | JSON：`title`（必填）、`status`（必填）、`description`、`priority`、`dueDate` |
| PATCH | `/api/tasks/{id}/status` | 只改状态 | 查询参数：`status=TODO\|IN_PROGRESS\|DONE` |
| DELETE | `/api/tasks/{id}` | 删除任务 | — |
| POST | `/api/tasks/publish` | 发布任务（老板）：创建 + 自动分配 | JSON：`publisherId`（必填，须为 BOSS）、`title`（必填）、`description`、`priority`、`dueDate`、`requiredSkills`（技能标签数组） |
| POST | `/api/users/register` | 注册用户 | JSON：`username`（必填）、`password`（必填，6-100 位）、`nickname`、`role`（BOSS/EMPLOYEE，默认 EMPLOYEE）、`skills`（技能标签数组，可空） |
| POST | `/api/users/login` | 登录 | JSON：`username`、`password` |
| GET | `/api/users` | 分页查询用户 | `role`、`skill`、`page`、`size` |
| GET | `/api/users/{id}` | 用户详情（含技能标签） | — |
| PUT | `/api/users/{id}/skills` | 全量更新技能标签 | JSON：`skills`（数组） |
| GET | `/api/notifications` | 分页查询通知（前端轮询） | `userId`（必填）、`unreadOnly`（默认 false）、`page`、`size` |
| GET | `/api/notifications/unread-count` | 未读数（角标） | `userId`（必填） |
| PATCH | `/api/notifications/{id}/read` | 标记单条已读（仅限本人） | 查询参数：`userId`（必填） |
| PATCH | `/api/notifications/read-all` | 全部已读 | 查询参数：`userId`（必填） |

示例：

```bash
curl "http://localhost:8080/api/tasks?page=1&size=10&status=TODO"

curl -X POST http://localhost:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"完成需求分析\",\"priority\":\"HIGH\",\"dueDate\":\"2026-11-10T18:00:00\"}"

curl -X PATCH "http://localhost:8080/api/tasks/1/status?status=DONE"

curl -X POST http://localhost:8080/api/users/register \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"secret123\",\"role\":\"EMPLOYEE\",\"skills\":[\"java\",\"python\"]}"

curl -X POST http://localhost:8080/api/users/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"alice\",\"password\":\"secret123\"}"

curl -X POST http://localhost:8080/api/tasks/publish \
  -H "Content-Type: application/json" \
  -d "{\"publisherId\":1,\"title\":\"开发登录接口\",\"priority\":\"HIGH\",\"requiredSkills\":[\"java\",\"python\"]}"
```

## 测试

```bash
mvn test
```

- `TaskServiceImplTest`：用 Mockito 模拟 Mapper，验证默认值、404 业务异常、分页边界；
- `TaskControllerTest`：用 `@WebMvcTest` + MockMvc 验证响应结构、参数校验、错误码映射；
- `UserServiceImplTest`：验证注册默认值与 BCrypt 加密、用户名冲突 409、登录失败统一 401、技能标签规范化、分页钳制；
- `UserControllerTest`：验证注册/登录响应结构、参数校验、401/404 错误码映射；
- `LocalRecommendationEngineTest`：验证技能命中率打分、负载惩罚、同分并列排序、零交集排除、阈值过滤；
- `AssignmentServiceImplTest`：验证自动分配成功/无匹配两条链路的通知生成，以及 LLM 模式未接入时的行为；
- `TaskPublishServiceImplTest` + `TaskAssignmentControllerTest`：验证"老板身份校验 → 创建 → 分配 → 回查"发布流程与接口契约；
- `LlmRecommendationClientTest` + `AssignmentServiceImplTest`：验证 LLM 链路解析/降级与四调度模式、主路失败自动回退；
- `NotificationServiceImplTest` + `NotificationControllerTest`：验证通知分页、未读数、本人已读校验与 404 映射。

> 演示账号（`db/data.sql` 自动插入）：`boss / boss123`（BOSS），
> `alice|bob|carol / employee123`（EMPLOYEE）。密码一律 BCrypt 摘要存储。

两层测试都不依赖 MySQL，所以 CI / 无数据库环境也能跑通。

## 新增一个业务模块的步骤

以「用户」为例：

1. `entity/User.java` + `mapper/UserMapper.java` + `resources/mapper/UserMapper.xml`
2. `dto/UserCreateRequest.java`（校验注解）、`vo/UserVO.java`
3. `service/UserService.java` + `service/impl/UserServiceImpl.java`
4. `controller/UserController.java`（`@RequestMapping("/api/users")`）
5. `db/schema.sql` 增加建表语句，补单元测试

## 说明

- 智能分配配置在 `application.yml` 的 `assignment.*`：`dispatch-mode`
  四选一（`LOCAL_ONLY` / `LLM_ONLY` / `LOCAL_FIRST`（默认） / `LLM_FIRST`，环境变量
  `ASSIGNMENT_DISPATCH_MODE` 可覆盖）、`match-threshold`（匹配阈值）、
  `workload-penalty`（负载惩罚分）。打分公式：技能命中率 × 100 − 活跃任务数 × 负载惩罚；
- LLM 备用链路（Push 3）：OpenAI 兼容协议，`llm.*` 三项（`base-url`/`api-key`/`model`）
  全配置才启用，api-key 走环境变量 `LLM_API_KEY`。`*_FIRST` 模式下主路失败或无匹配
  自动回退备用路；DeepSeek / 智谱 GLM / OpenAI 换厂商只改配置，详见 `docs/DEVELOPMENT.md`；
- `spring.sql.init.mode=always` 适合课程设计演示：换台电脑只要有 MySQL 就能直接跑；
  若以后部署到生产环境，建议改为 `never` 并用 Flyway/Liquibase 管理迁移。
- MyBatis SQL 日志通过 `mybatis.configuration.log-impl` 输出到控制台，方便学习调试。
