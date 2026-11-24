"""通用 Pydantic 数据模型：分页、消息、用户简要信息、技能标签。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from TaskManagementBackend.models.enums import GlobalRole

# 分页数据项泛型参数
PageItemType = TypeVar("PageItemType")


class PageResult(BaseModel, Generic[PageItemType]):
    """统一分页响应结构。"""

    items: list[PageItemType]
    total: int
    page: int
    pageSize: int


class MessageResponse(BaseModel):
    """简单消息响应。"""

    message: str


class UserBrief(BaseModel):
    """用户简要信息：接口中嵌套用户信息时统一使用。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar: str | None = None
    globalRole: GlobalRole


class SkillItem(BaseModel):
    """技能标签及熟练度。"""

    id: int
    name: str
    category: str | None = None
    proficiency: int
