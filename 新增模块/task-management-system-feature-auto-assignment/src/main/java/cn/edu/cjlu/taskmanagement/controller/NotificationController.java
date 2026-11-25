package cn.edu.cjlu.taskmanagement.controller;

import cn.edu.cjlu.taskmanagement.common.ApiResponse;
import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.service.NotificationService;
import cn.edu.cjlu.taskmanagement.vo.NotificationVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 通知接口层：前端轮询拉取（userId 标识当前登录用户，与用户模块同一套简化认证约定）。
 */
@RestController
@RequestMapping("/api/notifications")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationService notificationService;

    /** 分页查询：GET /api/notifications?userId=2&unreadOnly=true&page=1&size=10 */
    @GetMapping
    public ApiResponse<PageResult<NotificationVO>> page(
            @RequestParam Long userId,
            @RequestParam(defaultValue = "false") boolean unreadOnly,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.success(notificationService.page(userId, unreadOnly, page, size));
    }

    /** 未读数：GET /api/notifications/unread-count?userId=2（前端角标用） */
    @GetMapping("/unread-count")
    public ApiResponse<Long> unreadCount(@RequestParam Long userId) {
        return ApiResponse.success(
                notificationService.page(userId, true, 1, 1).getTotal());
    }

    /** 标记单条已读：PATCH /api/notifications/{id}/read?userId=2 */
    @PatchMapping("/{id}/read")
    public ApiResponse<Void> markRead(@PathVariable Long id, @RequestParam Long userId) {
        notificationService.markRead(id, userId);
        return ApiResponse.success();
    }

    /** 全部已读：PATCH /api/notifications/read-all?userId=2 */
    @PatchMapping("/read-all")
    public ApiResponse<Void> markAllRead(@RequestParam Long userId) {
        notificationService.markAllRead(userId);
        return ApiResponse.success();
    }
}
