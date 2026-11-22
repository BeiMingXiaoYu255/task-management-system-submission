"""AI 配置模块 Pydantic 数据模型（v1.1.1，见 aiModuleContract.md 第 9 节）。

请求/响应字段与前端 Frontend/src/types/aiConfig.ts 一一对应，统一使用 camelCase。
字段只做长度/数值范围等结构校验；URL、对话路径等业务校验集中在 aiConfigService，
错误统一抛 AppException，保证全局异常处理器输出统一 JSON。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 调度模式枚举（与 aiModuleContract.md 第 5 节一致）
AssignmentDispatchMode = Literal["LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST"]
# 配置来源：database 表示存在数据库覆盖值，environment 表示全部来自环境变量/默认值
AIConfigSource = Literal["database", "environment"]


class AIConfigFieldsBase(BaseModel):
    """AI 配置可编辑字段基类：PUT 与连通性测试草稿共用同一套字段。"""

    llmBaseUrl: str | None = Field(default=None, max_length=500, description="OpenAI-compatible service base URL")
    llmChatPath: str | None = Field(default=None, max_length=200, description="Chat completions endpoint path")
    llmModel: str | None = Field(default=None, max_length=100, description="Model name")
    llmApiKey: str | None = Field(
        default=None, max_length=500, description="API key (empty string keeps the saved value)"
    )
    clearApiKey: bool = Field(default=False, description="Whether to clear the saved API key")
    llmTimeoutSeconds: int | None = Field(default=None, ge=1, le=120, description="LLM read timeout in seconds")
    llmMaxCandidates: int | None = Field(default=None, ge=1, le=100, description="Maximum number of candidates")
    dispatchMode: AssignmentDispatchMode | None = Field(default=None, description="Dispatch mode")
    matchThreshold: int | None = Field(default=None, ge=0, le=100, description="Minimum local match score")
    workloadPenalty: int | None = Field(
        default=None, ge=0, le=100, description="Workload penalty per active to-do"
    )


class UpdateAIConfigRequest(AIConfigFieldsBase):
    """保存 AI 配置请求体（字段均可选，但至少提供一个，由服务层校验）。"""


class TestAIConfigRequest(AIConfigFieldsBase):
    """连通性测试请求体：字段同保存请求，全部可选（可用表单草稿覆盖，不写库）。"""


class AIConfigResponse(BaseModel):
    """AI 有效配置响应：apiKey 仅返回掩码，非管理员 apiKeyMasked 为 null。"""

    llmBaseUrl: str
    llmChatPath: str
    llmModel: str
    llmTimeoutSeconds: int
    llmMaxCandidates: int
    dispatchMode: AssignmentDispatchMode
    matchThreshold: int
    workloadPenalty: int
    hasApiKey: bool
    apiKeyMasked: str | None = None
    canEdit: bool
    configSource: AIConfigSource
    updatedAt: datetime | None = None
    updatedByName: str | None = None


class AIConfigLocalTestResult(BaseModel):
    """本地规则引擎连通性测试结果（始终可用）。"""

    available: bool
    message: str


class AIConfigLlmTestResult(BaseModel):
    """LLM 连通性测试结果：不含 API Key，仅给出中文结论与预览。"""

    configured: bool
    success: bool
    message: str
    latencyMs: int | None = None
    responsePreview: str | None = None


class AIConfigTestResponse(BaseModel):
    """AI 连通性测试响应：本地引擎与 LLM 两部分结果。"""

    testedAt: datetime
    local: AIConfigLocalTestResult
    llm: AIConfigLlmTestResult
