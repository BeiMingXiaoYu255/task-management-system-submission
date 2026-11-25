package cn.edu.cjlu.taskmanagement.vo;

import cn.edu.cjlu.taskmanagement.entity.Notification;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 返回给前端的通知视图对象。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationVO {

    private Long id;
    private Long taskId;
    private String title;
    private String content;
    /** 是否已读 */
    private boolean read;
    private LocalDateTime createdAt;

    public static NotificationVO from(Notification notification) {
        if (notification == null) {
            return null;
        }
        return NotificationVO.builder()
                .id(notification.getId())
                .taskId(notification.getTaskId())
                .title(notification.getTitle())
                .content(notification.getContent())
                .read(notification.getReadFlag() != null && notification.getReadFlag() == 1)
                .createdAt(notification.getCreatedAt())
                .build();
    }
}
