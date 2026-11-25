package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.TaskCreateRequest;
import cn.edu.cjlu.taskmanagement.dto.TaskQuery;
import cn.edu.cjlu.taskmanagement.entity.Task;
import cn.edu.cjlu.taskmanagement.entity.TaskPriority;
import cn.edu.cjlu.taskmanagement.entity.TaskStatus;
import cn.edu.cjlu.taskmanagement.mapper.TaskMapper;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Service 层单元测试：用 Mockito 模拟 Mapper，不需要数据库。
 */
@ExtendWith(MockitoExtension.class)
class TaskServiceImplTest {

    @Mock
    private TaskMapper taskMapper;

    @InjectMocks
    private TaskServiceImpl taskService;

    @Test
    @DisplayName("新建任务：默认状态为 TODO、默认优先级为 MEDIUM，并去掉标题首尾空白")
    void createShouldApplyDefaults() {
        TaskCreateRequest request = new TaskCreateRequest();
        request.setTitle("  完成需求分析  ");

        doAnswer(invocation -> {
            Task task = invocation.getArgument(0);
            task.setId(1L);
            return 1;
        }).when(taskMapper).insert(any(Task.class));

        TaskVO vo = taskService.create(request);

        assertThat(vo.getId()).isEqualTo(1L);
        assertThat(vo.getTitle()).isEqualTo("完成需求分析");
        assertThat(vo.getStatus()).isEqualTo(TaskStatus.TODO.name());
        assertThat(vo.getStatusLabel()).isEqualTo("待办");
        assertThat(vo.getPriority()).isEqualTo(TaskPriority.MEDIUM.name());
        assertThat(vo.getPriorityLabel()).isEqualTo("中");

        ArgumentCaptor<Task> captor = ArgumentCaptor.forClass(Task.class);
        verify(taskMapper).insert(captor.capture());
        assertThat(captor.getValue().getCreatedAt()).isNotNull();
        assertThat(captor.getValue().getUpdatedAt()).isNotNull();
    }

    @Test
    @DisplayName("查询不存在的任务：抛 404 业务异常")
    void getByIdShouldThrowWhenMissing() {
        when(taskMapper.selectById(99L)).thenReturn(null);

        assertThatThrownBy(() -> taskService.getById(99L))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("任务不存在")
                .hasFieldOrPropertyWithValue("code", 404);
    }

    @Test
    @DisplayName("分页查询：总数为 0 时返回空列表，且不再查询明细")
    void pageShouldSkipDetailQueryWhenEmpty() {
        when(taskMapper.countByQuery(any(TaskQuery.class))).thenReturn(0L);

        PageResult<TaskVO> result = taskService.page(new TaskQuery());

        assertThat(result.getTotal()).isZero();
        assertThat(result.getRecords()).isEmpty();
        assertThat(result.getPage()).isEqualTo(1);
        assertThat(result.getSize()).isEqualTo(10);
        verify(taskMapper, never()).selectPage(any(), anyInt(), anyInt());
    }

    @Test
    @DisplayName("分页查询：size 超过上限时被限制为 100")
    void pageShouldClampSizeToUpperBound() {
        TaskQuery query = new TaskQuery();
        query.setSize(1000);
        when(taskMapper.countByQuery(any(TaskQuery.class))).thenReturn(0L);

        PageResult<TaskVO> result = taskService.page(query);

        assertThat(result.getSize()).isEqualTo(100);
    }
}
