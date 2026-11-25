package cn.edu.cjlu.taskmanagement.vo;

import cn.edu.cjlu.taskmanagement.entity.Task;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 返回给前端的任务视图对象。
 *
 * <p>与实体分开的原因：接口字段可以独立演进（例如增加 statusLabel 这类展示字段），
 * 不会因为数据库表结构变化而直接破坏前端契约。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TaskVO {

    private Long id;
    private String title;
    private String description;
    /** 状态枚举名，例如 TODO */
    private String status;
    /** 状态中文名，例如 待办 */
    private String statusLabel;
    /** 优先级枚举名，例如 HIGH */
    private String priority;
    /** 优先级中文名，例如 高 */
    private String priorityLabel;
    private LocalDateTime dueDate;
    /** 所需技能标签原文，多个用英文逗号分隔，例如 java,python */
    private String requiredSkills;
    /** 被分配雇员的用户ID，未分配时为 null */
    private Long assigneeId;
    /** 分配方式枚举名，例如 UNASSIGNED */
    private String assignStatus;
    /** 分配方式中文名，例如 未分配 */
    private String assignStatusLabel;
    /** 发布者（老板）用户ID */
    private Long publisherId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static TaskVO from(Task task) {
        if (task == null) {
            return null;
        }
        return TaskVO.builder()
                .id(task.getId())
                .title(task.getTitle())
                .description(task.getDescription())
                .status(task.getStatus() == null ? null : task.getStatus().name())
                .statusLabel(task.getStatus() == null ? null : task.getStatus().getLabel())
                .priority(task.getPriority() == null ? null : task.getPriority().name())
                .priorityLabel(task.getPriority() == null ? null : task.getPriority().getLabel())
                .dueDate(task.getDueDate())
                .requiredSkills(task.getRequiredSkills())
                .assigneeId(task.getAssigneeId())
                .assignStatus(task.getAssignStatus() == null ? null : task.getAssignStatus().name())
                .assignStatusLabel(task.getAssignStatus() == null ? null : task.getAssignStatus().getLabel())
                .publisherId(task.getPublisherId())
                .createdAt(task.getCreatedAt())
                .updatedAt(task.getUpdatedAt())
                .build();
    }
}
