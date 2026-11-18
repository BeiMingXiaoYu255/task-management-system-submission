# v1.1 AI 模块移植契约（唯一权威）

> 来源：`新增模块/task-management-system-feature-auto-assignment`（Java Spring Boot 版），本轮完整移植到
> Python/FastAPI 后端（不引入 Java 运行时），并按本项目模型适配。核心算法、调度模式、LLM 协议保持等价。

## 1. 配置（Backend/.env 与 Settings）
| 配置项 | 环境变量示例 | 默认值 | 说明 |
| --- | --- | --- | --- |
| assignmentDispatchMode | ASSIGNMENTDISPATCHMODE | LOCAL_FIRST | LOCAL_ONLY / LLM_ONLY / LOCAL_FIRST / LLM_FIRST |
| assignmentMatchThreshold | ASSIGNMENTMATCHTHRESHOLD | 50 | 本地候选人最低分 |
| assignmentWorkloadPenalty | ASSIGNMENTWORKLOADPENALTY | 5 | 每个活跃待办的负载惩罚分 |
| llmBaseUrl | LLMBASEURL | "" | OpenAI 兼容根地址（DeepSeek: https://api.deepseek.com） |
| llmChatPath | LLMCHATPATH | /v1/chat/completions | 对话接口路径（智谱 GLM: /chat/completions） |
| llmApiKey | LLMAPIKEY | "" | API Key（不写入仓库） |
| llmModel | LLMMODEL | "" | 模型名（deepseek-chat / glm-4-flash / gpt-4o-mini） |
| llmTimeoutSeconds | LLMTIMEOUTSECONDS | 20 | 读取超时 |
| llmMaxCandidates | LLMMAXCANDIDATES | 20 | 送入提示词/采纳的最大候选人数 |

LLM 三项（baseUrl/apiKey/model）齐全才算 LLM 可用；未配置时 LLM_* 模式/回退会给出中文原因并落到本地引擎（LLM_ONLY 时返回空候选并由发布者手动指派）。

## 2. 本地推荐引擎（等价移植 Java LocalRecommendationEngine）
- 候选人池：当前团队中符合发布权限的目标成员（见 §3），且排除发布者本人；
- 所需技能：优先取请求中的 `requiredSkillNames`；未提供时从任务标题/描述中匹配团队成员已有技能标签名称（大小写不敏感、去重）；
- 打分：`score = round(命中率 × 100) − 活跃待办数 × workloadPenalty`；
  命中率 = 命中技能数 / 所需技能数（无技能要求时为 1.0）；
- 与所需技能零交集的候选人排除（所需技能非空时）；
- 低于 `matchThreshold` 的候选人排除；
- 排序：得分降序 → 活跃待办数升序 → 用户 ID 升序（稳定可复现）；
- 活跃待办数 = 该用户所有 status ∈ {pendingAcceptance, inProgress, pendingReview} 的 task_assignments 数量。

## 3. 候选人与权限适配
- 团队管理员：候选人为团队全体其他成员（排除本人）；
- 子管理员：排除管理员与本人；
- 普通成员：仅当其级别 canCreateTask=true，候选人为级别低于自己的成员；
- 请求可带级别范围（targetLevelMin/targetLevelMax）用于在任务表单选择范围时收敛候选人；
- 返回最多 10 名候选（按配置可调）。

## 4. LLM 链路（等价移植 Java LlmRecommendationClient）
- 请求：POST `{llmBaseUrl}{llmChatPath}`，Header `Authorization: Bearer <key>`，体为 OpenAI Chat Completions：
  `{ model, temperature: 0.2, messages: [system, user] }`；
- system prompt：与 Java 版一致的「任务分配助手」要求，只输出 JSON：
  `{"rankedUserIds":[候选人ID降序],"reason":"50字以内理由"}`；
- user prompt：任务所需技能 + 候选人清单（ID | 用户名 | 技能标签 | 当前活跃任务数）；
- 解析：允许返回带 markdown 代码块的 JSON；忽略不存在的用户 ID；score 按排名 100/90/80…；
- 失败（未配置/网络错误/非 JSON/空结果）→ 抛内部异常，由调度器按模式回退；
- 使用标准库 urllib.request（不新增依赖），超时控制；日志脱敏不输出 API Key。

## 5. 调度模式（等价 Java AssignmentServiceImpl）
| 模式 | 行为 |
| --- | --- |
| LOCAL_ONLY | 只用本地引擎 |
| LLM_ONLY | 只用 LLM；不可用/失败返回空候选（reason 说明） |
| LOCAL_FIRST | 本地有候选则用本地，否则尝试 LLM |
| LLM_FIRST | LLM 有候选则用 LLM，否则回退本地 |
最终返回 `{ route: 'local'|'llm'|null, reason, candidates: CandidateItem[], topCandidate } `。

## 6. 接口变更

