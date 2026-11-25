package cn.edu.cjlu.taskmanagement.service.assignment;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 智能分配配置项，对应 application.yml 的 {@code assignment.*}。
 */
@Data
@Component
@ConfigurationProperties(prefix = "assignment")
public class AssignmentProperties {

    /** 调度模式，默认只走本地链路（LLM 在后续版本接入） */
    private DispatchMode dispatchMode = DispatchMode.LOCAL_ONLY;

    /**
     * 本地匹配阈值：候选人得分低于该值视为无匹配。
     * 得分 = 技能命中率 × 100 − 活跃任务数 × workloadPenalty，因此阈值 50
     * 大致要求"至少命中一半技能且负载不高"。
     */
    private int matchThreshold = 50;

    /** 每个活跃任务的负载惩罚分 */
    private int workloadPenalty = 5;
}
