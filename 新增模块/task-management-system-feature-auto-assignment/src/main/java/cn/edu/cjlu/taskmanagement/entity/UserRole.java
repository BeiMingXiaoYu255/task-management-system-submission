package cn.edu.cjlu.taskmanagement.entity;

import lombok.Getter;

/**
 * 用户角色。数据库中以枚举名（VARCHAR）存储。
 */
@Getter
public enum UserRole {

    /** 老板：发布任务，不承接任务 */
    BOSS("老板"),
    /** 雇员：承接任务 */
    EMPLOYEE("雇员");

    private final String label;

    UserRole(String label) {
        this.label = label;
    }
}
