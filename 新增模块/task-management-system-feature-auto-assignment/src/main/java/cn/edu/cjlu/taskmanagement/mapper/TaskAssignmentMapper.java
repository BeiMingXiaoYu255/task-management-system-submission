package cn.edu.cjlu.taskmanagement.mapper;

import cn.edu.cjlu.taskmanagement.entity.AssignStatus;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;

/**
 * 任务分配相关持久层：只操作 task 表的分配列，与队友的 {@link TaskMapper} 各管各的列。
 */
public interface TaskAssignmentMapper {

    /** 更新任务的分配信息（required_skills / assignee_id / assign_status / publisher_id 由发布流程写入） */
    int updateAssignment(@Param("id") Long id,
                         @Param("requiredSkills") String requiredSkills,
                         @Param("assigneeId") Long assigneeId,
                         @Param("assignStatus") AssignStatus assignStatus,
                         @Param("updatedAt") LocalDateTime updatedAt);

    /** 统计某雇员名下未完成任务数（推荐打分的负载惩罚项） */
    long countActiveByAssignee(@Param("assigneeId") Long assigneeId);
}