### 6.1 `GET /ai/status`（扩展）
```json
{
  "provider": "hybrid",
  "available": true,
  "dispatchMode": "LOCAL_FIRST",
  "localAvailable": true,
  "llmConfigured": false,
  "llmModel": "",
  "matchThreshold": 50,
  "workloadPenalty": 5,
  "description": "本地规则引擎可用；LLM 未配置..."
}
```

### 6.2 `POST /teams/{teamId}/ai/recommend-assignees`（响应升级）
请求：
```json
{ "title": "...", "description": "...", "priority": "high",
  "targetLevelMin": null, "targetLevelMax": null,
  "requiredSkillNames": ["python", "database"], "maxCandidates": 10 }
```
响应：
```json
{ "route": "local", "reason": "按技能命中率与负载打分",
  "candidates": [ { "userId": 2, "username": "developerA", "nickname": "开发者小周",
    "levelName": "中级成员", "levelOrder": 2, "score": 95, "matchRatio": 1.0,
    "matchedSkills": ["python"], "activeTasks": 1,
    "reasons": ["命中技能 python、database", "当前 1 项活跃待办，负载较低"],
    "route": "local" } ] }
```
> 前端 `types/ai.ts` 与 `api/aiApi.ts` 需同步升级（响应由数组改为对象）。

### 6.3 发布任务支持自动分配（扩展 `POST /teams/{teamId}/tasks`）
请求新增字段：
- `autoAssign?: boolean`（默认 false）：为 true 时忽略 targetUserIds，由 AI 调度器自动选人；
- `requiredSkillNames?: string[]`：AI 分配所需技能标签（可空，空则从标题/描述推导）。
行为：
- 自动分配成功 → 创建任务与执行人待办（assignment_source='ai'，task.auto_assigned=true），任务进入正常执行流程；
- 无匹配 → 任务创建成功但 status=published 且无执行人（auto_assigned=false），通知发布者手动指派；
- 请求带 assignmentMode/acceptanceMode 时，autoAssign 任务仍按 acceptanceMode 决定是否直接进入进行中；级别范围可用于收敛候选。
- 响应 TaskDetail 新增字段：`autoAssigned: boolean`、`requiredSkillNames: string[]`。

### 6.4 手动指派（新增，用于自动分配失败 / 管理员改派）
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| POST | /tasks/{taskId}/assignments | 发布者/团队管理员 | `{ userIds: number[] }` 为无执行人的任务指派成员（生成 manual 来源待办），通知被指派者 |

### 6.5 通知（AI 相关）
| 事件 | 接收人 | type |
| --- | --- | --- |
| 自动分配成功 | 首选执行人 | taskAutoAssigned |
| 自动分配成功 | 其他匹配候选 | taskMatchReminder |
| 自动分配无匹配 | 发布者 | taskAssignFailed |
| 手动指派 | 被指派者 | taskAssigned |
| 普通任务审核通过/驳回 | 执行人 | taskReviewResult |

## 7. 前端变更（frontend AI 模块）
1. `AiRecommendPanel` 升级：展示调度模式/route/原因/匹配率/活跃负载/匹配技能；「一键选择首选」「全选推荐」；
2. `TaskForm` 发布模式新增「AI 自动分配」开关与「所需技能标签」多选（可空），开启后不再强制选择接收成员；提交后展示分配结果（成功执行人/无匹配提示）；
3. 顶栏新增通知铃铛（未读数轮询 20 秒、下拉最近 5 条、全部已读、跳转通知中心 /notifications）；
4. `ApiRecommendResponse`、`TaskItem/TaskDetail` 类型与 api 层同步扩展；AI 状态面板展示 LLM 配置状态与调度模式。

## 8. 测试要求
- 本地引擎：命中率/负载惩罚/零交集排除/阈值过滤/稳定排序/空技能列表；
- 调度模式：四种模式的选中与回退、LLM 未配置时的原因、异常降级；
- LLM 客户端：用 mock HTTP 验证请求体、JSON 解析（含 markdown 代码块）、非法返回异常、Key 脱敏；
- 自动分配发布：成功/无匹配/权限拒绝/通知生成；
- 通知接口：分页、未读数、已读幂等与越权 404。

## 9. AI 配置持久化与连通性测试（v1.1.1）

> 目的：把 AI（LLM/调度）配置与连通性测试放进「系统设置」页面，管理员可在界面修改并即时验证，不再只能改环境变量。

### 9.1 数据表 `system_settings`
系统级键值配置表（与用户级 user_settings 区分）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INT PK | 主键 |
| config_key | VARCHAR(100) UNIQUE | 配置键，AI 配置统一使用 `ai.` 前缀 |
| config_value | TEXT NULL | 配置值（字符串，数值/枚举在服务层转换） |
| updated_by | INT FK users SET NULL | 最后修改人 |
| created_at / updated_at | DATETIME | 时间 |

