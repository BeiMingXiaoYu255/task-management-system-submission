package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 修改任务的请求参数（PUT 为全量修改，标题和状态必填）。
 */
@Data
public class TaskUpdateRequest {

    @NotBlank(message = "任务标题不能为空")
    @Size(max = 100, message = "任务标题长度不能超过 100 个字符")
    private String title;

    @Size(max = 500, message = "任务描述长度不能超过 500 个字符")
    private String description;

    @NotNull(message = "任务状态不能为空")
    private TaskStatus status;

    /** 不传时保留原优先级 */
    private TaskPriority priority;

    /** ISO 格式，例如 2026-11-10T18:00:00 */
    private LocalDateTime dueDate;
}
