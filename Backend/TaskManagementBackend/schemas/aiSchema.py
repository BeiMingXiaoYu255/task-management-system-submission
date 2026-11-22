"""AI 辅助模块 Pydantic 数据模型（v1.1 AI 自动分配契约）。

请求/响应字段与 docs/development/aiModuleContract.md 第 6 节、前端
Frontend/src/types/ai.ts 一一对应，统一使用 camelCase 命名。
"""

from typing import Literal

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import TaskPriority

# 调度模式枚举（与 settings.assignmentDispatchMode 取值一致）
AssignmentDispatchMode = Literal["LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST"]


class RecommendAssigneesRequest(BaseModel):
    """任务执行人推荐请求体。"""

    title: str = Field(min_length=2, max_length=200, description="Task title")
    description: str | None = Field(default=None, max_length=5000, description="Task description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    targetLevelMin: int | None = Field(default=None, description="Minimum candidate level order")
    targetLevelMax: int | None = Field(default=None, description="Maximum candidate level order")
    requiredSkillNames: list[str] | None = Field(
        default=None,
        max_length=50,
        description="Required skill tags for AI assignment; inferred from title/description when empty",
    )
    maxCandidates: int | None = Field(
        default=None, ge=1, le=50, description="Maximum number of candidates to return (default 10)"
    )


class RecommendCandidateResponse(BaseModel):
    """单个候选执行人：得分、匹配率、匹配技能、活跃待办与中文推荐理由。"""

    userId: int
    username: str
    nickname: str
    levelName: str
    levelOrder: int
    score: int
    matchRatio: float
    matchedSkills: list[str]
    activeTasks: int
    reasons: list[str]
    route: str


class RecommendResponse(BaseModel):
    """推荐接口响应：产生结果的链路、中文原因与候选人列表（按得分降序）。"""

    route: str | None = None
    reason: str
    candidates: list[RecommendCandidateResponse] = Field(default_factory=list)


class AiStatusResponse(BaseModel):
    """AI 模块状态响应：调度模式、本地引擎与 LLM 配置状态。"""

    provider: str
    available: bool
    dispatchMode: AssignmentDispatchMode
    localAvailable: bool
    llmConfigured: bool
    llmModel: str
    matchThreshold: int
    workloadPenalty: int
    description: str
