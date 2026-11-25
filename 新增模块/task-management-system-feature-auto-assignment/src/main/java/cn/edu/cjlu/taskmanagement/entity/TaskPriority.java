package cn.edu.cjlu.taskmanagement.entity;

import lombok.Getter;

/**
 * 任务优先级。数据库中以枚举名（VARCHAR）存储。
 */
@Getter
public enum TaskPriority {

    /** 低 */
    LOW("低"),
    /** 中 */
    MEDIUM("中"),
    /** 高 */
    HIGH("高");

    private final String label;

    TaskPriority(String label) {
        this.label = label;
    }
}
