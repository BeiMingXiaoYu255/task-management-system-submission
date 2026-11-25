package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.TaskCreateRequest;
import cn.edu.cjlu.taskmanagement.dto.TaskQuery;
import cn.edu.cjlu.taskmanagement.dto.TaskUpdateRequest;
import cn.edu.cjlu.taskmanagement.entity.Task;
import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import cn.edu.cjlu.taskmanagement.mapper.TaskMapper;
import cn.edu.cjlu.taskmanagement.service.TaskService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 任务业务实现。
 *
 * <p>职责：校验业务规则（存在性、默认值、分页边界）、组装实体、调用 Mapper、
 * 把实体转换成对外的 VO。控制器不再写这些逻辑。</p>
 */
@Service
@RequiredArgsConstructor
public class TaskServiceImpl implements TaskService {

    private final TaskMapper taskMapper;

    @Override
    public PageResult<TaskVO> page(TaskQuery query) {
        TaskQuery condition = query == null ? new TaskQuery() : query;
        int page = Math.max(condition.getPage(), 1);
        int size = Math.min(Math.max(condition.getSize(), 1), 100);
        int offset = (page - 1) * size;

        long total = taskMapper.countByQuery(condition);
        if (total == 0) {
            return PageResult.of(List.of(), 0L, page, size);
        }

        List<TaskVO> records = taskMapper.selectPage(condition, offset, size)
                .stream()
                .map(TaskVO::from)
                .toList();
        return PageResult.of(records, total, page, size);
    }

    @Override
    public TaskVO getById(Long id) {
        return TaskVO.from(requireTask(id));
    }

    @Override
    @Transactional
    public TaskVO create(TaskCreateRequest request) {
        LocalDateTime now = LocalDateTime.now();
        Task task = new Task();
        task.setTitle(request.getTitle().trim());
        task.setDescription(request.getDescription());
        task.setStatus(TaskStatus.TODO);
        task.setPriority(request.getPriority() == null ? TaskPriority.MEDIUM : request.getPriority());
        task.setDueDate(request.getDueDate());
        task.setCreatedAt(now);
        task.setUpdatedAt(now);

        taskMapper.insert(task);
        return TaskVO.from(task);
    }

    @Override
    @Transactional
    public TaskVO update(Long id, TaskUpdateRequest request) {
        Task task = requireTask(id);
        task.setTitle(request.getTitle().trim());
        task.setDescription(request.getDescription());
        task.setStatus(request.getStatus());
        if (request.getPriority() != null) {
            task.setPriority(request.getPriority());
        }
        task.setDueDate(request.getDueDate());
        task.setUpdatedAt(LocalDateTime.now());

        taskMapper.update(task);
        return TaskVO.from(task);
    }

    @Override
    @Transactional
    public TaskVO changeStatus(Long id, TaskStatus status) {
        Task task = requireTask(id);
        if (status == null) {
            throw new BusinessException("任务状态不能为空");
        }
        LocalDateTime now = LocalDateTime.now();
        taskMapper.updateStatus(id, status, now);

        task.setStatus(status);
        task.setUpdatedAt(now);
        return TaskVO.from(task);
    }

    @Override
    @Transactional
    public void delete(Long id) {
        requireTask(id);
        taskMapper.deleteById(id);
    }

    /** 查找任务，不存在直接抛 404 */
    private Task requireTask(Long id) {
        if (id == null) {
            throw new BusinessException("任务 ID 不能为空");
        }
        Task task = taskMapper.selectById(id);
        if (task == null) {
            throw new BusinessException(404, "任务不存在：" + id);
        }
        return task;
    }
}
