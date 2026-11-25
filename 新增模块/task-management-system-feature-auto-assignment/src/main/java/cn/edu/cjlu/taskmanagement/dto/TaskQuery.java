package cn.edu.cjlu.taskmanagement.dto;

import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.Data;

/**
 * 任务列表查询条件（GET /api/tasks 的查询参数）。
 */
@Data
public class TaskQuery {

    /** 标题或描述模糊搜索 */
    private String keyword;

    /** 状态精确筛选 */
    private TaskStatus status;

    /** 优先级精确筛选 */
    private TaskPriority priority;

    @Min(value = 1, message = "页码从 1 开始")
    private int page = 1;

    @Min(value = 1, message = "每页至少 1 条")
    @Max(value = 100, message = "每页最多 100 条")
    private int size = 10;
}
