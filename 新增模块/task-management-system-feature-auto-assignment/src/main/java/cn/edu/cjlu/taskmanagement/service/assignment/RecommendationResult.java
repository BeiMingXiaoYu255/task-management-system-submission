package cn.edu.cjlu.taskmanagement.service.assignment;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 一条推荐链路的返回结果：按得分降序的候选人列表 + 首选人选。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecommendationResult {

    /** 产生该结果的链路名：local / llm */
    private String route;

    /** 说明信息（无匹配时给出原因） */
    private String reason;

    /** 按得分降序排列、且都达到阈值的候选人 */
    private List<CandidateScore> candidates;

    /** 首选人选（列表非空时即第一个），无匹配为 null */
    public CandidateScore getTopCandidate() {
        return candidates == null || candidates.isEmpty() ? null : candidates.get(0);
    }

    public static RecommendationResult empty(String route, String reason) {
        return RecommendationResult.builder().route(route).reason(reason).candidates(List.of()).build();
    }
}
