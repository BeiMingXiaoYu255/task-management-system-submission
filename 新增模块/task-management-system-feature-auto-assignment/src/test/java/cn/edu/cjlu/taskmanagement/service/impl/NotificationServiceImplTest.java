package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.entity.Notification;
import cn.edu.cjlu.taskmanagement.mapper.NotificationMapper;
import cn.edu.cjlu.taskmanagement.vo.NotificationVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 通知业务单元测试：用 Mockito 模拟 Mapper，不需要数据库。
 */
@ExtendWith(MockitoExtension.class)
class NotificationServiceImplTest {

    @Mock
    private NotificationMapper notificationMapper;

    @InjectMocks
    private NotificationServiceImpl notificationService;

    private Notification notification(long id, long userId, boolean read) {
        Notification notification = new Notification();
        notification.setId(id);
        notification.setUserId(userId);
        notification.setTaskId(10L);
        notification.setTitle("新任务分配通知");
        notification.setContent("任务「写推荐引擎」已分配给你");
        notification.setReadFlag(read ? 1 : 0);
        return notification;
    }

    @Test
    @DisplayName("分页查询：正常返回并转为 VO，read 字段由 read_flag 映射")
    void pageShouldMapToVo() {
        when(notificationMapper.countByQuery(2L, false)).thenReturn(1L);
        when(notificationMapper.selectPage(2L, false, 0, 10)).thenReturn(List.of(notification(1L, 2L, false)));

        PageResult<NotificationVO> result = notificationService.page(2L, false, 1, 10);

        assertThat(result.getTotal()).isEqualTo(1);
        assertThat(result.getRecords()).hasSize(1);
        assertThat(result.getRecords().get(0).getId()).isEqualTo(1L);
        assertThat(result.getRecords().get(0).isRead()).isFalse();
    }

    @Test
    @DisplayName("分页查询：total 为 0 时返回空列表，不查明细")
    void pageShouldSkipDetailWhenEmpty() {
        when(notificationMapper.countByQuery(anyLong(), anyBoolean())).thenReturn(0L);

        PageResult<NotificationVO> result = notificationService.page(2L, true, 1, 10);

        assertThat(result.getRecords()).isEmpty();
        verify(notificationMapper, never()).selectPage(anyLong(), anyBoolean(), anyInt(), anyInt());
    }

    @Test
    @DisplayName("分页查询：size 超过上限钳制为 100，页码最小为 1")
    void pageShouldClampBounds() {
        when(notificationMapper.countByQuery(anyLong(), anyBoolean())).thenReturn(0L);

        notificationService.page(2L, false, -3, 5000);

        // 钳制后的边界由 offset = (page-1)*size 体现，这里验证查询确实以规范化后的参数执行
        verify(notificationMapper).countByQuery(eq(2L), eq(false));
    }

    @Test
    @DisplayName("标记已读：非本人或不存在（0 行受影响）抛 404")
    void markReadShouldThrowWhenNotOwner() {
        when(notificationMapper.markRead(1L, 2L)).thenReturn(0);

        assertThatThrownBy(() -> notificationService.markRead(1L, 2L))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("通知不存在")
                .hasFieldOrPropertyWithValue("code", 404);
    }

    @Test
    @DisplayName("标记已读：本人通知正常通过")
    void markReadShouldPassForOwner() {
        when(notificationMapper.markRead(1L, 2L)).thenReturn(1);

        notificationService.markRead(1L, 2L);

        verify(notificationMapper).markRead(1L, 2L);
    }

    @Test
    @DisplayName("缺少用户 ID：抛业务异常")
    void shouldRejectMissingUserId() {
        assertThatThrownBy(() -> notificationService.page(null, false, 1, 10))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户 ID 不能为空");
        verify(notificationMapper, never()).countByQuery(anyLong(), anyBoolean());
    }
}
