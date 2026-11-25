package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.UserRole;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 注册用户的请求参数。
 *
 * <p>技能标签可选；不传角色时默认为 {@link UserRole#EMPLOYEE}。</p>
 */
@Data
public class UserRegisterRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(max = 50, message = "用户名长度不能超过 50 个字符")
    @Pattern(regexp = "^[A-Za-z0-9_-]+$", message = "用户名只能包含字母、数字、下划线和短横线")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度必须在 6 到 100 个字符之间")
    private String password;

    @Size(max = 50, message = "昵称长度不能超过 50 个字符")
    private String nickname;

    /** 不传时默认为 EMPLOYEE */
    private UserRole role;

    /** 技能标签列表，小写；仅对 EMPLOYEE 有意义，可空 */
    @Size(max = 20, message = "技能标签最多 20 个")
    private List<String> skills;
}