AI 配置键：
`ai.llmBaseUrl`、`ai.llmChatPath`、`ai.llmApiKey`、`ai.llmModel`、`ai.llmTimeoutSeconds`、
`ai.llmMaxCandidates`、`ai.dispatchMode`、`ai.matchThreshold`、`ai.workloadPenalty`。

**有效配置解析优先级**：数据库 `system_settings` 中的值 > 环境变量/默认 Settings > 内置默认值。
数据库中没有对应键时回退环境变量（便于开发/服务器用 env 管理）；一旦在界面保存，则以数据库为准。
启动时无需缓存，每次调用读取数据库（轻量查询）；保存后立即生效。

### 9.2 接口（前缀 /api/v1/settings/ai-config）
| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | /settings/ai-config | 登录用户 | 读取有效 AI 配置（apiKey 仅返回掩码；非管理员 canEdit=false，apiKeyMasked=null） |
| PUT | /settings/ai-config | globalAdmin / superAdmin | 部分更新 AI 配置并持久化；写审计日志；返回最新配置 |
| POST | /settings/ai-config/test | globalAdmin / superAdmin | 连通性测试：测试本地规则引擎与 LLM 实际连通性，不修改已保存配置（可用表单草稿测试） |

响应 `AIConfigResponse`：
```typescript
interface AIConfigResponse {
  llmBaseUrl: string; llmChatPath: string; llmModel: string;
  llmTimeoutSeconds: number; llmMaxCandidates: number;
  dispatchMode: 'LOCAL_ONLY'|'LLM_ONLY'|'LOCAL_FIRST'|'LLM_FIRST';
  matchThreshold: number; workloadPenalty: number;
  hasApiKey: boolean; apiKeyMasked: string | null;   // 例如 "****abcd"；仅管理员可见
  canEdit: boolean; configSource: 'database' | 'environment';
  updatedAt: string | null; updatedByName: string | null;
}
```

请求 `UpdateAIConfigRequest`（PUT，字段均可选；至少提供一项）：
```typescript
{
  llmBaseUrl?: string;      // http(s):// 开头，自动去尾部 /
  llmChatPath?: string;     // 以 / 开头，默认 /v1/chat/completions
  llmModel?: string;        // ≤100 字
  llmApiKey?: string;       // 空字符串=保持原值不变；配合 clearApiKey=true 清空
  clearApiKey?: boolean;
  llmTimeoutSeconds?: number;  // 1-120
  llmMaxCandidates?: number;   // 1-100
  dispatchMode?: 'LOCAL_ONLY'|'LLM_ONLY'|'LOCAL_FIRST'|'LLM_FIRST';
  matchThreshold?: number;     // 0-100
  workloadPenalty?: number;    // 0-100
}
```

连通性测试 `AIConfigTestRequest`：字段同 PUT（用于草稿测试；llmApiKey 空=使用已保存 Key）。
响应 `AIConfigTestResponse`：
```typescript
{
  testedAt: string;
  local: { available: boolean; message: string };   // 本地规则引擎始终可用
  llm: { configured: boolean; success: boolean; message: string;
         latencyMs: number | null; responsePreview: string | null };
}
```
LLM 测试实现：使用「有效配置 + 请求草稿覆盖」向 `{baseUrl}{chatPath}` 发送最小 Chat Completions 请求
（messages=用户 ping，max_tokens 较小），HTTP 2xx 且返回 choices.message.content 非空为成功；
未配置三项时返回 configured=false、success=false、中文原因；失败返回 HTTP 状态/网络错误中文信息；不泄露 API Key。

### 9.3 与现有 AI 服务集成
- `services/aiConfigService.py`：配置读取/合并/保存/掩码/连通性测试 + 审计日志；
- `aiAssignmentService`、`localRecommendationEngine`、`llmRecommendationClient`、`aiService` 全部改为读取**有效配置**（不再直接读 settings 的 ai 字段）；
- `GET /ai/status` 的 dispatchMode/llmConfigured/llmModel/matchThreshold/workloadPenalty 必须来自有效配置；
- 保存配置后无需重启，下一次推荐/自动分配立即使用新配置。

### 9.4 前端（系统设置页）
- `SettingsPage` 新增「AI 配置」卡片（位于外观/安全之后、系统信息之前）；
- 所有登录用户可查看当前状态（调度模式、LLM 是否配置、模型、阈值）；非管理员只读并提示「仅全局管理员可修改」；
- 管理员可编辑：调度模式、LLM Base URL/对话路径/模型/API Key（密码框，留空=保持不变，提供清除按钮）、超时、候选上限、匹配阈值、负载惩罚；
- 操作：保存配置、测试连通性（使用当前表单值草稿测试，不要求先保存）；展示本地引擎/LLM 测试结果、延迟与错误中文提示；
- 保存成功 toast 提示并刷新 AI 状态；API Key 显示为掩码。
