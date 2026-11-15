"""全部业务枚举定义。

枚举值使用前端友好的 camelCase 字符串，数据库 ENUM 列存储同样的字符串值，
避免前后端来回转换。所有枚举继承 str，便于 JSON 序列化与比较。
"""

from enum import Enum


class GlobalRole(str, Enum):
    """全局角色：超级用户 > 全局管理员 > 普通用户。"""

    SUPER_ADMIN = "superAdmin"
    GLOBAL_ADMIN = "globalAdmin"
    USER = "user"


class TeamRole(str, Enum):
    """团队角色：团队管理员 > 子管理员 > 普通成员。"""

    ADMIN = "admin"
    SUB_ADMIN = "subAdmin"
    MEMBER = "member"


class JoinMethod(str, Enum):
    """团队加入方式。"""

    FREE = "free"
    APPROVAL = "approval"
    INVITE_ONLY = "inviteOnly"


class TeamStatus(str, Enum):
    """团队认证状态：待审核 / 已认证 / 已驳回。"""

    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"


class JoinRequestStatus(str, Enum):
    """入团申请状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaskPriority(str, Enum):
    """任务优先级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """任务聚合状态。"""

    PUBLISHED = "published"
    IN_PROGRESS = "inProgress"
    PENDING_REVIEW = "pendingReview"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


class AssignmentMode(str, Enum):
    """任务分配方式：指定成员 / 指定级别范围。"""

    SPECIFIC = "specific"
    LEVEL_RANGE = "levelRange"


class AcceptanceMode(str, Enum):
    """任务接受方式：必须接受 / 选择性接受。"""

    MANDATORY = "mandatory"
    OPTIONAL = "optional"


class AssignmentStatus(str, Enum):
    """个人待办状态。"""

    PENDING_ACCEPTANCE = "pendingAcceptance"
    IN_PROGRESS = "inProgress"
    PENDING_REVIEW = "pendingReview"
    ARCHIVED = "archived"


class ReviewResult(str, Enum):
    """审核结果。"""

    APPROVED = "approved"
    REJECTED = "rejected"


class CollaborationStatus(str, Enum):
    """团队/子团队协作关系状态。"""

    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    ENDED = "ended"


class ThemeMode(str, Enum):
    """界面主题。"""

    LIGHT = "light"
    DARK = "dark"


class FontSize(str, Enum):
    """界面字号档位。"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class FontFamily(str, Enum):
    """界面字体族档位。"""

    SYSTEM = "system"
    SERIF = "serif"
    SANS = "sans"
    MONOSPACE = "monospace"


# 优先级排序权重：数值越大越紧急，用于排序与推荐打分
PRIORITY_WEIGHT = {
    TaskPriority.LOW: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.HIGH: 3,
    TaskPriority.URGENT: 4,
}

# 任务状态中文名称，供文档与提示复用
TASK_STATUS_LABELS = {
    TaskStatus.PUBLISHED: "Published",
    TaskStatus.IN_PROGRESS: "In Progress",
    TaskStatus.PENDING_REVIEW: "Pending Review",
    TaskStatus.ARCHIVED: "Archived",
    TaskStatus.CANCELLED: "Cancelled",
}


class CollaborationPhase(str, Enum):
    """协作任务阶段（字符串落库在 tasks.collaboration_phase）。"""

    PENDING_CONFIRMATION = "pendingConfirmation"
    EXECUTING = "executing"
    TARGET_REVIEW = "targetReview"
    SOURCE_REVIEW = "sourceReview"
    REJECTED = "rejected"


class ReviewStage(str, Enum):
    """双审核阶段（字符串落库在 task_assignments.review_stage）。"""

    TARGET = "target"
    SOURCE = "source"


class AssignmentSource(str, Enum):
    """任务分配来源。"""

    MANUAL = "manual"
    AI = "ai"
    COLLABORATION = "collaboration"


class NotificationType(str, Enum):
    """站内通知类型标识，前端据此展示图标/分组。"""

    COLLABORATION_APPLIED = "collaborationApplied"
    COLLABORATION_CONFIRMED = "collaborationConfirmed"
    COLLABORATION_REJECTED = "collaborationRejected"
    COLLABORATION_ENDED = "collaborationEnded"
    COLLABORATION_TASK_RECEIVED = "collaborationTaskReceived"
    COLLABORATION_TASK_CONFIRMED = "collaborationTaskConfirmed"
    COLLABORATION_TASK_REJECTED = "collaborationTaskRejected"
    COLLABORATION_TASK_TARGET_REVIEW = "collaborationTaskTargetReview"
    COLLABORATION_TASK_SOURCE_REVIEW = "collaborationTaskSourceReview"
    COLLABORATION_TASK_ARCHIVED = "collaborationTaskArchived"
    TASK_AUTO_ASSIGNED = "taskAutoAssigned"
    TASK_MATCH_REMINDER = "taskMatchReminder"
    TASK_ASSIGN_FAILED = "taskAssignFailed"
    TASK_ASSIGNED = "taskAssigned"
    TASK_REVIEW_RESULT = "taskReviewResult"

