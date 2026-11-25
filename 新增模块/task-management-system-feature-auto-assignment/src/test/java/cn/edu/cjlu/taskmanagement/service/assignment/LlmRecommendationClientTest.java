package cn.edu.cjlu.taskmanagement.service.assignment;

import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.mapper.TaskAssignmentMapper;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.lenient;

/**
 * LLM 推荐链路单元测试：覆写 HTTP 方法，不发起真实网络请求。
 */
@ExtendWith(MockitoExtension.class)
class LlmRecommendationClientTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private TaskAssignmentMapper taskAssignmentMapper;

    private LlmProperties properties;
    private TestableLlmClient client;

    /** 只替换 HTTP 调用，其余逻辑全部走真实实现 */
    static class TestableLlmClient extends LlmRecommendationClient {
        private String cannedContent;
        private RuntimeException httpFailure;

        TestableLlmClient(LlmProperties properties, UserMapper userMapper, TaskAssignmentMapper taskAssignmentMapper) {
            super(properties, userMapper, taskAssignmentMapper);
        }

        @Override
        String postForChatCompletion(String systemPrompt, String userPrompt) {
            if (httpFailure != null) {
                throw httpFailure;
            }
            return cannedContent;
        }
    }

    @BeforeEach
    void setUp() {
        properties = new LlmProperties();
        properties.setBaseUrl("https://llm.example.com");
        properties.setApiKey("test-key");
        properties.setModel("test-model");
        client = new TestableLlmClient(properties, userMapper, taskAssignmentMapper);
    }

    private void mockEmployees() {
        User alice = new User();
        alice.setId(2L);
        alice.setUsername("alice");
        alice.setNickname("后端·Alice");
        User bob = new User();
        bob.setId(3L);
        bob.setUsername("bob");
        bob.setNickname("前端·Bob");
        lenient().when(userMapper.selectAllByRole("EMPLOYEE")).thenReturn(List.of(alice, bob));
        lenient().when(userMapper.selectSkillNamesByUserId(2L)).thenReturn(List.of("java", "python"));
        lenient().when(userMapper.selectSkillNamesByUserId(3L)).thenReturn(List.of("java"));
        lenient().when(taskAssignmentMapper.countActiveByAssignee(2L)).thenReturn(1L);
        lenient().when(taskAssignmentMapper.countActiveByAssignee(3L)).thenReturn(0L);
    }

    @Test
    @DisplayName("未配置 API：直接返回空结果并说明原因，不发起 HTTP 调用")
    void shouldReturnEmptyWhenNotConfigured() {
        properties.setApiKey("");
        TestableLlmClient unconfigured = new TestableLlmClient(properties, userMapper, taskAssignmentMapper) {
            @Override
            String postForChatCompletion(String systemPrompt, String userPrompt) {
                throw new AssertionError("未配置时不应发起 HTTP 调用");
            }
        };

        RecommendationResult result = unconfigured.recommend(List.of("java"));

        assertThat(result.getTopCandidate()).isNull();
        assertThat(result.getRoute()).isEqualTo("llm");
        assertThat(result.getReason()).contains("LLM API 未配置");
    }

    @Test
    @DisplayName("正常返回：解析排序 JSON，忽略无效 ID，按排名给展示分")
    void shouldParseRankedResponse() {
        mockEmployees();
        client.cannedContent = """
                {"rankedUserIds":[3,2,99],"reason":"bob 负载更低且技能足够"}""";

        RecommendationResult result = client.recommend(List.of("java", "python"));

        assertThat(result.getCandidates()).hasSize(2); // 99 是幻觉 ID，被忽略
        assertThat(result.getTopCandidate().getUserId()).isEqualTo(3L);
        assertThat(result.getTopCandidate().getScore()).isEqualTo(100);
        assertThat(result.getCandidates().get(1).getUserId()).isEqualTo(2L);
        assertThat(result.getCandidates().get(1).getScore()).isEqualTo(90);
        assertThat(result.getTopCandidate().getMatchRatio()).isEqualTo(0.5); // bob 只命中 java
        assertThat(result.getReason()).contains("bob");
    }

    @Test
    @DisplayName("返回带 markdown 代码块的内容：能提取出 JSON")
    void shouldExtractJsonFromFencedContent() {
        mockEmployees();
        client.cannedContent = "```json\n{\"rankedUserIds\":[2],\"reason\":\"alice 全部命中\"}\n```";

        RecommendationResult result = client.recommend(List.of("java", "python"));

        assertThat(result.getTopCandidate().getUserId()).isEqualTo(2L);
        assertThat(result.getTopCandidate().getMatchRatio()).isEqualTo(1.0);
    }

    @Test
    @DisplayName("返回内容不是 JSON：抛 LlmRouteException")
    void shouldThrowWhenContentNotJson() {
        mockEmployees();
        client.cannedContent = "抱歉，我无法完成这个请求。";

        assertThatThrownBy(() -> client.recommend(List.of("java")))
                .isInstanceOf(LlmRouteException.class)
                .hasMessageContaining("不是合法 JSON");
    }

    @Test
    @DisplayName("HTTP 调用失败：抛 LlmRouteException，由调度层回退")
    void shouldThrowWhenHttpFails() {
        mockEmployees();
        client.httpFailure = new RuntimeException("connect timeout");

        assertThatThrownBy(() -> client.recommend(List.of("java")))
                .isInstanceOf(LlmRouteException.class)
                .hasMessageContaining("调用 LLM 接口失败");
    }

    @Test
    @DisplayName("排序里全是无效 ID：返回空结果")
    void shouldReturnEmptyWhenAllIdsInvalid() {
        mockEmployees();
        client.cannedContent = "{\"rankedUserIds\":[88,99],\"reason\":\"\"}";

        RecommendationResult result = client.recommend(List.of("java"));

        assertThat(result.getCandidates()).isEmpty();
        assertThat(result.getReason()).contains("均无效");
    }

    @Test
    @DisplayName("没有雇员：直接返回空结果，不调用 LLM")
    void shouldReturnEmptyWhenNoEmployees() {
        lenient().when(userMapper.selectAllByRole("EMPLOYEE")).thenReturn(List.of());
        client.cannedContent = "{\"rankedUserIds\":[2],\"reason\":\"x\"}";

        RecommendationResult result = client.recommend(List.of("java"));

        assertThat(result.getCandidates()).isEmpty();
        assertThat(result.getReason()).contains("没有雇员");
    }
}
