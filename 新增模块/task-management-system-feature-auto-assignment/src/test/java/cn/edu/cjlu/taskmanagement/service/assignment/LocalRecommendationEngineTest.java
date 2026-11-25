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
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * 本地推荐引擎单元测试：验证打分、排除、阈值与排序，不需要数据库。
 */
@ExtendWith(MockitoExtension.class)
class LocalRecommendationEngineTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private TaskAssignmentMapper taskAssignmentMapper;

    private AssignmentProperties properties;
    private LocalRecommendationEngine engine;

    @BeforeEach
    void setUp() {
        properties = new AssignmentProperties();
        engine = new LocalRecommendationEngine(userMapper, taskAssignmentMapper, properties);
    }

    private User employee(long id, String username) {
        User user = new User();
        user.setId(id);
        user.setUsername(username);
        user.setNickname(username + "-nick");
        return user;
    }

    private void mockUser(long id, String username, List<String> skills, long activeTasks) {
        lenient().when(userMapper.selectAllByRole("EMPLOYEE")).thenReturn(List.of(employee(id, username)));
        lenient().when(userMapper.selectSkillNamesByUserId(id)).thenReturn(skills);
        lenient().when(taskAssignmentMapper.countActiveByAssignee(id)).thenReturn(activeTasks);
    }

    @Test
    @DisplayName("打分：命中全部技能、无负载时得满分，命中信息随结果返回")
    void shouldScoreFullMatchWithoutLoad() {
        mockUser(1L, "alice", List.of("java", "python"), 0);

        RecommendationResult result = engine.recommend(List.of("java", "python"));

        assertThat(result.getTopCandidate()).isNotNull();
        assertThat(result.getTopCandidate().getUserId()).isEqualTo(1L);
        assertThat(result.getTopCandidate().getMatchedSkills()).isEqualTo(2);
        assertThat(result.getTopCandidate().getMatchRatio()).isEqualTo(1.0);
        assertThat(result.getTopCandidate().getScore()).isEqualTo(100);
    }

    @Test
    @DisplayName("负载惩罚：技能命中相同时，活跃任务多者得分更低且排后")
    void shouldPenalizeHigherWorkload() {
        lenient().when(userMapper.selectAllByRole("EMPLOYEE"))
                .thenReturn(List.of(employee(1L, "busy"), employee(2L, "idle")));
        lenient().when(userMapper.selectSkillNamesByUserId(anyLong())).thenReturn(List.of("java"));
        lenient().when(taskAssignmentMapper.countActiveByAssignee(1L)).thenReturn(4L);
        lenient().when(taskAssignmentMapper.countActiveByAssignee(2L)).thenReturn(0L);

        RecommendationResult result = engine.recommend(List.of("java"));

        assertThat(result.getCandidates()).hasSize(2);
        assertThat(result.getTopCandidate().getUserId()).isEqualTo(2L);
        assertThat(result.getTopCandidate().getScore()).isEqualTo(100);
        assertThat(result.getCandidates().get(1).getScore()).isEqualTo(100 - 4 * properties.getWorkloadPenalty());
    }

    @Test
    @DisplayName("同分并列：负载少者优先，再按用户ID升序保证稳定")
    void shouldTieBreakByWorkloadThenId() {
        lenient().when(userMapper.selectAllByRole("EMPLOYEE"))
                .thenReturn(List.of(employee(3L, "c"), employee(1L, "a"), employee(2L, "b")));
        lenient().when(userMapper.selectSkillNamesByUserId(anyLong())).thenReturn(List.of("java"));
        lenient().when(taskAssignmentMapper.countActiveByAssignee(anyLong())).thenReturn(0L);

        RecommendationResult result = engine.recommend(List.of("java"));

        assertThat(result.getCandidates())
                .extracting(CandidateScore::getUserId)
                .containsExactly(1L, 2L, 3L);
    }

    @Test
    @DisplayName("零交集排除：技能完全对不上的雇员不进入候选")
    void shouldExcludeNoSkillOverlap() {
        mockUser(1L, "bob", List.of("css", "html"), 0);

        RecommendationResult result = engine.recommend(List.of("java"));

        assertThat(result.getCandidates()).isEmpty();
        assertThat(result.getTopCandidate()).isNull();
        assertThat(result.getReason()).contains("没有雇员达到匹配阈值");
    }

    @Test
    @DisplayName("阈值过滤：得分低于阈值视为无匹配")
    void shouldFilterBelowThreshold() {
        // 命中 1/2 项技能（50 分）且负载 1（-5），得分 45 < 默认阈值 50
        mockUser(1L, "carol", List.of("java"), 1);

        RecommendationResult result = engine.recommend(List.of("java", "python"));

        assertThat(result.getCandidates()).isEmpty();
    }

    @Test
    @DisplayName("无技能要求：所有雇员都是候选人，按负载升序")
    void shouldReturnAllEmployeesWhenNoSkillRequired() {
        lenient().when(userMapper.selectAllByRole("EMPLOYEE"))
                .thenReturn(List.of(employee(1L, "a"), employee(2L, "b")));
        lenient().when(userMapper.selectSkillNamesByUserId(anyLong())).thenReturn(List.of());
        lenient().when(taskAssignmentMapper.countActiveByAssignee(1L)).thenReturn(2L);
        lenient().when(taskAssignmentMapper.countActiveByAssignee(2L)).thenReturn(0L);

        RecommendationResult result = engine.recommend(List.of());

        assertThat(result.getCandidates()).hasSize(2);
        assertThat(result.getTopCandidate().getUserId()).isEqualTo(2L);
    }

    @Test
    @DisplayName("规范化：技能标签统一转小写去重后再参与匹配")
    void shouldNormalizeRequiredSkills() {
        mockUser(1L, "alice", List.of("java"), 0);

        RecommendationResult result = engine.recommend(LocalRecommendationEngine.normalize(List.of("JAVA", " java ")));

        assertThat(result.getTopCandidate().getMatchedSkills()).isEqualTo(1);
        assertThat(result.getTopCandidate().getScore()).isEqualTo(100);
    }
}
