package cn.edu.cjlu.taskmanagement.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 任务实体，对应数据库表 {@code task}。
 *
 * <p>字段与表列通过 {@code map-underscore-to-camel-case} 自动映射
 * （due_date → dueDate）。</p>
 */
@Data
public class Task {

    /** 主键，自增 */
    private Long id;

    /** 任务标题 */
    private String title;

    /** 任务描述 */
    private String description;

    /** 状态：TODO / IN_PROGRESS / DONE */
    private TaskStatus status;

    /** 优先级：LOW / MEDIUM / HIGH */
    private TaskPriority priority;

    /** 截止时间 */
    private LocalDateTime dueDate;

    /** 所需技能标签，多个用英文逗号分隔，小写：java,python */
    private String requiredSkills;

    /** 被分配雇员的用户ID，未分配时为 null */
    private Long assigneeId;

    /** 分配方式：UNASSIGNED / AUTO / MANUAL */
    private AssignStatus assignStatus;

    /** 发布者（老板）用户ID */
    private Long publisherId;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 最后更新时间 */
    private LocalDateTime updatedAt;
}
