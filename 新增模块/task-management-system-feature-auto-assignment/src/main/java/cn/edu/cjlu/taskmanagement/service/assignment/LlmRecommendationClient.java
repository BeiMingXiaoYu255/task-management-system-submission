package cn.edu.cjlu.taskmanagement.service.assignment;

import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.TaskAssignmentMapper;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * LLM 推荐链路（第二路，备用）。
 *
 * <p>定位：本地链路失效，或新任务在本地规则下没有任何人达到匹配阈值时，
 * 由大语言模型对候选雇员做语义排序兜底。按 OpenAI 兼容协议调用，
 * {@code llm.*} 配置齐全才启用；配置缺失、调用失败、返回不可解析时抛出
 * {@link LlmRouteException}，由调度层决定回退行为。</p>
 *
 * <p>与本地链路不同，LLM 允许推荐与所需技能零交集的候选人（语义相近也算），
 * 候选人的 {@code score} 字段在此链路下表示排名分（第一名 100，依次递减 10）。</p>
 */
@Slf4j
@Component
public class LlmRecommendationClient implements RecommendationRoute {

    private static final String SYSTEM_PROMPT = """
            你是任务管理系统的分配助手。根据任务所需技能与候选雇员的技能标签、当前负载，\
            选出最合适的雇员并按合适程度排序。允许推荐技能标签不完全匹配但语义相近的候选人。\
            必须只输出一个 JSON 对象，不要输出任何其他文字，格式：\
            {"rankedUserIds":[按合适程度降序排列的候选人ID],"reason":"50字以内的理由"}""";

    private final LlmProperties properties;
    private final UserMapper userMapper;
    private final TaskAssignmentMapper taskAssignmentMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final RestClient restClient;

    public LlmRecommendationClient(LlmProperties properties,
                                   UserMapper userMapper,
                                   TaskAssignmentMapper taskAssignmentMapper) {
        this.properties = properties;
        this.userMapper = userMapper;
        this.taskAssignmentMapper = taskAssignmentMapper;
        this.restClient = buildRestClient(properties.getTimeoutSeconds());
    }

    @Override
    public String routeName() {
        return "llm";
    }

    @Override
    public RecommendationResult recommend(List<String> requiredSkills) {
        if (!properties.isConfigured()) {
            return RecommendationResult.empty(routeName(),
                    "LLM API 未配置（需要 llm.base-url、llm.api-key、llm.model）");
        }

        List<String> required = LocalRecommendationEngine.normalize(requiredSkills);
        List<User> employees = userMapper.selectAllByRole(UserRole.EMPLOYEE.name());
        if (employees.isEmpty()) {
            return RecommendationResult.empty(routeName(), "系统中没有雇员级用户");
        }

        // 组装候选人花名册：技能标签 + 当前负载
        Map<Long, List<String>> skillsMap = new LinkedHashMap<>();
        Map<Long, Integer> activeMap = new LinkedHashMap<>();
        for (User employee : employees) {
            skillsMap.put(employee.getId(), userMapper.selectSkillNamesByUserId(employee.getId()));
            activeMap.put(employee.getId(), (int) taskAssignmentMapper.countActiveByAssignee(employee.getId()));
        }

        String content;
        try {
            content = postForChatCompletion(SYSTEM_PROMPT, buildUserPrompt(required, employees, skillsMap, activeMap));
        } catch (LlmRouteException e) {
            throw e;
        } catch (Exception e) {
            // 契约：本链路对外只抛 LlmRouteException，保证调度层能统一回退
            throw new LlmRouteException("调用 LLM 接口失败：" + e.getMessage(), e);
        }
        return parseRanked(content, employees, skillsMap, activeMap, required);
    }

