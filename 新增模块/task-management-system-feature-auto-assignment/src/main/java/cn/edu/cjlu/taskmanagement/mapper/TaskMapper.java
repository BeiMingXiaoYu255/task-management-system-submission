package cn.edu.cjlu.taskmanagement.mapper;

import cn.edu.cjlu.taskmanagement.dto.TaskQuery;
import cn.edu.cjlu.taskmanagement.entity.Task;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 任务表持久层接口，SQL 写在 {@code resources/mapper/TaskMapper.xml}。
 *
 * <p>注意：这里只做数据库操作，不写业务逻辑（业务逻辑在 service 层）。</p>
 */
@Mapper
public interface TaskMapper {

    /** 分页查询 */
    List<Task> selectPage(@Param("query") TaskQuery query,
                          @Param("offset") int offset,
                          @Param("size") int size);

    /** 查询满足条件的总条数 */
    long countByQuery(@Param("query") TaskQuery query);

    /** 按主键查询，不存在返回 null */
    Task selectById(@Param("id") Long id);

    /** 新增，成功后回填自增主键 */
    int insert(Task task);

    /** 更新可变字段（标题、描述、状态、优先级、截止时间） */
    int update(Task task);

    /** 只更新状态 */
    int updateStatus(@Param("id") Long id,
                     @Param("status") TaskStatus status,
                     @Param("updatedAt") LocalDateTime updatedAt);

    /** 按主键删除 */
    int deleteById(@Param("id") Long id);
}
