"""系统设置模块 Pydantic 数据模型：界面设置、修改密码与注销账号请求。"""

from pydantic import BaseModel, Field

from TaskManagementBackend.models.enums import FontFamily, FontSize, ThemeMode


class UserSettingsResponse(BaseModel):
    """用户界面设置响应结构。"""

    theme: ThemeMode
    fontSize: FontSize
    fontFamily: FontFamily


class UpdateSettingsRequest(BaseModel):
    """修改界面设置请求体：三项均为必填，与前端 UpdateSettingsPayload 一致。"""

    theme: ThemeMode
    fontSize: FontSize
    fontFamily: FontFamily


class ChangePasswordRequest(BaseModel):
    """修改密码请求体：需提供旧密码验证身份。"""

    oldPassword: str = Field(min_length=1, max_length=64)
    newPassword: str = Field(min_length=6, max_length=64)


class DeleteAccountRequest(BaseModel):
    """注销账号请求体：需密码二次确认。"""

    password: str = Field(min_length=1, max_length=64)
