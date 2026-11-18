# 开发规范与协作约定

## 1. 命名规范（强约束）
- **所有代码标识符必须使用全拼英文，禁止缩写**（如 `user` 不写 `usr`，`task` 不写 `tsk`；通用公认缩写如 `id`、`api`、`url`、`http`、`json` 允许）。
- **文件命名使用驼峰命名法**：Python 模块小驼峰 `userService.py`；React 组件文件大驼峰 `TaskCard.tsx`；工具/接口小驼峰 `httpClient.ts`。
- **函数/变量**：小驼峰 `getUserById`；**类**：大驼峰 `UserService`；**常量**：全大写蛇形 `MAX_LOGIN_ATTEMPTS`。
- **数据库**：表名/列名 snake_case；**API JSON**：camelCase。
- 目录名使用小写全拼单词（`controllers`、`repositories`）。
- 所有函数 ≤100 行；每个文件建议 ≤300 行（后端单文件 ≤300 行，超出拆分）。
- 每个函数、类、模块、复杂变量必须写中文注释；复杂函数需说明实现原理。

## 2. 后端分层（MVC 强化版）
```
controllers/   接口层：FastAPI APIRouter，只做参数校验、调用 Service、返回 Schema，不写业务逻辑与 SQL
services/      业务层：权限校验、事务边界、状态机、组合多个 Repository
repositories/  数据访问层：只封装 SQLAlchemy 查询，不写业务判断
models/        ORM 模型（继承 Base）
schemas/       Pydantic 请求/响应模型
core/          配置、数据库、Redis、JWT、密码、异常、权限依赖
utils/         纯函数工具
main.py        应用装配：路由注册、异常处理、CORS、静态文件、启动事件
```
- **接口文件**：`controllers/*Controller.py` 只包含路由定义；每个模块一个控制器文件。
- **父类与子类分文件**：抽象基类放 `repositories/baseRepository.py`、`services/baseService.py`，具体子类放各自模块文件。
- 控制器路由统一 `prefix="/api/v1"`，Tags 中文；HTTP 方法语义正确（GET 无副作用）。
- 所有数据库写操作使用事务（`with db.begin()` 或显式 commit/rollback）。
- 错误统一抛 `AppException(code, message, statusCode)`，由全局异常处理器转换。
- 敏感信息（密码哈希、token secret）不得出现在日志与响应中。

## 3. 前端规范
- 组件文件 ≤300 行；单文件一个默认导出组件 + 少量类型导出。
- 每个可复用组件必须有 `.module.css` 同名样式文件（页面级样式也允许 Page.module.css）。
- 禁止引入 UI/图标/图表/状态库；禁止内联颜色值（必须用 CSS 变量）。
- 页面容器组件只负责数据获取与组合；展示组件无副作用。
- 所有按钮/链接有可读文本或 aria-label；键盘可操作（Esc 关闭弹窗、Enter 提交）。
- 严格的 TypeScript：不得使用 `any`，API 返回值必须定义类型。

## 4. 端口与本地环境
| 服务 | 地址 | 账号 |
| --- | --- | --- |
| 后端 API | http://127.0.0.1:8765 | — |
| 前端开发服务器 | http://127.0.0.1:5173 | — |
| MySQL 开发实例 | 127.0.0.1:3307 | 库 task_management / task_management_test，用户 taskadmin / taskadmin123 |
| Redis 开发实例 | 127.0.0.1:6380 | 无密码 |
| 局域网访问 | http://<本机IP>:8765 | 由后端直接托管前端构建产物 |

- 环境变量模板：`Backend/.env.example`；本地开发复制为 `Backend/.env`。
- 后端虚拟环境：`Backend/.venv`，已安装依赖；命令：`.\.venv\Scripts\python.exe -m uvicorn runServer:app --reload --port 8765`。
- 前端：`npm run dev`；构建 `npm run build`。
- 测试：`Backend/.venv/Scripts/python.exe -m pytest`；前端 `npm test`。

## 5. 认证与权限（实现要点）
- JWT HS256，payload：`{ sub: userId, username, globalRole, exp, type:'access' }`，默认 7 天；secret 来自环境变量，开发默认值仅用于本地。
- 密码 bcrypt（cost 12）；登录失败计数存 Redis（key `login:fail:{username}:{ip}`，5 分钟窗口）。
- token 黑名单：logout 后 `token:blacklist:{jti}`，TTL=剩余有效期；jti 放入 payload。
- 所有团队接口必须先校验成员身份；权限判断集中在 `core/permissions.py`，禁止在控制器里散落 if。
- 管理后台数据库直管接口必须记录审计日志。

## 6. 测试要求
- 每个后端模块至少覆盖：正常流程、权限拒绝、参数校验、关键状态机分支。
- 测试使用独立库 `task_management_test`，每个测试函数前清库（conftest 提供 fixtures）。
- 接口测试直接用 FastAPI TestClient（httpx），断言状态码 + 响应结构 + 数据库副作用。
- 前端对工具函数/关键组件做 Vitest 测试。
- 提交前必须通过：后端全部 pytest、前端 `npm run build`（tsc 类型检查）。

## 7. Git 约定
- 提交信息格式：`模块: 说明`（如 `任务: 实现审核驳回状态机`）。
- 不提交 `.venv`、`node_modules`、`Runtime/`、`.devdata/`、安装包产物。
