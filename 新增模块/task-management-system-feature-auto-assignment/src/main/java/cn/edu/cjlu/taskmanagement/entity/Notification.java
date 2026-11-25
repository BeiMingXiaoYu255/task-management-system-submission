package cn.edu.cjlu.taskmanagement.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 站内通知实体，对应数据库表 {@code notification}。
 *
 * <p>自动分配成功后写给被分配者与其他候选雇员；无匹配时写给发布任务的老板。</p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Notification {

    /** 主键，自增 */
    private Long id;

    /** 接收者用户ID */
    private Long userId;

    /** 关联任务ID，可为空 */
    private Long taskId;

    /** 通知标题 */
    private String title;

    /** 通知内容 */
    private String content;

    /** 是否已读：0 未读 / 1 已读 */
    private Integer readFlag;

    /** 创建时间 */
    private LocalDateTime createdAt;
}
