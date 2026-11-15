"""用户资料与技能标签接口控制器。

控制器只做参数接收与响应组装，权限校验与业务逻辑在 UserService / permissions 中。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from TaskManagementBackend.core.database import getDb
from TaskManagementBackend.core.dependencies import getCurrentUser
from TaskManagementBackend.models import User
from TaskManagementBackend.schemas.userSchema import (
    CreateSkillTagRequest,
    SaveSkillsRequest,
    SkillItemResponse,
    SkillTagItemResponse,
    UpdateProfileRequest,
    UserDetailResponse,
)
from TaskManagementBackend.services.userService import UserService

# 路由前缀由主应用统一追加 /api/v1
router = APIRouter(tags=["User Profile"])


@router.get("/users/me", response_model=UserDetailResponse, summary="Get my profile")
def getMyProfile(
    currentUser: User = Depends(getCurrentUser), db: Session = Depends(getDb)
) -> dict:
    """返回当前登录用户的完整资料。"""
    return UserService(db).getMyProfile(currentUser)


@router.put("/users/me", response_model=UserDetailResponse, summary="Update my profile")
def updateMyProfile(
    payload: UpdateProfileRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """修改昵称、邮箱、手机号与个人简介，仅更新显式提交的字段。"""
    return UserService(db).updateMyProfile(currentUser, payload)


@router.put("/users/me/skills", response_model=UserDetailResponse, summary="Save my skills (overwrite)")
def saveMySkills(
    payload: SaveSkillsRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """覆盖式保存本人技能标签及熟练度。"""
    return UserService(db).saveMySkills(currentUser, payload)


@router.post(
    "/users/me/skills/tags", response_model=SkillItemResponse, summary="Create skill tag"
)
def createSkillTag(
    payload: CreateSkillTagRequest,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """新建技能标签；同名标签已存在时直接返回已有标签。"""
    return UserService(db).createSkillTag(payload)


@router.get("/skill-tags", response_model=list[SkillTagItemResponse], summary="List skill tags")
def listSkillTags(
    keyword: str | None = Query(default=None, description="Name keyword"),
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> list[dict]:
    """返回全部技能标签字典，可按名称关键字过滤。"""
    return UserService(db).listSkillTags(keyword)


@router.get(
    "/users/{userId}/profile", response_model=UserDetailResponse, summary="View user profile"
)
def getUserProfile(
    userId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """查看他人资料：本人/全局管理员/同团队管理者或更高级别成员可查看。"""
    return UserService(db).getUserProfile(currentUser, userId)


@router.get(
    "/users/{userId}/public-profile",
    response_model=UserDetailResponse,
    summary="View team member public profile",
)
def getUserPublicProfile(
    userId: int,
    currentUser: User = Depends(getCurrentUser),
    db: Session = Depends(getDb),
) -> dict:
    """查看同团队成员的公开资料（邮箱与手机号始终隐藏）。"""
    return UserService(db).getUserPublicProfile(currentUser, userId)
