package cn.edu.cjlu.taskmanagement.service;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.dto.UserQuery;
import cn.edu.cjlu.taskmanagement.dto.UserRegisterRequest;
import cn.edu.cjlu.taskmanagement.vo.UserVO;

import java.util.List;

/**
 * 用户业务接口。
 */
public interface UserService {

    /** 注册：校验用户名唯一，BCrypt 加密密码，保存技能标签 */
    UserVO register(UserRegisterRequest request);

    /** 登录：校验用户名与密码，成功返回用户信息 */
    UserVO login(String username, String password);

    /** 分页查询用户列表（带技能标签） */
    PageResult<UserVO> page(UserQuery query);

    /** 查询用户详情（带技能标签），不存在抛 404 */
    UserVO getById(Long id);

    /** 全量覆盖某用户的技能标签 */
    void updateSkills(Long userId, List<String> skills);
}
