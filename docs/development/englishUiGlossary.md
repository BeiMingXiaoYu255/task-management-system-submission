# 英文 UI 翻译规范与术语表（v1.2 界面英文化）

> 目标：将系统中所有**用户可见文字**改为英文；代码注释、docstring、开发文档保持中文。
> 本文件同时作为智能体翻译时的统一术语与验收标准。

## 1. 范围
- 前端 `Frontend/src` 中所有 JSX 文本、字符串字面量、模板字符串、ARIA 标签、title/placeholder、
  toast/错误/空态/加载文案、枚举与状态中文映射、日期/相对时间格式、HTML title 与 lang。
- `Frontend/index.html`（title/lang）、侧边栏品牌名、Tauri 窗口标题。
- 后端返回给界面展示的文字：异常 message、成功提示、通知标题/内容、AI 推荐理由与状态说明、
  连通性测试提示、初始化默认技能标签、内置超级用户昵称、演示数据。
- 不翻译：代码注释、docstring、日志、开发/接口/测试文档、数据库字段名、URL。

## 2. 表达规则
- 英文使用美式拼写、句首大写、按钮用祈使句（Save / Cancel / Confirm / Reject / Approve / Retry）。
- 不使用中文标点；省略号用 `...`（如 "Loading..."）；破折号用 " - "。
- 数量与复数：简单场景用 "1 member / 2 members"；可写 "`{count} members`"。
- 日期格式：`MMM D, YYYY`（如 "Nov 25, 2026"）；时间 24 小时制 `HH:mm`；
  相对时间："Just now / 5 minutes ago / 2 hours ago / 3 days ago / in 2 days / Overdue by 2 days"。
- 后端错误 message 面向用户、简短、无需错误码前缀；前端错误回退文案统一英文。
- 保持语气中性、低饱和极简风格，避免感叹号。

## 3. 统一术语表
| 中文 | 英文 |
| --- | --- |
| 任务管理系统 | Task Management System（品牌简称 Task Management） |
| 仪表盘 | Dashboard |
| 团队 | Team |
| 子团队 | Sub-team |
| 团队成员 | Team Member |
| 团队管理员 | Team Admin |
| 子管理员 | Sub-admin |
| 子负责人 | Sub-team Lead |
| 普通成员 | Member |
| 超级用户 | Super Admin |
| 全局管理员 | Global Admin |
| 普通用户 | Standard User |
| 管理后台 | Admin Console |
| 个人资料 | Profile |
| 设置 / 系统设置 | Settings / System Settings |
| 任务 | Task |
| 待办 | To-do |
| 便签 | Sticky Notes |
| 发布任务 | Publish Task |
| 指派 / 指定成员 | Assign |
| 优先级 | Priority（Low / Medium / High / Urgent） |
| 截止时间 | Due Date |
| 逾期 | Overdue |
| 状态 | Status（Published / In Progress / Pending Review / Archived / Cancelled / Pending Assignment / Pending Acceptance） |
| 审核 | Review |
| 通过 / 驳回 | Approve / Request Changes（按钮用 Approve / Reject） |
| 归档 | Archive |
| 团队认证 | Team Certification（Certified / Pending / Rejected） |
| 加入方式 | Join Method（Free Join / Approval Required / Invite Code） |
| 入团申请 | Join Request |
| 成员级别 | Member Level（Level） |
| 转让团队 | Transfer Ownership |
| 踢出成员 | Remove Member |
| 协作 / 协作关系 | Collaboration |
| 协作中心 | Collaboration Center |
| 对接人 | Liaison |
| 发起方 / 接收方 | Initiator / Receiver |
| 发起单位 / 接收单位 | Initiating Unit / Receiving Unit |
| 确认接单 | Accept Task |
| 指派执行人 | Assign Assignee |
| 双审核 | Two-stage Review |
| 接收方审核 / 发起方审核 | Receiver Review / Initiator Review |
| 通知 | Notifications |
| 未读 / 全部已读 | Unread / Mark All as Read |
| AI 自动分配 | AI Auto-assignment |
| AI 推荐 | AI Recommendation |
| 调度模式 | Dispatch Mode（Local Only / LLM Only / Local First / LLM First） |
| 本地规则引擎 | Local Rule Engine |
| 大模型 / LLM | LLM |
| 候选上限 | Max Candidates |
| 匹配阈值 | Match Threshold |
| 负载惩罚 | Workload Penalty |
| API 密钥 | API Key |
| 连通性测试 | Connectivity Test |
| 技能标签 | Skill Tags |
| 所需技能 | Required Skills |
| 保存 / 取消 / 删除 | Save / Cancel / Delete |
| 编辑 / 新建 | Edit / Create |
| 确认 / 拒绝 | Confirm / Reject |
| 搜索 / 筛选 / 重置 | Search / Filter / Reset |
| 上一页 / 下一页 | Previous / Next |
| 共 N 条 | Total: N |
| 暂无数据 | No data yet |
| 加载中 | Loading... |
| 出错了，请重试 | Something went wrong. Please try again. |

## 4. 验收
- 前端：`cd Frontend && node checkEnglishUi.mjs` 退出码 0（AST 级检测，忽略注释）。
- 后端：`python scripts/checkBackendEnglish.py` 退出码 0（AST 级检测，忽略 docstring/注释）。
- `npx tsc --noEmit`、`npm run build`、`npm test`、`npx playwright test` 全部通过。
- 后端 pytest 全量通过（断言同步更新为英文）。
- 重新截取全部界面截图（英文界面）。

## 5. 分工
- backend-account：auth/user/team/admin 模块消息。
- backend-task：task/todo/dashboard/setting 模块消息。
- backend-collaboration：collaboration/sub-team 及协作通知文案。
- backend-ai：AI/LLM/配置/推荐理由/自动分配通知文案。
- Lead：core/exceptions/permissions、initialization、seed 演示数据、系统名称、通知服务基础、验收与提交。
- 前端 F1：设计系统 ui/**、layout、auth、contexts、utils、hooks、枚举/展示工具、index.html、Tauri 标题。
- 前端 F2：team/task/todo 页面、组件、api、types（AI 专属任务组件除外）。
- 前端 F3：dashboard/profile/settings（AI 配置除外）/admin 页面与组件。
- 前端 F4：collaboration/sub-team/notification/AI 推荐/AI 配置 页面、组件、api、types。
- 文件互不重叠；注释保留中文；只翻译字符串，不改逻辑。
