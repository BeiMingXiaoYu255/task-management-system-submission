"""序列化辅助函数：把 ORM 对象转换为契约中的嵌套结构。

由多个业务服务共用，避免每个模块重复拼装用户/技能/团队身份数据。
"""

from TaskManagementBackend.models import Team, TeamMember, User, UserSkill


def buildUserBrief(user: User | None) -> dict:
    """把用户对象转换为 UserBrief 字典；用户注销时返回占位信息。"""
    if user is None:
        return {
            "id": 0,
            "username": "deleted",
            "nickname": "Deleted User",
            "avatar": None,
            "globalRole": "user",
        }
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "globalRole": user.globalRole.value if hasattr(user.globalRole, "value") else user.globalRole,
    }


def buildSkillItems(userSkills: list[UserSkill]) -> list[dict]:
    """把用户技能关联列表转换为 SkillItem 字典列表。"""
    skillItems: list[dict] = []
    for userSkill in userSkills:
        skillTag = userSkill.skillTag
        if skillTag is None:
            continue
        skillItems.append(
            {
                "id": skillTag.id,
                "name": skillTag.name,
                "category": skillTag.category,
                "proficiency": userSkill.proficiency,
            }
        )
    return skillItems


def buildUserDetail(user: User) -> dict:
    """构建用户完整资料字典（本人/管理员视角）。"""
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "globalRole": user.globalRole.value,
        "email": user.email,
        "phone": user.phone,
        "bio": user.bio,
        "createdAt": user.createdAt,
        "skills": buildSkillItems(user.skills),
    }


def buildTeamMembership(team: Team, membership: TeamMember) -> dict:
    """构建当前用户的团队身份信息字典。"""
    level = membership.level
    return {
        "teamId": team.id,
        "teamName": team.name,
        "teamStatus": team.status.value,
        "role": membership.role.value,
        "levelId": membership.levelId,
        "levelName": level.name if level is not None else "Unknown Level",
        "levelOrder": level.levelOrder if level is not None else 0,
        "canCreateTask": bool(level.canCreateTask) if level is not None else False,
        "joinedAt": membership.joinedAt,
    }


def buildTeamBrief(team: Team, memberCount: int) -> dict:
    """构建团队列表项字典。"""
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "status": team.status.value,
        "joinMethod": team.joinMethod.value,
        "createdBy": team.createdBy,
        "memberCount": memberCount,
        "createdAt": team.createdAt,
    }
