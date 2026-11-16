"""测试辅助函数集合：测试文件可直接 from tests.helpers import ... 使用。"""


def buildAuthHeaders(token: str) -> dict:
    """构造 Bearer 认证请求头。"""
    return {"Authorization": "Bearer " + token}
