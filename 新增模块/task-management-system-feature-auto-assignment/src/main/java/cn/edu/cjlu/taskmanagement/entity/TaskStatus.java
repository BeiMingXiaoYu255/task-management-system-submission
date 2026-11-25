package cn.edu.cjlu.taskmanagement.entity;

import lombok.Getter;

/**
 * 任务状态。数据库中以枚举名（VARCHAR）存储。
 */
@Getter
public enum TaskStatus {

    /** 待办 */
    TODO("待办"),
    /** 进行中 */
    IN_PROGRESS("进行中"),
    /** 已完成 */
    DONE("已完成");

    private final String label;

    TaskStatus(String label) {
        this.label = label;
    }

    /** 是否为合法的下一个状态（用于将来扩展状态流转校验） */
    public boolean canTransitionTo(TaskStatus target) {
        if (target == null || target == this) {
            return false;
        }
        return switch (this) {
            case TODO -> target == IN_PROGRESS || target == DONE;
            case IN_PROGRESS -> target == DONE;
            case DONE -> target == TODO;
        };
    }
}
