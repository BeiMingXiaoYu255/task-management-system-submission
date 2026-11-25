package cn.edu.cjlu.taskmanagement.service.assignment;

import java.util.List;

/**
 * 推荐链路统一接口：本地规则引擎与 LLM 客户端都实现它，
 * 调度层按 {@link DispatchMode} 在多条链路之间选择与回退。
 */
public interface RecommendationRoute {

    /** 链路名：local / llm */
    String routeName();

    /**
     * 对给定所需技能返回候选人排序。
     *
     * @param requiredSkills 所需技能标签（已规范化为小写），空列表表示无技能要求
     */
    RecommendationResult recommend(List<String> requiredSkills);
}
