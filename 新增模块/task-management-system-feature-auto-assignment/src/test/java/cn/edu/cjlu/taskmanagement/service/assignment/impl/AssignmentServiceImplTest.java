package cn.edu.cjlu.taskmanagement.service.assignment.impl;

import cn.edu.cjlu.taskmanagement.entity.AssignStatus;
import cn.edu.cjlu.taskmanagement.entity.Notification;
import cn.edu.cjlu.taskmanagement.mapper.NotificationMapper;
import cn.edu.cjlu.taskmanagement.mapper.TaskAssignmentMapper;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentProperties;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentResult;
import cn.edu.cjlu.taskmanagement.service.assignment.CandidateScore;
import cn.edu.cjlu.taskmanagement.service.assignment.DispatchMode;
import cn.edu.cjlu.taskmanagement.service.assignment.LocalRecommendationEngine;
import cn.edu.cjlu.taskmanagement.service.assignment.LlmRecommendationClient;
import cn.edu.cjlu.taskmanagement.service.assignment.LlmRouteException;
import cn.edu.cjlu.taskmanagement.service.assignment.RecommendationResult;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 自动分配编排单元测试：覆盖四调度模式、主路失败回退与通知生成，不需要数据库。
 */
@ExtendWith(MockitoExtension.class)
class AssignmentServiceImplTest {

    @Mock
    private LocalRecommendationEngine localEngine;

    @Mock
    private LlmRecommendationClient llmClient;

    @Mock
    private TaskAssignmentMapper taskAssignmentMapper;

    @Mock
    private NotificationMapper notificationMapper;

    private AssignmentProperties properties;
    private AssignmentServiceImpl assignmentService;

    @BeforeEach
    void setUp() {
        properties = new AssignmentProperties();
        assignmentService = new AssignmentServiceImpl(
                localEngine, llmClient, properties, taskAssignmentMapper, notificationMapper);
    }

    private CandidateScore candidate(long userId, String username, long score) {
        return CandidateScore.builder()
                .userId(userId).username(username).nickname(username + "-nick")
                .matchedSkills(1).matchRatio(1.0).activeTasks(0).score(score).build();
    }

    @Test
    @DisplayName("LOCAL_ONLY 匹配成功：写回 AUTO 分配，给首选和其余候选都发通知")
    void localOnlyShouldAssignTopCandidateAndNotifyAll() {
        properties.setDispatchMode(DispatchMode.LOCAL_ONLY);
        when(localEngine.recommend(anyList())).thenReturn(RecommendationResult.builder()
                .route("local")
                .candidates(List.of(candidate(2L, "alice", 100), candidate(3L, "bob", 50)))
                .build());

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "java,python", 1L);

        assertThat(result.isAssigned()).isTrue();
        assertThat(result.getAssigneeId()).isEqualTo(2L);
        assertThat(result.getAssignStatus()).isEqualTo(AssignStatus.AUTO);
        verify(taskAssignmentMapper).updateAssignment(eq(10L), eq("java,python"), eq(2L), eq(AssignStatus.AUTO), any(LocalDateTime.class));
        verify(llmClient, never()).recommend(anyList());

