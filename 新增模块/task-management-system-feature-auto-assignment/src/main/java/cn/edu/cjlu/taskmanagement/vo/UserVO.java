package cn.edu.cjlu.taskmanagement.vo;

import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 返回给前端的用户视图对象。
 *
 * <p>绝不包含密码字段。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserVO {

    private Long id;
    private String username;
    private String nickname;
    /** 角色枚举名，例如 EMPLOYEE */
    private String role;
    /** 角色中文名，例如 雇员 */
    private String roleLabel;
    /** 技能标签列表（仅查询详情/列表时按需填充） */
    private List<String> skills;
    private LocalDateTime createdAt;

    public static UserVO from(User user) {
        return from(user, null);
    }

    public static UserVO from(User user, List<String> skills) {
        if (user == null) {
            return null;
        }
        return UserVO.builder()
                .id(user.getId())
                .username(user.getUsername())
                .nickname(user.getNickname())
                .role(user.getRole() == null ? null : user.getRole().name())
                .roleLabel(user.getRole() == null ? null : user.getRole().getLabel())
                .skills(skills)
                .createdAt(user.getCreatedAt())
                .build();
    }
}