    /** 把 LLM 返回的文本解析成排序候选人；解析不出有效 JSON 或没有有效人选时抛异常/返回空 */
    RecommendationResult parseRanked(String content,
                                     List<User> employees,
                                     Map<Long, List<String>> skillsMap,
                                     Map<Long, Integer> activeMap,
                                     List<String> required) {
        JsonNode root = readJson(content);
        JsonNode rankedNode = root.path("rankedUserIds");
        if (!rankedNode.isArray() || rankedNode.isEmpty()) {
            return RecommendationResult.empty(routeName(), "LLM 未给出有效人选排序");
        }
        String reason = root.path("reason").asText("");

        Map<Long, User> employeeMap = new LinkedHashMap<>();
        employees.forEach(user -> employeeMap.put(user.getId(), user));

        List<CandidateScore> candidates = new ArrayList<>();
        int rank = 0;
        for (JsonNode idNode : rankedNode) {
            Long userId = idNode.canConvertToLong() ? idNode.asLong() : null;
            User employee = userId == null ? null : employeeMap.get(userId);
            if (employee == null) {
                continue; // 忽略 LLM 幻觉出的不存在 ID
            }
            rank++;
            List<String> skills = skillsMap.getOrDefault(userId, List.of());
            long matched = required.stream().filter(skills::contains).count();
            candidates.add(CandidateScore.builder()
                    .userId(userId)
                    .username(employee.getUsername())
                    .nickname(employee.getNickname())
                    .matchedSkills((int) matched)
                    .matchRatio(required.isEmpty() ? 1.0 : (double) matched / required.size())
                    .activeTasks(activeMap.getOrDefault(userId, 0))
                    .score(100L - (long) (rank - 1) * 10)
                    .build());
            if (rank >= properties.getMaxCandidates()) {
                break;
            }
        }
        if (candidates.isEmpty()) {
            return RecommendationResult.empty(routeName(), "LLM 返回的候选人 ID 均无效");
        }
        return RecommendationResult.builder()
                .route(routeName())
                .reason(reason.isBlank() ? "LLM 语义排序" : reason)
                .candidates(candidates)
                .build();
    }

    /** 从可能带 markdown 代码块的内容里提取 JSON 对象 */
    private JsonNode readJson(String content) {
        try {
            return objectMapper.readTree(content.trim());
        } catch (Exception directFailure) {
            int start = content.indexOf('{');
            int end = content.lastIndexOf('}');
            if (start >= 0 && end > start) {
                try {
                    return objectMapper.readTree(content.substring(start, end + 1));
                } catch (Exception ignored) {
                    // 落到下面的统一异常
                }
            }
            throw new LlmRouteException("LLM 返回内容不是合法 JSON：" + abbreviate(content));
        }
    }

    /** 调用 OpenAI 兼容对话接口，返回 message.content；包内可重写以便单测 */
    String postForChatCompletion(String systemPrompt, String userPrompt) {
        Map<String, Object> body = Map.of(
                "model", properties.getModel(),
                "temperature", 0.2,
                "messages", List.of(
                        Map.of("role", "system", "content", systemPrompt),
                        Map.of("role", "user", "content", userPrompt)));
        try {
            String response = restClient.post()
                    .uri(properties.getBaseUrl() + properties.getChatPath())
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getApiKey())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(String.class);
            String content = objectMapper.readTree(response == null ? "" : response)
                    .path("choices").path(0).path("message").path("content").asText("");
            if (content.isBlank()) {
                throw new LlmRouteException("LLM 返回的 message.content 为空");
            }
            log.debug("LLM 返回：{}", abbreviate(content));
            return content;
        } catch (LlmRouteException e) {
            throw e;
        } catch (Exception e) {
            throw new LlmRouteException("调用 LLM 接口失败：" + e.getMessage(), e);
        }
    }

    private String buildUserPrompt(List<String> required,
                                   List<User> employees,
                                   Map<Long, List<String>> skillsMap,
                                   Map<Long, Integer> activeMap) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("任务所需技能标签：").append(required.isEmpty() ? "（无明确要求）" : String.join(", ", required)).append('\n');
        prompt.append("候选雇员（ID | 用户名 | 技能标签 | 当前未完成任务数）：\n");
        for (User employee : employees) {
            prompt.append(employee.getId()).append(" | ").append(employee.getUsername()).append(" | ")
                    .append(String.join(",", skillsMap.getOrDefault(employee.getId(), List.of())))
                    .append(" | ").append(activeMap.getOrDefault(employee.getId(), 0)).append('\n');
        }
        prompt.append("请输出 JSON。");
        return prompt.toString();
    }

    private static RestClient buildRestClient(int timeoutSeconds) {
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(10));
        factory.setReadTimeout(Duration.ofSeconds(Math.max(timeoutSeconds, 1)));
        return RestClient.builder().requestFactory(factory).build();
    }

    private static String abbreviate(String text) {
        if (text == null) {
            return "";
        }
        return text.length() <= 120 ? text : text.substring(0, 120) + "...";
    }
}
