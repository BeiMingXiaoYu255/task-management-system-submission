package cn.edu.cjlu.taskmanagement.service;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.vo.NotificationVO;

/**
 * 通知业务接口：前端轮询拉取与已读管理。
 */
public interface NotificationService {

    /** 分页查询某用户的通知（可只看未读），按时间倒序 */
    PageResult<NotificationVO> page(Long userId, boolean unreadOnly, int page, int size);

    /** 标记单条通知为已读（仅限本人），不存在或非本人通知抛 404 */
    void markRead(Long id, Long userId);

    /** 标记某用户全部通知为已读 */
    void markAllRead(Long userId);
}
