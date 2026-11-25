package cn.edu.cjlu.taskmanagement.mapper;

import cn.edu.cjlu.taskmanagement.entity.Notification;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 通知表持久层：分配流程写入（insertBatch），通知模块负责查询与已读。
 */
public interface NotificationMapper {

    /** 批量插入通知（自动分配流程调用） */
    int insertBatch(@Param("notifications") List<Notification> notifications);

    /** 统计某用户满足条件的通知总数 */
    long countByQuery(@Param("userId") Long userId,
                      @Param("unreadOnly") boolean unreadOnly);

    /** 分页查询某用户的通知，按时间倒序 */
    List<Notification> selectPage(@Param("userId") Long userId,
                                  @Param("unreadOnly") boolean unreadOnly,
                                  @Param("offset") int offset,
                                  @Param("size") int size);

    /** 标记单条通知为已读（仅限本人），返回受影响行数 */
    int markRead(@Param("id") Long id,
                 @Param("userId") Long userId);

    /** 标记某用户全部通知为已读 */
    int markAllRead(@Param("userId") Long userId);
}
