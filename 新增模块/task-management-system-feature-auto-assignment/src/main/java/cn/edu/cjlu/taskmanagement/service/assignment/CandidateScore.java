package cn.edu.cjlu.taskmanagement.service.assignment;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 候选雇员的打分明细。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CandidateScore {

    /** 候选人用户ID */
    private Long userId;

    /** 用户名 */
    private String username;

    /** 昵称 */
    private String nickname;

    /** 命中的技能标签数 */
    private int matchedSkills;

    /** 技能命中率：命中数 / 所需技能数（无技能要求时为 1.0） */
    private double matchRatio;

    /** 当前名下未完成任务数 */
    private int activeTasks;

    /** 综合得分 = 命中率 × 100 − 活跃任务数 × 负载惩罚 */
    private long score;
}
