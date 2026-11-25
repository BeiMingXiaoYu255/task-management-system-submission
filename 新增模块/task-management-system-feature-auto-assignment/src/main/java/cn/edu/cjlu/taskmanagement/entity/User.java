package cn.edu.cjlu.taskmanagement.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 用户实体，对应数据库表 {@code user}。
 *
 * <p>字段与表列通过 {@code map-underscore-to-camel-case} 自动映射。</p>
 */
@Data
public class User {

    /** 主键，自增 */
    private Long id;

    /** 登录名，唯一 */
    private String username;

    /** BCrypt 密码摘要，任何接口不得对外返回 */
    private String password;

    /** 显示昵称 */
    private String nickname;

    /** 角色：BOSS / EMPLOYEE */
    private UserRole role;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 最后更新时间 */
    private LocalDateTime updatedAt;
}
