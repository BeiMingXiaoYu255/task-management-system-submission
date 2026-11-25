package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.UserRole;
import lombok.Data;

/**
 * 用户列表查询条件。
 *
 * <p>GET /api/users?role=EMPLOYEE&amp;skill=java&amp;page=1&amp;size=10</p>
 */
@Data
public class UserQuery {

    /** 按角色过滤，可空 */
    private UserRole role;

    /** 按技能标签过滤（精确匹配单个标签，小写），可空 */
    private String skill;

    /** 页码，从 1 开始 */
    private int page = 1;

    /** 每页条数 */
    private int size = 10;
}
