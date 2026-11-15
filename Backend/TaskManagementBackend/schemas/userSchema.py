"""用户资料与技能标签接口数据模型。"""

from datetime import datetime

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import GlobalRole


class SkillItemResponse(BaseModel):
    """技能标签及熟练度（用户资料 skills 元素）。"""

    id: int
    name: str
    category: str | None = None
    proficiency: int


class SkillTagItemResponse(BaseModel):
    """技能标签字典项（技能选择器使用，不含熟练度）。"""

    id: int
    name: str
    category: str | None = None


class UserDetailResponse(BaseModel):
    """用户完整资料响应（隐私字段是否可见由服务层控制）。"""

    id: int
    username: str
    nickname: str
    avatar: str | None = None
    globalRole: GlobalRole
    email: str | None = None
    phone: str | None = None
    bio: str | None = None
    createdAt: datetime
    skills: list[SkillItemResponse]


class UpdateProfileRequest(BaseModel):
    """修改个人资料请求体；仅提交需要修改的字段。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    bio: str | None = Field(default=None, max_length=2000)


class SkillEntryRequest(BaseModel):
    """单个技能保存项：标签主键 + 熟练度 1-5。"""

    skillTagId: int = Field(gt=0)
    proficiency: int = Field(default=3, ge=1, le=5)


class SaveSkillsRequest(BaseModel):
    """覆盖式保存技能请求体。"""

    skills: list[SkillEntryRequest] = Field(default_factory=list)


class CreateSkillTagRequest(BaseModel):
    """新建技能标签请求体。"""

    name: str = Field(min_length=1, max_length=50)
    category: str | None = Field(default=None, max_length=50)
