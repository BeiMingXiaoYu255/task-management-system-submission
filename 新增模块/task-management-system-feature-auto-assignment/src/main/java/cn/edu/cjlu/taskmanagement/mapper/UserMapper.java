package cn.edu.cjlu.taskmanagement.mapper;

import cn.edu.cjlu.taskmanagement.dto.UserQuery;
import cn.edu.cjlu.taskmanagement.entity.User;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 用户表持久层：只做数据库操作。
 */
public interface UserMapper {

    /** 插入用户，回填自增主键 */
    int insert(User user);

    /** 按登录名查询，不存在返回 null */
    User selectByUsername(@Param("username") String username);

    /** 按主键查询，不存在返回 null */
    User selectById(@Param("id") Long id);

    /** 查询某角色的全部用户（推荐引擎的候选集来源） */
    List<User> selectAllByRole(@Param("role") String role);

    /** 统计满足条件的用户总数 */
    long countByQuery(@Param("query") UserQuery query);

    /** 分页查询用户；带 skill 条件时只返回拥有该技能的用户 */
    List<User> selectPage(@Param("query") UserQuery query,
                          @Param("offset") int offset,
                          @Param("size") int size);

    /** 查询某用户的全部技能标签名 */
    List<String> selectSkillNamesByUserId(@Param("userId") Long userId);

    /** 批量插入技能标签，重复项由唯一键 + INSERT IGNORE 兜底 */
    int insertSkills(@Param("userId") Long userId,
                     @Param("skills") List<String> skills);

    /** 删除某用户的全部技能标签（全量覆盖前调用） */
    int deleteSkillsByUserId(@Param("userId") Long userId);
}
