"""系统设置业务服务：界面设置读写、修改密码与注销账号。

注销账号严格按 databaseContract.md 第 3 节第 9 条实现：
软删除用户、username 加后缀释放、清理团队成员关系与入团申请、删除待办、
发布任务 createdBy 置空（改由团队管理员审核）、管理员须先转让团队或团队无成员时解散。
"""

from sqlalchemy.orm import Session

from TaskManagementBackend.core.exceptions import conflict, validationError
from TaskManagementBackend.core.security import verifyPassword
from TaskManagementBackend.models import User
from TaskManagementBackend.models.enums import TeamRole
from TaskManagementBackend.repositories.settingRepository import SettingRepository
from TaskManagementBackend.repositories.taskRepository import TaskRepository
from TaskManagementBackend.schemas.settingSchema import UpdateSettingsRequest
from TaskManagementBackend.services.baseService import BaseService
from TaskManagementBackend.services.taskService import recomputeTaskStatus

# 注销账号后用户名后缀模板：保留原用户名并追加唯一后缀，释放原登录名
USERNAME_RELEASED_SUFFIX_TEMPLATE = "_deleted_{userId}"
# users.username 列最大长度
USERNAME_MAX_LENGTH = 50


class SettingService(BaseService):
    """系统设置业务服务：界面设置、密码与账号生命周期。"""

    def __init__(self, db: Session) -> None:
        """注入数据库会话并初始化设置、任务仓储。"""
        super().__init__(db)
        self.settingRepository = SettingRepository(db)
        self.taskRepository = TaskRepository(db)

    def _getOrCreateSetting(self, userId: int):
        """读取用户界面设置，不存在时自动创建默认记录。"""
        setting = self.settingRepository.getByUserId(userId)
        if setting is None:
            setting = self.settingRepository.createDefault(userId)
            self.commit()
        return setting

    def getSettings(self, currentUser: User) -> dict:
        """读取界面设置：不存在时返回默认值并自动创建。"""
        setting = self._getOrCreateSetting(currentUser.id)
        return {
            "theme": setting.theme,
            "fontSize": setting.fontSize,
            "fontFamily": setting.fontFamily,
        }

    def updateSettings(self, currentUser: User, request: UpdateSettingsRequest) -> dict:
        """覆盖式保存界面设置：主题、字号、字体族三项均必填。"""
        setting = self._getOrCreateSetting(currentUser.id)
        setting.theme = request.theme
        setting.fontSize = request.fontSize
        setting.fontFamily = request.fontFamily
        self.commit()
        return {
            "theme": setting.theme,
            "fontSize": setting.fontSize,
            "fontFamily": setting.fontFamily,
        }

    def _collectTeamsToDelete(self, currentUser: User) -> list:
        """校验团队管理员身份并返回需要跟着解散的团队（已无其他成员）。"""
        teamsToDelete = []
        for membership in self.settingRepository.listMemberships(currentUser.id):
            if membership.role != TeamRole.ADMIN:
                continue
            if self.settingRepository.countTeamMembers(membership.teamId) > 1:
                raise conflict("You are still a team admin. Transfer the admin role before deleting your account.")
            teamsToDelete.append(membership.team)
        return teamsToDelete

    def deleteAccount(self, currentUser: User, password: str) -> dict:
        """注销账号：密码二次确认后软删除用户并清理全部关联数据。"""
        if not verifyPassword(password, currentUser.passwordHash):
            raise validationError("Incorrect password. The account cannot be deleted.")
        teamsToDelete = self._collectTeamsToDelete(currentUser)
        for team in teamsToDelete:
            self.settingRepository.deleteTeam(team)
        affectedTaskIds = self.settingRepository.listAssignedTaskIds(currentUser.id)
        self.settingRepository.deleteAssignmentsByUser(currentUser.id)
        self.settingRepository.clearTaskCreator(currentUser.id)
        self.settingRepository.deleteJoinRequestsByUser(currentUser.id)
        self.settingRepository.deleteMembershipsByUser(currentUser.id)
        for taskId in affectedTaskIds:
            task = self.taskRepository.getTaskWithRelations(taskId)
            if task is not None:
                recomputeTaskStatus(task, self.taskRepository)
        suffix = USERNAME_RELEASED_SUFFIX_TEMPLATE.format(userId=currentUser.id)
        currentUser.username = f"{currentUser.username[:USERNAME_MAX_LENGTH - len(suffix)]}{suffix}"
        currentUser.isActive = False
        self.commit()
        return {"message": "Account deleted. Thank you for using the system."}