package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.service.assignment.TaskPublishService;
import cn.edu.cjlu.taskmanagement.vo.TaskVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 任务发布接口切片测试：只加载 Web 层，Service 用 Mock 替代，不需要数据库。
 */
@WebMvcTest(TaskAssignmentController.class)
class TaskAssignmentControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TaskPublishService taskPublishService;

    @Test
    @DisplayName("POST /api/tasks/publish 返回 201 与带分配结果的任务")
    void shouldPublishAndAssign() throws Exception {
        TaskVO vo = TaskVO.builder()
                .id(10L)
                .title("写推荐引擎")
                .status("TODO")
                .statusLabel("待办")
                .requiredSkills("java,python")
                .assigneeId(2L)
                .assignStatus("AUTO")
                .assignStatusLabel("自动分配")
                .publisherId(1L)
                .build();
        when(taskPublishService.publish(any())).thenReturn(vo);

        mockMvc.perform(post("/api/tasks/publish")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"publisherId":1,"title":"写推荐引擎","priority":"HIGH",\
                                "requiredSkills":["java","python"]}"""))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.assignStatus").value("AUTO"))
                .andExpect(jsonPath("$.data.assignStatusLabel").value("自动分配"))
                .andExpect(jsonPath("$.data.publisherId").value(1));
    }

    @Test
    @DisplayName("POST /api/tasks/publish 标题为空时返回 400")
    void shouldRejectBlankTitle() throws Exception {
        mockMvc.perform(post("/api/tasks/publish")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"publisherId\":1,\"title\":\"   \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(containsString("任务标题不能为空")));
    }

    @Test
    @DisplayName("POST /api/tasks/publish 缺少发布者时返回 400")
    void shouldRejectMissingPublisher() throws Exception {
        mockMvc.perform(post("/api/tasks/publish")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"没有发布者\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(containsString("发布者")));
    }

    @Test
    @DisplayName("POST /api/tasks/publish 非老板发布时返回 403")
    void shouldReturn403WhenNotBoss() throws Exception {
        when(taskPublishService.publish(any()))
                .thenThrow(new BusinessException(403, "只有老板级用户可以发布任务"));

        mockMvc.perform(post("/api/tasks/publish")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"publisherId\":2,\"title\":\"越权发布\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value(403));
    }
}
