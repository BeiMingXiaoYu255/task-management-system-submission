package cn.edu.cjlu.taskmanagement.service.assignment;

import cn.edu.cjlu.taskmanagement.dto.PublishTaskRequest;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;

/**
 * 任务发布业务接口：发布 = 创建任务 + 触发自动分配。
 */
public interface TaskPublishService {

    /** 校验发布者身份后创建任务并自动分配，返回带分配结果的最新任务 */
    TaskVO publish(PublishTaskRequest request);
}
