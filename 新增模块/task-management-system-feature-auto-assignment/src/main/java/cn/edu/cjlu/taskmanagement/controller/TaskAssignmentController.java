package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.ApiResponse;
import cn.edu.cjlu.taskmanagement.dto.PublishTaskRequest;
import cn.edu.cjlu.taskmanagement.service.assignment.TaskPublishService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * 任务发布接口（自动分配入口）。
 *
 * <p>与 {@link TaskController} 同基路径但方法路径不同，互不冲突：
 * 普通增删改查走 {@code TaskController}，"发布即分配"走这里。</p>
 */
@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
public class TaskAssignmentController {

    private final TaskPublishService taskPublishService;

    /** 发布任务（老板）：POST /api/tasks/publish，创建任务并自动分配给技能符合度最高的雇员 */
    @PostMapping("/publish")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<TaskVO> publish(@Valid @RequestBody PublishTaskRequest request) {
        return ApiResponse.success(taskPublishService.publish(request));
    }
}
