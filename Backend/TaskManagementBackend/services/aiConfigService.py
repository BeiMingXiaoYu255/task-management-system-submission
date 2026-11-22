"""AI 配置业务服务（v1.1.1）：有效配置解析、保存、掩码与连通性测试编排。

有效配置优先级（aiModuleContract.md 第 9 节）：数据库 system_settings 覆盖值 >
环境变量/默认 Settings > 内置默认值。数据库中不存在的键回退环境变量；保存过的键
（包括空字符串，例如清空 API Key）以数据库为准。不做缓存，每次调用直接读库，
因此保存后下一次推荐/自动分配立即生效。API Key 只返回掩码，审计明细不含明文。
LLM 连通性测试的 HTTP 细节委托给 llmRecommendationClient.testLlmConnectivity，
本服务负责合并草稿配置、组装响应与审计。
"""

from dataclasses import asdict, dataclass, replace
from datetime import datetime

from sqlalchemy.orm import Session

from TaskManagementBackend.config.settings import settings
from TaskManagementBackend.core.exceptions import validationError
from TaskManagementBackend.models import SystemSetting, User
from TaskManagementBackend.models.enums import GlobalRole
from TaskManagementBackend.repositories.systemSettingRepository import SystemSettingRepository
from TaskManagementBackend.schemas.aiConfigSchema import TestAIConfigRequest, UpdateAIConfigRequest
from TaskManagementBackend.services.auditService import AuditService
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.llmRecommendationClient import testLlmConnectivity
from TaskManagementBackend.utils.timeUtils import getCurrentTime

# 调度模式合法取值（aiModuleContract.md 第 5 节）
VALID_DISPATCH_MODES = ("LOCAL_ONLY", "LLM_ONLY", "LOCAL_FIRST", "LLM_FIRST")
DEFAULT_DISPATCH_MODE = "LOCAL_FIRST"
DEFAULT_CHAT_PATH = "/v1/chat/completions"
# AI 配置字段 -> system_settings 配置键（统一 ai. 前缀）
AI_CONFIG_STRING_FIELDS = {
    "llmBaseUrl": "ai.llmBaseUrl",
    "llmChatPath": "ai.llmChatPath",
    "llmModel": "ai.llmModel",
}
# 整数字段 -> (配置键, 默认值, 最小值, 最大值)
AI_CONFIG_INTEGER_FIELDS = {
    "llmTimeoutSeconds": ("ai.llmTimeoutSeconds", 20, 1, 120),
    "llmMaxCandidates": ("ai.llmMaxCandidates", 20, 1, 100),
    "matchThreshold": ("ai.matchThreshold", 50, 0, 100),
    "workloadPenalty": ("ai.workloadPenalty", 5, 0, 100),
}
AI_CONFIG_KEY_LLM_API_KEY = "ai.llmApiKey"
AI_CONFIG_KEY_DISPATCH_MODE = "ai.dispatchMode"
AI_CONFIG_KEYS = (
    *AI_CONFIG_STRING_FIELDS.values(),
    AI_CONFIG_KEY_LLM_API_KEY,
    *(definition[0] for definition in AI_CONFIG_INTEGER_FIELDS.values()),
    AI_CONFIG_KEY_DISPATCH_MODE,
)
# 审计动作标识与审计明细中去掉 Key 明文的说明
AI_CONFIG_AUDIT_ACTION = "admin.aiConfig.update"


@dataclass
class AIConfig:
    """AI 有效配置快照：数据库覆盖值与环境默认值合并后的结果。"""

    llmBaseUrl: str
    llmChatPath: str
    llmModel: str
    llmApiKey: str
    llmTimeoutSeconds: int
    llmMaxCandidates: int
    dispatchMode: str
    matchThreshold: int
    workloadPenalty: int
    configSource: str = "environment"
    updatedAt: datetime | None = None
    updatedByName: str | None = None

    @property
    def hasApiKey(self) -> bool:
        """是否已配置 API Key（空字符串视为未配置）。"""
        return bool(self.llmApiKey.strip())

    @property
    def llmConfigured(self) -> bool:
        """LLM 三项关键配置（Base URL/API Key/模型）齐全才算可用。"""
        return bool(self.llmBaseUrl.strip() and self.hasApiKey and self.llmModel.strip())


