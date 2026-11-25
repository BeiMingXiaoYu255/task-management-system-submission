package cn.edu.cjlu.taskmanagement.service.assignment.impl;

import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.PublishTaskRequest;
import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import cn.edu.cjlu.taskmanagement.service.TaskService;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentResult;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 任务发布编排单元测试：验证身份校验与"创建 → 分配 → 回查"流程。
 */
@ExtendWith(MockitoExtension.class)
class TaskPublishServiceImplTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private TaskService taskService;

    @Mock
    private AssignmentService assignmentService;

    @InjectMocks
    private TaskPublishServiceImpl publishService;

    private User user(long id, UserRole role) {
        User user = new User();
        user.setId(id);
        user.setUsername("u" + id);
        user.setRole(role);
        return user;
    }

    @Test
    @DisplayName("老板发布成功：创建任务后触发分配，返回带分配结果的最新数据")
    void shouldCreateThenAssignThenReload() {
        when(userMapper.selectById(1L)).thenReturn(user(1L, UserRole.BOSS));
        TaskVO created = TaskVO.builder().id(10L).title("写推荐引擎").build();
        when(taskService.create(any())).thenReturn(created);
        when(assignmentService.assign(eq(10L), eq("写推荐引擎"), eq("java,python"), eq(1L)))
                .thenReturn(AssignmentResult.builder().taskId(10L).assigned(true).assigneeId(2L).build());
        TaskVO reloaded = TaskVO.builder().id(10L).title("写推荐引擎").assigneeId(2L).build();
        when(taskService.getById(10L)).thenReturn(reloaded);

        PublishTaskRequest request = new PublishTaskRequest();
        request.setPublisherId(1L);
        request.setTitle("写推荐引擎");
        request.setRequiredSkills(java.util.List.of("Java", "python"));

        TaskVO vo = publishService.publish(request);

        assertThat(vo.getAssigneeId()).isEqualTo(2L);
        // 传给分配服务前技能已规范化为小写逗号串
        verify(assignmentService).assign(eq(10L), eq("写推荐引擎"), eq("java,python"), eq(1L));
    }

    @Test
    @DisplayName("发布者不是老板：抛 403，不创建任务")
    void shouldRejectNonBossPublisher() {
        when(userMapper.selectById(2L)).thenReturn(user(2L, UserRole.EMPLOYEE));

        PublishTaskRequest request = new PublishTaskRequest();
        request.setPublisherId(2L);
        request.setTitle("越权发布");

        assertThatThrownBy(() -> publishService.publish(request))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("只有老板级用户可以发布任务")
                .hasFieldOrPropertyWithValue("code", 403);
        verify(taskService, never()).create(any());
        verify(assignmentService, never()).assign(any(), any(), any(), any());
    }

    @Test
    @DisplayName("发布者不存在：抛 404")
    void shouldRejectMissingPublisher() {
        when(userMapper.selectById(99L)).thenReturn(null);

        PublishTaskRequest request = new PublishTaskRequest();
        request.setPublisherId(99L);
        request.setTitle("幽灵发布");

        assertThatThrownBy(() -> publishService.publish(request))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("发布者不存在")
                .hasFieldOrPropertyWithValue("code", 404);
    }
}
