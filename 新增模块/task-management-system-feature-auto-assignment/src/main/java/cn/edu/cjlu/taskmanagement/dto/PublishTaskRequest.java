package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 老板发布任务的请求参数。
 *
 * <p>与普通新建任务的 {@link TaskCreateRequest} 区分：发布 = 创建 + 自动分配，
 * 需要额外带上发布者与所需技能。</p>
 */
@Data
public class PublishTaskRequest {

    /** 发布者用户ID，必须是 BOSS 角色 */
    @NotNull(message = "发布者 ID 不能为空")
    private Long publisherId;

    @NotBlank(message = "任务标题不能为空")
    @Size(max = 100, message = "任务标题长度不能超过 100 个字符")
    private String title;

    @Size(max = 500, message = "任务描述长度不能超过 500 个字符")
    private String description;

    /** 不传时默认为 {@link TaskPriority#MEDIUM} */
    private TaskPriority priority;

    /** ISO 格式，例如 2026-11-10T18:00:00 */
    private LocalDateTime dueDate;

    /** 所需技能标签，例如 ["java","python"]，空表示无技能要求 */
    @Size(max = 20, message = "所需技能最多 20 个")
    private List<String> requiredSkills;
}