def normalizeDispatchMode(configValue: str | None) -> str:
    """调度模式规范化：大写后校验，非法或未配置时回退 LOCAL_FIRST。"""
    normalizedMode = str(configValue or "").strip().upper()
    return normalizedMode if normalizedMode in VALID_DISPATCH_MODES else DEFAULT_DISPATCH_MODE


def normalizeChatPath(chatPath: str | None) -> str:
    """对话路径规范化：空值用默认路径，缺少前缀 / 时自动补齐。"""
    strippedPath = str(chatPath or "").strip()
    if not strippedPath:
        return DEFAULT_CHAT_PATH
    return strippedPath if strippedPath.startswith("/") else "/" + strippedPath


def normalizeStringFieldValue(fieldName: str, fieldValue: object) -> str:
    """按字段类型校验并规范化字符串配置（Base URL / 对话路径 / 模型名）。"""
    strippedValue = str(fieldValue or "").strip()
    if fieldName == "llmModel":
        return strippedValue
    if fieldName == "llmChatPath":
        if strippedValue and not strippedValue.startswith("/"):
            raise validationError("Chat path must start with /")
        return strippedValue
    if strippedValue and not (
        strippedValue.startswith("http://") or strippedValue.startswith("https://")
    ):
        raise validationError("LLM base URL must start with http:// or https://")
    normalizedBaseUrl = strippedValue.rstrip("/")
    if normalizedBaseUrl in ("http:", "https:"):
        raise validationError("LLM base URL must include a host, not only the protocol prefix")
    return normalizedBaseUrl


def parseInteger(configValue: str | None, defaultValue: int, minimum: int, maximum: int) -> int:
    """把数据库/config 中的字符串安全转换为整数并收敛到合法区间。"""
    try:
        parsedValue = int(str(configValue).strip())
    except (TypeError, ValueError):
        return defaultValue
    return max(minimum, min(maximum, parsedValue))


def buildEnvironmentConfig() -> AIConfig:
    """按环境变量/默认 Settings 构造配置（数据库无覆盖值时使用）。"""
    return AIConfig(
        llmBaseUrl=str(settings.llmBaseUrl or "").strip().rstrip("/"),
        llmChatPath=normalizeChatPath(settings.llmChatPath),
        llmModel=str(settings.llmModel or "").strip(),
        llmApiKey=str(settings.llmApiKey or "").strip(),
        llmTimeoutSeconds=parseInteger(str(settings.llmTimeoutSeconds), 20, 1, 120),
        llmMaxCandidates=parseInteger(str(settings.llmMaxCandidates), 20, 1, 100),
        dispatchMode=normalizeDispatchMode(settings.assignmentDispatchMode),
        matchThreshold=parseInteger(str(settings.assignmentMatchThreshold), 50, 0, 100),
        workloadPenalty=parseInteger(str(settings.assignmentWorkloadPenalty), 5, 0, 100),
    )


def loadEffectiveAIConfig(db: Session) -> AIConfig:
    """读取有效配置：数据库值优先覆盖环境默认值，并附带最后修改信息与来源。"""
    config = buildEnvironmentConfig()
    settingRows = SystemSettingRepository(db).listByKeys(list(AI_CONFIG_KEYS))
    if not settingRows:
        return config
    config.configSource = "database"
    databaseValues = {settingRow.configKey: settingRow.configValue for settingRow in settingRows}
    if AI_CONFIG_KEY_LLM_API_KEY in databaseValues:
        config.llmApiKey = str(databaseValues[AI_CONFIG_KEY_LLM_API_KEY] or "").strip()
    for fieldName, configKey in AI_CONFIG_STRING_FIELDS.items():
        if configKey in databaseValues:
            setattr(config, fieldName, str(databaseValues[configKey] or "").strip())
    config.llmBaseUrl = config.llmBaseUrl.rstrip("/")
    config.llmChatPath = normalizeChatPath(config.llmChatPath)
    for fieldName, (configKey, defaultValue, minimum, maximum) in AI_CONFIG_INTEGER_FIELDS.items():
        if configKey in databaseValues:
            setattr(config, fieldName, parseInteger(databaseValues[configKey], defaultValue, minimum, maximum))
    if AI_CONFIG_KEY_DISPATCH_MODE in databaseValues:
        config.dispatchMode = normalizeDispatchMode(databaseValues[AI_CONFIG_KEY_DISPATCH_MODE])
    latestRow = max(settingRows, key=lambda row: (row.updatedAt or datetime.min, row.id))
    config.updatedAt = latestRow.updatedAt
    config.updatedByName = latestRow.updater.nickname if latestRow.updater is not None else None
    return config


