package cn.edu.cjlu.taskmanagement.service.assignment;

/**
 * 任务自动分配业务接口。
 */
public interface AssignmentService {

    /**
     * 对已创建的任务执行一次智能分配：按调度模式选择推荐链路 →
     * 写回任务的分配列 → 生成站内通知（成功：分配者+其余候选；失败：发布者）。
     *
     * @param taskId         任务ID
     * @param taskTitle      任务标题（用于通知文案）
     * @param requiredSkills 所需技能标签，多个用英文逗号分隔，可空
     * @param publisherId    发布者用户ID（无匹配时接收通知）
     */
    AssignmentResult assign(Long taskId, String taskTitle, String requiredSkills, Long publisherId);
}
