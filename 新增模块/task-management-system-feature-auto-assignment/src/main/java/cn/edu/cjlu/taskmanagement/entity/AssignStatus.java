package cn.edu.cjlu.taskmanagement.entity;

import lombok.Getter;

/**
 * 任务分配方式。数据库中以枚举名（VARCHAR）存储。
 */
@Getter
public enum AssignStatus {

    /** 尚未分配，发布后匹配失败或等待手动指派 */
    UNASSIGNED("未分配"),
    /** 由推荐算法自动分配 */
    AUTO("自动分配"),
    /** 由老板手动指派 */
    MANUAL("手动分配");

    private final String label;

    AssignStatus(String label) {
        this.label = label;
    }
}
