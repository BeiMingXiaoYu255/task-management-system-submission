package cn.edu.cjlu.taskmanagement.service;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.dto.TaskCreateRequest;
import cn.edu.cjlu.taskmanagement.dto.TaskQuery;
import cn.edu.cjlu.taskmanagement.dto.TaskUpdateRequest;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;

/**
 * 任务业务接口：控制器只依赖这个接口，不直接接触 Mapper。
 */
public interface TaskService {

    /** 分页查询任务 */
    PageResult<TaskVO> page(TaskQuery query);

    /** 按 ID 查询任务，不存在时抛 404 业务异常 */
    TaskVO getById(Long id);

    /** 新建任务 */
    TaskVO create(TaskCreateRequest request);

    /** 全量修改任务 */
    TaskVO update(Long id, TaskUpdateRequest request);

    /** 只修改状态 */
    TaskVO changeStatus(Long id, TaskStatus status);

    /** 删除任务，不存在时抛 404 业务异常 */
    void delete(Long id);
}
