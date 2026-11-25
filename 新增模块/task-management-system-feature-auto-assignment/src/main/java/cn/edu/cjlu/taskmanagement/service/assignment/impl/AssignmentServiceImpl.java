package cn.edu.cjlu.taskmanagement.service.assignment.impl;

import cn.edu.cjlu.taskmanagement.entity.AssignStatus;
import cn.edu.cjlu.taskmanagement.entity.Notification;
import cn.edu.cjlu.taskmanagement.mapper.NotificationMapper;
import cn.edu.cjlu.taskmanagement.mapper.TaskAssignmentMapper;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentProperties;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentResult;
import cn.edu.cjlu.taskmanagement.service.assignment.AssignmentService;
import cn.edu.cjlu.taskmanagement.service.assignment.CandidateScore;
import cn.edu.cjlu.taskmanagement.service.assignment.DispatchMode;
import cn.edu.cjlu.taskmanagement.service.assignment.LocalRecommendationEngine;
import cn.edu.cjlu.taskmanagement.service.assignment.LlmRecommendationClient;
import cn.edu.cjlu.taskmanagement.service.assignment.RecommendationResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * 任务自动分配实现。
 *
 * <p>调度逻辑：按 {@code assignment.dispatch-mode} 在本地/LLM 两条链路间选择。
 * *_FIRST 模式下主路抛异常或没给出候选人时自动回退备用路；两条路都无结果则任务
 * 保持 UNASSIGNED 并通知发布者。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AssignmentServiceImpl implements AssignmentService {

    private final LocalRecommendationEngine localEngine;
    private final LlmRecommendationClient llmClient;
    private final AssignmentProperties properties;
    private final TaskAssignmentMapper taskAssignmentMapper;
    private final NotificationMapper notificationMapper;

    @Override
    @Transactional
    public AssignmentResult assign(Long taskId, String taskTitle, String requiredSkills, Long publisherId) {
        List<String> required = LocalRecommendationEngine.normalize(
                requiredSkills == null ? List.of() : Arrays.asList(requiredSkills.split(",")));

        RecommendationResult result = dispatch(required);
        LocalDateTime now = LocalDateTime.now();

        CandidateScore top = result.getTopCandidate();
        if (top == null) {
            // 无匹配：任务保持 UNASSIGNED，通知发布者手动指派
            taskAssignmentMapper.updateAssignment(taskId, requiredSkills, null, AssignStatus.UNASSIGNED, now);
            notifyPublisherNoMatch(taskId, taskTitle, publisherId, result.getReason());
            log.info("任务 {} 自动分配失败：{}", taskId, result.getReason());
            return AssignmentResult.builder()
                    .taskId(taskId)
                    .assigned(false)
                    .assignStatus(AssignStatus.UNASSIGNED)
                    .route(result.getRoute())
                    .message(result.getReason())
                    .build();
        }

        taskAssignmentMapper.updateAssignment(taskId, requiredSkills, top.getUserId(), AssignStatus.AUTO, now);
        notifyAssignment(taskId, taskTitle, result.getCandidates());
        String message = String.format("已自动分配给 %s（%s），得分 %d：命中 %d/%d 项技能，当前负载 %d 个任务",
                top.getUsername(), top.getNickname(), top.getScore(),
                top.getMatchedSkills(), Math.max(required.size(), top.getMatchedSkills()), top.getActiveTasks());
        log.info("任务 {} 自动分配成功：{}", taskId, message);
        return AssignmentResult.builder()
                .taskId(taskId)
                .assigned(true)
                .assigneeId(top.getUserId())
                .assignStatus(AssignStatus.AUTO)
                .route(result.getRoute())
                .message(message)
                .build();
    }

    /** 按调度模式选择链路；主路无结果或失败时自动回退备用路 */
    private RecommendationResult dispatch(List<String> required) {
        DispatchMode mode = properties.getDispatchMode();
        return switch (mode) {
            case LOCAL_ONLY -> tryRoute(localEngine, required);
            case LLM_ONLY -> tryRoute(llmClient, required);
            case LOCAL_FIRST -> {
                RecommendationResult primary = tryRoute(localEngine, required);
                yield hasCandidates(primary) ? primary : tryRoute(llmClient, required);
            }
            case LLM_FIRST -> {
                RecommendationResult primary = tryRoute(llmClient, required);
                yield hasCandidates(primary) ? primary : tryRoute(localEngine, required);
            }
        };
    }

    /** 调用一条链路；失败不外抛，转成空结果（reason 带原因） */
    private RecommendationResult tryRoute(cn.edu.cjlu.taskmanagement.service.assignment.RecommendationRoute route,
                                          List<String> required) {
        try {
            return route.recommend(required);
        } catch (Exception e) {
            log.warn("推荐链路 {} 失败：{}", route.routeName(), e.getMessage());
            return RecommendationResult.empty(route.routeName(), route.routeName() + " 链路失败：" + e.getMessage());
        }
    }

    private boolean hasCandidates(RecommendationResult result) {
        return result != null && result.getTopCandidate() != null;
    }

    /** 分配成功：给被分配者发"新任务"，给其余候选发"技能匹配提醒" */
    private void notifyAssignment(Long taskId, String taskTitle, List<CandidateScore> candidates) {
        List<Notification> notifications = new ArrayList<>();
        for (int i = 0; i < candidates.size(); i++) {
            CandidateScore candidate = candidates.get(i);
            boolean isTop = i == 0;
            notifications.add(Notification.builder()
                    .userId(candidate.getUserId())
                    .taskId(taskId)
                    .title(isTop ? "新任务分配通知" : "新任务匹配提醒")
                    .content(isTop
                            ? String.format("任务「%s」已自动分配给你（匹配得分 %d），请及时处理。", taskTitle, candidate.getScore())
                            : String.format("新任务「%s」与你的技能匹配（得分 %d），如需承接请联系任务发布者。", taskTitle, candidate.getScore()))
                    .readFlag(0)
                    .createdAt(LocalDateTime.now())
                    .build());
        }
        notificationMapper.insertBatch(notifications);
    }

    /** 无匹配：通知发布者手动指派 */
    private void notifyPublisherNoMatch(Long taskId, String taskTitle, Long publisherId, String reason) {
        if (publisherId == null) {
            return;
        }
        notificationMapper.insertBatch(List.of(Notification.builder()
                .userId(publisherId)
                .taskId(taskId)
                .title("任务分配失败提醒")
                .content(String.format("任务「%s」未找到符合条件的雇员（%s），请手动指派或调整技能要求。", taskTitle, reason))
                .readFlag(0)
                .createdAt(LocalDateTime.now())
                .build()));
    }
}
