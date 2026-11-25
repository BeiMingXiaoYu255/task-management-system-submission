package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.service.TaskService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Controller 层切片测试：只加载 Web 层，Service 用 Mock 替代，不需要数据库。
 */
@WebMvcTest(TaskController.class)
class TaskControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TaskService taskService;

    @Test
    @DisplayName("GET /api/tasks 返回统一的分页响应结构")
    void shouldReturnTaskPage() throws Exception {
        TaskVO task = TaskVO.builder()
                .id(1L)
                .title("写课程设计报告")
                .status("TODO")
                .statusLabel("待办")
                .priority("HIGH")
                .priorityLabel("高")
                .build();
        when(taskService.page(any())).thenReturn(PageResult.of(List.of(task), 1L, 1, 10));

        mockMvc.perform(get("/api/tasks").param("page", "1").param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.message").value("success"))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.records[0].title").value("写课程设计报告"))
                .andExpect(jsonPath("$.data.records[0].statusLabel").value("待办"));
    }

    @Test
    @DisplayName("POST /api/tasks 标题为空白时返回 400 与校验信息")
    void shouldRejectBlankTitle() throws Exception {
        mockMvc.perform(post("/api/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"   \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(containsString("任务标题不能为空")));
    }

    @Test
    @DisplayName("GET /api/tasks/{id} 任务不存在时返回 404")
    void shouldReturn404WhenTaskMissing() throws Exception {
        when(taskService.getById(anyLong())).thenThrow(new BusinessException(404, "任务不存在：1"));

        mockMvc.perform(get("/api/tasks/1"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.message").value("任务不存在：1"));
    }

    @Test
    @DisplayName("PATCH /api/tasks/{id}/status 状态非法时返回 400")
    void shouldRejectInvalidStatus() throws Exception {
        mockMvc.perform(patch("/api/tasks/1/status").param("status", "UNKNOWN"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }
}
