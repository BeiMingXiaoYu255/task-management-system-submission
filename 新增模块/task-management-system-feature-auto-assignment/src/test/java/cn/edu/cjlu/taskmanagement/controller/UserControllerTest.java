package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.service.UserService;
import cn.edu.cjlu.taskmanagement.vo.UserVO;
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
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Controller 层切片测试：只加载 Web 层，Service 用 Mock 替代，不需要数据库。
 */
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserService userService;

    @Test
    @DisplayName("POST /api/users/register 返回统一响应结构且不含密码")
    void shouldRegisterUser() throws Exception {
        UserVO vo = UserVO.builder()
                .id(1L)
                .username("zhangsan")
                .nickname("张三")
                .role("EMPLOYEE")
                .roleLabel("雇员")
                .skills(List.of("java"))
                .build();
        when(userService.register(any())).thenReturn(vo);

        mockMvc.perform(post("/api/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"zhangsan\",\"password\":\"secret123\",\"nickname\":\"张三\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.username").value("zhangsan"))
                .andExpect(jsonPath("$.data.roleLabel").value("雇员"))
                .andExpect(jsonPath("$.password").doesNotExist())
                .andExpect(jsonPath("$.data.password").doesNotExist());
    }

    @Test
    @DisplayName("POST /api/users/register 用户名为空时返回 400 与校验信息")
    void shouldRejectBlankUsername() throws Exception {
        mockMvc.perform(post("/api/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"\",\"password\":\"secret123\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value(containsString("用户名不能为空")));
    }

    @Test
    @DisplayName("POST /api/users/register 密码过短时返回 400")
    void shouldRejectShortPassword() throws Exception {
        mockMvc.perform(post("/api/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"zhangsan\",\"password\":\"123\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("POST /api/users/login 用户名或密码错误时返回 401")
    void shouldReturn401WhenLoginFails() throws Exception {
        when(userService.login(anyString(), anyString()))
                .thenThrow(new BusinessException(401, "用户名或密码错误"));

        mockMvc.perform(post("/api/users/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"ghost\",\"password\":\"wrong123\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.message").value("用户名或密码错误"));
    }

    @Test
    @DisplayName("GET /api/users?skill=java 返回统一的分页响应结构")
    void shouldReturnUserPage() throws Exception {
        UserVO vo = UserVO.builder()
                .id(2L)
                .username("lisi")
                .role("EMPLOYEE")
                .roleLabel("雇员")
                .skills(List.of("java"))
                .build();
        when(userService.page(any())).thenReturn(PageResult.of(List.of(vo), 1L, 1, 10));

        mockMvc.perform(get("/api/users").param("skill", "java"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.records[0].username").value("lisi"))
                .andExpect(jsonPath("$.data.records[0].skills[0]").value("java"));
    }

    @Test
    @DisplayName("GET /api/users/{id} 用户不存在时返回 404")
    void shouldReturn404WhenUserMissing() throws Exception {
        when(userService.getById(99L)).thenThrow(new BusinessException(404, "用户不存在：99"));

        mockMvc.perform(get("/api/users/99"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value(404))
                .andExpect(jsonPath("$.message").value("用户不存在：99"));
    }

    @Test
    @DisplayName("PUT /api/users/{id}/skills 全量覆盖技能标签")
    void shouldUpdateSkills() throws Exception {
        mockMvc.perform(put("/api/users/1/skills")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"skills\":[\"python\",\"c++\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(0));
    }
}
