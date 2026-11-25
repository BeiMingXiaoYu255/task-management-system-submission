package cn.edu.cjlu.taskmanagement.service.assignment;

import cn.edu.cjlu.taskmanagement.entity.AssignStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 一次自动分配的结果。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AssignmentResult {

    /** 任务ID */
    private Long taskId;

    /** 是否成功分配到人选 */
    private boolean assigned;

    /** 被分配者用户ID，未分配为 null */
    private Long assigneeId;

    /** 落库后的分配方式：AUTO / UNASSIGNED */
    private AssignStatus assignStatus;

    /** 使用的链路名 */
    private String route;

    /** 结果说明（分配理由 / 无匹配原因） */
    private String message;
}
