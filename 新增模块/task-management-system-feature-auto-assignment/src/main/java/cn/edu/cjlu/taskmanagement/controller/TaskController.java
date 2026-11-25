package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.ApiResponse;
import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.dto.TaskCreateRequest;
import cn.edu.cjlu.taskmanagement.dto.TaskQuery;
import cn.edu.cjlu.taskmanagement.dto.TaskUpdateRequest;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import cn.edu.cjlu.taskmanagement.service.TaskService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * 任务接口层（Controller）：只负责接收请求、参数校验、调用 service、包装响应。
 */
@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    /** 分页查询：GET /api/tasks?keyword=&status=&priority=&page=1&size=10 */
    @GetMapping
    public ApiResponse<PageResult<TaskVO>> page(@Valid TaskQuery query) {
        return ApiResponse.success(taskService.page(query));
    }

    /** 查询详情：GET /api/tasks/{id} */
    @GetMapping("/{id}")
    public ApiResponse<TaskVO> detail(@PathVariable Long id) {
        return ApiResponse.success(taskService.getById(id));
    }

    /** 新建任务：POST /api/tasks */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<TaskVO> create(@Valid @RequestBody TaskCreateRequest request) {
        return ApiResponse.success(taskService.create(request));
    }

    /** 修改任务：PUT /api/tasks/{id} */
    @PutMapping("/{id}")
    public ApiResponse<TaskVO> update(@PathVariable Long id,
                                      @Valid @RequestBody TaskUpdateRequest request) {
        return ApiResponse.success(taskService.update(id, request));
    }

    /** 修改状态：PATCH /api/tasks/{id}/status?status=DONE */
    @PatchMapping("/{id}/status")
    public ApiResponse<TaskVO> changeStatus(@PathVariable Long id,
                                            @RequestParam TaskStatus status) {
        return ApiResponse.success(taskService.changeStatus(id, status));
    }

    /** 删除任务：DELETE /api/tasks/{id} */
    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id) {
        taskService.delete(id);
        return ApiResponse.success();
    }
}
