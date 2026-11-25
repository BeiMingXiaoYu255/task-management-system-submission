package cn.edu.cjlu.taskmanagement.service.assignment.impl;

import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.PublishTaskRequest;
import cn.edu.cjlu.taskmanagement.dto.TaskCreateRequest;
import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import cn.edu.cjlu.taskmanagement.service.TaskService;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentService;
import cn.edu.cjlu.taskmanagement.service.assignment.LocalRecommendationEngine;
import cn.edu.cjlu.taskmanagement.service.assignment.TaskPublishService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 任务发布编排实现。
 *
 * <p>复用队友的 {@link TaskService#create} 完成任务创建，再触发智能分配，
 * 全程同一个事务：分配链路抛异常时任务创建一并回滚。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TaskPublishServiceImpl implements TaskPublishService {

    private final UserMapper userMapper;
    private final TaskService taskService;
    private final AssignmentService assignmentService;

    @Override
    @Transactional
    public TaskVO publish(PublishTaskRequest request) {
        User publisher = requirePublisher(request.getPublisherId());

        // 复用既有创建逻辑，保证与新普通建任务走同一套默认值
        TaskCreateRequest create = new TaskCreateRequest();
        create.setTitle(request.getTitle());
        create.setDescription(request.getDescription());
        create.setPriority(request.getPriority());
        create.setDueDate(request.getDueDate());
        TaskVO created = taskService.create(create);

        String requiredSkills = String.join(",", LocalRecommendationEngine.normalize(request.getRequiredSkills()));
        var result = assignmentService.assign(created.getId(), created.getTitle(), requiredSkills, publisher.getId());
        log.info("任务 {} 由 {} 发布，分配结果：{}", created.getId(), publisher.getUsername(), result.getMessage());

        // 重新查询，返回带分配列的最新数据
        return taskService.getById(created.getId());
    }

    /** 发布者必须存在且为 BOSS */
    private User requirePublisher(Long publisherId) {
        if (publisherId == null) {
            throw new BusinessException("发布者 ID 不能为空");
        }
        User publisher = userMapper.selectById(publisherId);
        if (publisher == null) {
            throw new BusinessException(404, "发布者不存在：" + publisherId);
        }
        if (publisher.getRole() != UserRole.BOSS) {
            throw new BusinessException(403, "只有老板级用户可以发布任务");
        }
        return publisher;
    }
}