        ArgumentCaptor<List<Notification>> captor = ArgumentCaptor.forClass(List.class);
        verify(notificationMapper).insertBatch(captor.capture());
        List<Notification> notifications = captor.getValue();
        assertThat(notifications).hasSize(2);
        assertThat(notifications.get(0).getUserId()).isEqualTo(2L);
        assertThat(notifications.get(0).getTitle()).isEqualTo("新任务分配通知");
        assertThat(notifications.get(1).getUserId()).isEqualTo(3L);
        assertThat(notifications.get(1).getTitle()).isEqualTo("新任务匹配提醒");
        assertThat(notifications).allSatisfy(n -> {
            assertThat(n.getTaskId()).isEqualTo(10L);
            assertThat(n.getReadFlag()).isZero();
        });
    }

    @Test
    @DisplayName("LOCAL_FIRST：本地有匹配时不调用 LLM")
    void localFirstShouldSkipLlmWhenLocalMatches() {
        properties.setDispatchMode(DispatchMode.LOCAL_FIRST);
        when(localEngine.recommend(anyList()))
                .thenReturn(RecommendationResult.builder().route("local")
                        .candidates(List.of(candidate(2L, "alice", 100))).build());

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "java", 1L);

        assertThat(result.isAssigned()).isTrue();
        assertThat(result.getRoute()).isEqualTo("local");
        verify(llmClient, never()).recommend(anyList());
    }

    @Test
    @DisplayName("LOCAL_FIRST：本地无匹配时回退 LLM，LLM 的人选生效")
    void localFirstShouldFallbackToLlmWhenLocalEmpty() {
        properties.setDispatchMode(DispatchMode.LOCAL_FIRST);
        when(localEngine.recommend(anyList()))
                .thenReturn(RecommendationResult.empty("local", "没有雇员达到匹配阈值"));
        when(llmClient.recommend(anyList()))
                .thenReturn(RecommendationResult.builder().route("llm")
                        .reason("语义相近：carol 会 rust")
                        .candidates(List.of(candidate(4L, "carol", 100))).build());

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "rust", 1L);

        assertThat(result.isAssigned()).isTrue();
        assertThat(result.getAssigneeId()).isEqualTo(4L);
        assertThat(result.getRoute()).isEqualTo("llm");
        assertThat(result.getMessage()).contains("carol");
        verify(taskAssignmentMapper).updateAssignment(eq(10L), eq("rust"), eq(4L), eq(AssignStatus.AUTO), any(LocalDateTime.class));
    }

    @Test
    @DisplayName("LOCAL_FIRST：本地无匹配且 LLM 未配置 → 保持 UNASSIGNED 并通知发布者")
    void localFirstShouldStayUnassignedWhenBothRoutesFail() {
        properties.setDispatchMode(DispatchMode.LOCAL_FIRST);
        when(localEngine.recommend(anyList()))
                .thenReturn(RecommendationResult.empty("local", "没有雇员达到匹配阈值"));
        when(llmClient.recommend(anyList()))
                .thenReturn(RecommendationResult.empty("llm", "LLM API 未配置（需要 llm.base-url、llm.api-key、llm.model）"));

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "cobol", 1L);

        assertThat(result.isAssigned()).isFalse();
        assertThat(result.getAssignStatus()).isEqualTo(AssignStatus.UNASSIGNED);
        verify(taskAssignmentMapper).updateAssignment(eq(10L), eq("cobol"), isNull(), eq(AssignStatus.UNASSIGNED), any(LocalDateTime.class));
        ArgumentCaptor<List<Notification>> captor = ArgumentCaptor.forClass(List.class);
        verify(notificationMapper).insertBatch(captor.capture());
        assertThat(captor.getValue()).hasSize(1);
        assertThat(captor.getValue().get(0).getUserId()).isEqualTo(1L);
        assertThat(captor.getValue().get(0).getTitle()).isEqualTo("任务分配失败提醒");
    }

    @Test
    @DisplayName("LLM_FIRST：LLM 抛异常时回退本地并成功分配")
    void llmFirstShouldFallbackToLocalWhenLlmThrows() {
        properties.setDispatchMode(DispatchMode.LLM_FIRST);
        when(llmClient.recommend(anyList())).thenThrow(new LlmRouteException("调用 LLM 接口失败：connect timeout"));
        when(localEngine.recommend(anyList()))
                .thenReturn(RecommendationResult.builder().route("local")
                        .candidates(List.of(candidate(2L, "alice", 100))).build());

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "java", 1L);

        assertThat(result.isAssigned()).isTrue();
        assertThat(result.getAssigneeId()).isEqualTo(2L);
        assertThat(result.getRoute()).isEqualTo("local");
    }

    @Test
    @DisplayName("LLM_ONLY：LLM 成功时只用 LLM，不调用本地引擎")
    void llmOnlyShouldUseLlmOnly() {
        properties.setDispatchMode(DispatchMode.LLM_ONLY);
        when(llmClient.recommend(anyList()))
                .thenReturn(RecommendationResult.builder().route("llm")
                        .candidates(List.of(candidate(4L, "carol", 100))).build());

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "rust", 1L);

        assertThat(result.isAssigned()).isTrue();
        assertThat(result.getRoute()).isEqualTo("llm");
        verify(localEngine, never()).recommend(anyList());
    }

    @Test
    @DisplayName("LLM_ONLY：LLM 链路不可用 → 按无匹配处理并通知发布者")
    void llmOnlyShouldStayUnassignedWhenLlmUnavailable() {
        properties.setDispatchMode(DispatchMode.LLM_ONLY);
        when(llmClient.recommend(anyList()))
                .thenReturn(RecommendationResult.empty("llm", "LLM API 未配置（需要 llm.base-url、llm.api-key、llm.model）"));

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "java", 1L);

        assertThat(result.isAssigned()).isFalse();
        verify(localEngine, never()).recommend(anyList());
        verify(notificationMapper).insertBatch(anyList());
    }

    @Test
    @DisplayName("无匹配且发布者未知：跳过发布者通知，不抛异常")
    void shouldSkipPublisherNotificationWhenPublisherUnknown() {
        properties.setDispatchMode(DispatchMode.LOCAL_ONLY);
        when(localEngine.recommend(anyList()))
                .thenReturn(RecommendationResult.empty("local", "没有雇员达到匹配阈值"));

        AssignmentResult result = assignmentService.assign(10L, "写推荐引擎", "cobol", null);

        assertThat(result.isAssigned()).isFalse();
        verify(notificationMapper, never()).insertBatch(anyList());
    }
}