def maskApiKey(apiKey: str | None) -> str | None:
    """生成 API Key 掩码（如 ****abcd），未配置返回 None。"""
    strippedKey = str(apiKey or "").strip()
    if not strippedKey:
        return None
    if len(strippedKey) <= 4:
        return "****"
    return "****" + strippedKey[-4:]


def buildConfigResponse(config: AIConfig, canEdit: bool) -> dict:
    """把有效配置转换为接口响应字典：Key 只返回掩码，非管理员不返回掩码。"""
    response = asdict(config)
    response.pop("llmApiKey")
    response.update(hasApiKey=config.hasApiKey, apiKeyMasked=maskApiKey(config.llmApiKey) if canEdit else None, canEdit=canEdit)
    return response


def applyDraftConfig(savedConfig: AIConfig, request: UpdateAIConfigRequest | TestAIConfigRequest) -> AIConfig:
    """把表单草稿覆盖到已保存配置上（不写库）；apiKey 留空表示沿用已保存 Key。"""
    draftConfig = replace(savedConfig)
    draftFields = request.model_dump(exclude_unset=True)
    for fieldName in AI_CONFIG_STRING_FIELDS:
        if draftFields.get(fieldName) is not None:
            setattr(draftConfig, fieldName, normalizeStringFieldValue(fieldName, draftFields[fieldName]))
    draftConfig.llmChatPath = normalizeChatPath(draftConfig.llmChatPath)
    for fieldName in AI_CONFIG_INTEGER_FIELDS:
        if draftFields.get(fieldName) is not None:
            setattr(draftConfig, fieldName, int(draftFields[fieldName]))
    if draftFields.get("dispatchMode") is not None:
        draftConfig.dispatchMode = normalizeDispatchMode(draftFields["dispatchMode"])
    if draftFields.get("clearApiKey"):
        draftConfig.llmApiKey = ""
    elif str(draftFields.get("llmApiKey") or "").strip():
        draftConfig.llmApiKey = str(draftFields["llmApiKey"]).strip()
    return draftConfig


