package cn.edu.cjlu.taskmanagement.service.assignment;

import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.TaskAssignmentMapper;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * 本地规则推荐引擎（第一路）。
 *
 * <p>打分公式：{@code 得分 = 技能命中率 × 100 − 活跃任务数 × 负载惩罚}。</p>
 * <ul>
 *   <li>技能命中率 = 命中的所需技能数 / 所需技能总数；无技能要求时视为 1.0；</li>
 *   <li>与所需技能零交集的候选人直接排除；</li>
 *   <li>得分低于 {@code assignment.match-threshold} 的候选人视为无匹配；</li>
 *   <li>同分排序：活跃任务少者优先，再按用户ID升序保证结果稳定。</li>
 * </ul>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class LocalRecommendationEngine implements RecommendationRoute {

    private final UserMapper userMapper;
    private final TaskAssignmentMapper taskAssignmentMapper;
    private final AssignmentProperties properties;

    @Override
    public String routeName() {
        return "local";
    }

    @Override
    public RecommendationResult recommend(List<String> requiredSkills) {
        List<String> required = normalize(requiredSkills);
        List<User> employees = userMapper.selectAllByRole(UserRole.EMPLOYEE.name());

        List<CandidateScore> candidates = new ArrayList<>();
        for (User employee : employees) {
            CandidateScore score = score(employee, required);
            if (score != null) {
                candidates.add(score);
            }
        }

        // 得分降序 → 负载升序 → 用户ID升序（稳定、可复现）
        candidates.sort((a, b) -> {
            if (a.getScore() != b.getScore()) {
                return Long.compare(b.getScore(), a.getScore());
            }
            if (a.getActiveTasks() != b.getActiveTasks()) {
                return Integer.compare(a.getActiveTasks(), b.getActiveTasks());
            }
            return Long.compare(a.getUserId(), b.getUserId());
        });

        log.debug("本地推荐：所需技能={}，候选 {} 人", required, candidates.size());
        return RecommendationResult.builder()
                .route(routeName())
                .reason(candidates.isEmpty() ? "没有雇员达到匹配阈值" : "按技能命中率与负载打分")
                .candidates(candidates)
                .build();
    }

    /** 给单个候选人打分；不合格返回 null */
    private CandidateScore score(User employee, List<String> required) {
        List<String> skills = userMapper.selectSkillNamesByUserId(employee.getId());
        long matched = required.stream().filter(skills::contains).count();
        if (!required.isEmpty() && matched == 0) {
            return null; // 与所需技能零交集，直接排除
        }
        double ratio = required.isEmpty() ? 1.0 : (double) matched / required.size();
        int activeTasks = (int) taskAssignmentMapper.countActiveByAssignee(employee.getId());
        long score = Math.round(ratio * 100) - (long) activeTasks * properties.getWorkloadPenalty();
        if (score < properties.getMatchThreshold()) {
            return null; // 低于阈值视为无匹配
        }
        return CandidateScore.builder()
                .userId(employee.getId())
                .username(employee.getUsername())
                .nickname(employee.getNickname())
                .matchedSkills((int) matched)
                .matchRatio(ratio)
                .activeTasks(activeTasks)
                .score(score)
                .build();
    }

    /** 技能标签统一转小写、去空白、去重，保持顺序 */
    public static List<String> normalize(List<String> skills) {
        if (skills == null || skills.isEmpty()) {
            return List.of();
        }
        return skills.stream()
                .filter(s -> s != null && !s.isBlank())
                .map(s -> s.trim().toLowerCase(Locale.ROOT))
                .distinct()
                .toList();
    }
}
