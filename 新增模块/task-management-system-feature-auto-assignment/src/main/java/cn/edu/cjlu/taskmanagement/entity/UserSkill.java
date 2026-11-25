package cn.edu.cjlu.taskmanagement.entity;

import lombok.Data;

/**
 * 用户技能标签实体，对应数据库表 {@code user_skill}。
 *
 * <p>一个用户可拥有多个技能标签，(user_id, skill_name) 唯一。</p>
 */
@Data
public class UserSkill {

    /** 主键，自增 */
    private Long id;

    /** 所属用户ID */
    private Long userId;

    /** 技能标签，小写：java/python/c++ 等，与标签字典保持一致 */
    private String skillName;
}
