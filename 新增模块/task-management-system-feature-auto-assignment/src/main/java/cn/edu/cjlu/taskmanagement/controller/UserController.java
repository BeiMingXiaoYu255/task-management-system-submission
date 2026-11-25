package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.ApiResponse;
import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.dto.UserLoginRequest;
import cn.edu.cjlu.taskmanagement.dto.UserQuery;
import cn.edu.cjlu.taskmanagement.dto.UserRegisterRequest;
import cn.edu.cjlu.taskmanagement.dto.UserUpdateSkillsRequest;
import cn.edu.cjlu.taskmanagement.service.UserService;
import cn.edu.cjlu.taskmanagement.vo.UserVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户接口层（Controller）：只负责接收请求、参数校验、调用 service、包装响应。
 */
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    /** 注册：POST /api/users/register */
    @PostMapping("/register")
    public ApiResponse<UserVO> register(@Valid @RequestBody UserRegisterRequest request) {
        return ApiResponse.success(userService.register(request));
    }

    /** 登录：POST /api/users/login */
    @PostMapping("/login")
    public ApiResponse<UserVO> login(@Valid @RequestBody UserLoginRequest request) {
        return ApiResponse.success(userService.login(request.getUsername(), request.getPassword()));
    }

    /** 分页查询：GET /api/users?role=&skill=&page=1&size=10 */
    @GetMapping
    public ApiResponse<PageResult<UserVO>> page(@Valid UserQuery query) {
        return ApiResponse.success(userService.page(query));
    }

    /** 查询详情：GET /api/users/{id} */
    @GetMapping("/{id}")
    public ApiResponse<UserVO> detail(@PathVariable Long id) {
        return ApiResponse.success(userService.getById(id));
    }

    /** 全量更新技能标签：PUT /api/users/{id}/skills */
    @PutMapping("/{id}/skills")
    public ApiResponse<Void> updateSkills(@PathVariable Long id,
                                          @Valid @RequestBody UserUpdateSkillsRequest request) {
        userService.updateSkills(id, request.getSkills());
        return ApiResponse.success();
    }
}
