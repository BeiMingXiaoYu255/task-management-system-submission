package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.mapper.NotificationMapper;
import cn.edu.cjlu.taskmanagement.service.NotificationService;
import cn.edu.cjlu.taskmanagement.vo.NotificationVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 通知业务实现：只做查询条件规范化、分页边界与已读归属校验。
 */
@Service
@RequiredArgsConstructor
public class NotificationServiceImpl implements NotificationService {

    private final NotificationMapper notificationMapper;

    @Override
    public PageResult<NotificationVO> page(Long userId, boolean unreadOnly, int page, int size) {
        requireUserId(userId);
        int safePage = Math.max(page, 1);
        int safeSize = Math.min(Math.max(size, 1), 100);
        int offset = (safePage - 1) * safeSize;

        long total = notificationMapper.countByQuery(userId, unreadOnly);
        if (total == 0) {
            return PageResult.of(List.of(), 0L, safePage, safeSize);
        }
        List<NotificationVO> records = notificationMapper
                .selectPage(userId, unreadOnly, offset, safeSize)
                .stream()
                .map(NotificationVO::from)
                .toList();
        return PageResult.of(records, total, safePage, safeSize);
    }

    @Override
    public void markRead(Long id, Long userId) {
        requireUserId(userId);
        if (id == null) {
            throw new BusinessException("通知 ID 不能为空");
        }
        // WHERE 带 user_id，别人的通知改不动；受影响 0 行即视为不存在
        if (notificationMapper.markRead(id, userId) == 0) {
            throw new BusinessException(404, "通知不存在：" + id);
        }
    }

    @Override
    public void markAllRead(Long userId) {
        requireUserId(userId);
        notificationMapper.markAllRead(userId);
    }

    private void requireUserId(Long userId) {
        if (userId == null) {
            throw new BusinessException("用户 ID 不能为空");
        }
    }
}
