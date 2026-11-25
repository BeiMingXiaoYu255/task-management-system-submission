package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 新建任务的请求参数。
 */
@Data
public class TaskCreateRequest {

    @NotBlank(message = "任务标题不能为空")
    @Size(max = 100, message = "任务标题长度不能超过 100 个字符")
    private String title;

    @Size(max = 500, message = "任务描述长度不能超过 500 个字符")
    private String description;

    /** 不传时默认为 {@link TaskPriority#MEDIUM} */
    private TaskPriority priority;

    /** ISO 格式，例如 2026-11-10T18:00:00 */
    private LocalDateTime dueDate;
}
