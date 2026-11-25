package cn.edu.cjlu.taskmanagement.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 用户登录的请求参数。
 */
@Data
public class UserLoginRequest {

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;
}
