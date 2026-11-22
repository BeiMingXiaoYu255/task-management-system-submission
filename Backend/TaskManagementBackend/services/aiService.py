"""AI 辅助业务服务（v1.1.1）：模块状态与推荐接口编排。

算法实现全部下沉到 aiAssignmentService / localRecommendationEngine /
llmRecommendationClient；配置一律通过 aiConfigService.loadEffectiveAIConfig 读取
（数据库 system_settings 优先、环境变量兜底），本服务只做编排与状态组装。
AI 配置的读写与连通性测试见 aiConfigService / aiConfigController。
"""

from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.aiSchema import RecommendAssigneesRequest
from TaskManagementBackend.services.aiAssignmentService import getDispatchMode, recommendCandidates
from TaskManagementBackend.services.aiConfigService import AIConfig, loadEffectiveAIConfig
from TaskManagementBackend.services.baseService import BaseService

# AI 模块 provider 标识：本地规则引擎 + LLM 混合；本地规则引擎始终可用
AI_PROVIDER_NAME = "hybrid"
LOCAL_AVAILABLE = True


def buildStatusDescription(config: AIConfig) -> str:
    """生成 AI 模块状态说明：本地引擎始终可用，LLM 未配置时提示所需配置项。"""
    if config.llmConfigured:
        return (
            f"Local rule engine is available; LLM is configured (model {config.llmModel or 'not set'}), "
            f"current dispatch mode {getDispatchMode(config)}."
        )
    return (
        "Local rule engine is available; LLM is not configured. Set the LLM base URL, API key "
        "and model in Settings to enable the LLM route (LLM_* dispatch modes fall back to the local engine)."
    )


class AIService(BaseService):
    """AI 辅助业务服务：模块状态与任务执行人推荐。"""

    def getStatus(self) -> dict:
        """返回 AI 模块状态：provider、调度模式、本地/LLM 可用性与打分参数（来自有效配置）。"""
        config = loadEffectiveAIConfig(self.db)
        return {
            "provider": AI_PROVIDER_NAME,
            "available": True,
            "dispatchMode": getDispatchMode(config),
            "localAvailable": LOCAL_AVAILABLE,
            "llmConfigured": config.llmConfigured,
            "llmModel": config.llmModel if config.llmConfigured else "",
            "matchThreshold": config.matchThreshold,
            "workloadPenalty": config.workloadPenalty,
            "description": buildStatusDescription(config),
        }

    def recommendAssignees(
        self, currentUser: User, teamId: int, request: RecommendAssigneesRequest
    ) -> dict:
        """按任务内容、级别范围与所需技能推荐执行人，返回 { route, reason, candidates }。"""
        return recommendCandidates(
            self.db,
            currentUser,
            teamId,
            request.title,
            request.description,
            request.priority,
            request.targetLevelMin,
            request.targetLevelMax,
            request.requiredSkillNames,
            request.maxCandidates,
        )