class AIConfigService(BaseService):
    """AI 配置业务服务：读取/保存有效配置、生成审计日志与连通性测试。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化系统配置仓储与审计服务。"""
        super().__init__(db)
        self.systemSettingRepository = SystemSettingRepository(db)
        self.auditService = AuditService(db)

    def getConfig(self, currentUser: User) -> dict:
        """读取有效 AI 配置（普通用户只能看状态，管理员额外返回 Key 掩码）。"""
        return buildConfigResponse(loadEffectiveAIConfig(self.db), self.canEdit(currentUser))

    def updateConfig(
        self, currentUser: User, request: UpdateAIConfigRequest, clientIp: str | None = None
    ) -> dict:
        """保存 AI 配置：部分更新 system_settings，写审计日志后返回最新有效配置。"""
        if not request.model_dump(exclude_unset=True):
            raise validationError("At least one AI configuration field is required")
        changedFields = self.applyUpdates(currentUser.id, request)
        effectiveConfig = loadEffectiveAIConfig(self.db)
        if changedFields:
            auditDetail = self.buildAuditDetail(changedFields, effectiveConfig)
            self.auditService.recordAuditLog(currentUser.id, AI_CONFIG_AUDIT_ACTION, auditDetail, clientIp)
        self.commit()
        return buildConfigResponse(loadEffectiveAIConfig(self.db), self.canEdit(currentUser))

    def applyUpdates(self, updatedByUserId: int, request: UpdateAIConfigRequest) -> list[str]:
        """把请求中显式提供的字段写入 system_settings，返回实际变更的字段名列表。"""
        requestedValues = request.model_dump(exclude_unset=True)
        changedFields: list[str] = []
        for fieldName, configKey in AI_CONFIG_STRING_FIELDS.items():
            if requestedValues.get(fieldName) is not None:
                normalizedValue = normalizeStringFieldValue(fieldName, requestedValues[fieldName])
                self.saveConfigValue(configKey, normalizedValue, updatedByUserId)
                changedFields.append(fieldName)
        for fieldName, (configKey, _defaultValue, _minimum, _maximum) in AI_CONFIG_INTEGER_FIELDS.items():
            if requestedValues.get(fieldName) is not None:
                self.saveConfigValue(configKey, str(int(requestedValues[fieldName])), updatedByUserId)
                changedFields.append(fieldName)
        if requestedValues.get("dispatchMode") is not None:
            dispatchMode = normalizeDispatchMode(requestedValues["dispatchMode"])
            self.saveConfigValue(AI_CONFIG_KEY_DISPATCH_MODE, dispatchMode, updatedByUserId)
            changedFields.append("dispatchMode")
        if requestedValues.get("clearApiKey"):
            self.saveConfigValue(AI_CONFIG_KEY_LLM_API_KEY, "", updatedByUserId)
            changedFields.append("llmApiKey")
        elif str(requestedValues.get("llmApiKey") or "").strip():
            apiKeyValue = str(requestedValues["llmApiKey"]).strip()
            self.saveConfigValue(AI_CONFIG_KEY_LLM_API_KEY, apiKeyValue, updatedByUserId)
            changedFields.append("llmApiKey")
        return changedFields

    def saveConfigValue(self, configKey: str, configValue: str, updatedByUserId: int) -> None:
        """写入或更新一条系统配置并记录最后修改人（事务由调用方提交）。"""
        settingRow = self.systemSettingRepository.getByKey(configKey)
        if settingRow is None:
            newSetting = SystemSetting(configKey=configKey, configValue=configValue, updatedBy=updatedByUserId)
            self.systemSettingRepository.add(newSetting)
            return
        settingRow.configValue = configValue
        settingRow.updatedBy = updatedByUserId
        self.db.flush()

    def buildAuditDetail(self, changedFields: list[str], config: AIConfig) -> dict:
        """构造审计明细：只记录变更字段与配置摘要，绝不包含 API Key 明文。"""
        return {
            "changedFields": sorted(set(changedFields)),
            "dispatchMode": config.dispatchMode,
            "llmBaseUrl": config.llmBaseUrl,
            "llmChatPath": config.llmChatPath,
            "llmModel": config.llmModel,
            "llmTimeoutSeconds": config.llmTimeoutSeconds,
            "llmMaxCandidates": config.llmMaxCandidates,
            "matchThreshold": config.matchThreshold,
            "workloadPenalty": config.workloadPenalty,
            "hasApiKey": config.hasApiKey,
        }

    def testConnectivity(self, request: TestAIConfigRequest) -> dict:
        """连通性测试：本地引擎始终可用；LLM 用「已保存配置 + 请求草稿」实际调用一次。"""
        draftConfig = applyDraftConfig(loadEffectiveAIConfig(self.db), request)
        return {
            "testedAt": getCurrentTime(),
            "local": {"available": True, "message": "Local rule engine is available (no external service required; recommendations and auto-assignment always work)"},
            "llm": testLlmConnectivity(draftConfig),
        }

    @staticmethod
    def canEdit(currentUser: User) -> bool:
        """判断当前用户是否有权修改 AI 配置（仅全局管理员与超级用户）。"""
        return currentUser.globalRole in (GlobalRole.GLOBAL_ADMIN, GlobalRole.SUPER_ADMIN)