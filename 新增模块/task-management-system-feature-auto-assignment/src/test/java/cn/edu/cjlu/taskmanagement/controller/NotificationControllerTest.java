package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.service.NotificationService;
import cn.edu.cjlu.taskmanagement.vo.NotificationVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 通知接口切片测试：只加载 Web 层，Service 用 Mock 替代，不需要数据库。
 */
@WebMvcTest(NotificationController.class)
class NotificationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NotificationService notificationService;

    @Test
    @DisplayName("GET /api/notifications 返回统一分页结构")
    void shouldReturnNotificationPage() throws Exception {
        NotificationVO vo = NotificationVO.builder()
                .id(1L)
                .taskId(10L)
                .title("新任务分配通知")
                .content("任务「写推荐引擎」已自动分配给你")
                .read(false)
                .build();
        when(notificationService.page(any(), anyBoolean(), anyInt(), anyInt()))
                .thenReturn(PageResult.of(List.of(vo), 1L, 1, 10));

        mockMvc.perform(get("/api/notifications").param("userId", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.records[0].title").value("新任务分配通知"))
                .andExpect(jsonPath("$.data.records[0].read").value(false));
    }

    @Test
    @DisplayName("GET /api/notifications 缺少 userId 时返回 400")
    void shouldRejectMissingUserId() throws Exception {
        mockMvc.perform(get("/api/notifications"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(containsString("userId")));
    }

    @Test
    @DisplayName("GET /api/notifications/unread-count 返回未读数")
    void shouldReturnUnreadCount() throws Exception {
        when(notificationService.page(anyLong(), eq(true), anyInt(), anyInt()))
                .thenReturn(PageResult.of(List.of(), 3L, 1, 1));

        mockMvc.perform(get("/api/notifications/unread-count").param("userId", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").value(3));
    }

    @Test
    @DisplayName("PATCH /api/notifications/{id}/read 标记他人通知返回 404")
    void shouldReturn404WhenMarkingOthersNotification() throws Exception {
        doThrow(new BusinessException(404, "通知不存在：1"))
                .when(notificationService).markRead(1L, 2L);

        mockMvc.perform(patch("/api/notifications/1/read").param("userId", "2"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    @DisplayName("PATCH /api/notifications/read-all 全部已读")
    void shouldMarkAllRead() throws Exception {
        mockMvc.perform(patch("/api/notifications/read-all").param("userId", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));

        verify(notificationService).markAllRead(2L);
    }
}
