-- 示例数据（INSERT IGNORE 保证重复启动不会插入重复行）
INSERT IGNORE INTO task (id, title, description, status, priority, due_date, required_skills, assignee_id, assign_status, publisher_id, created_at, updated_at)
VALUES (1, '完成软件工程课程设计需求分析', '整理功能需求与非功能需求，输出需求规格说明书', 'IN_PROGRESS', 'HIGH',
        '2026-11-10 18:00:00', 'python', NULL, 'UNASSIGNED', 1, NOW(), NOW()),
       (2, '设计数据库表结构', '任务表、用户表初稿，约定字段与索引', 'TODO', 'MEDIUM', '2026-11-15 18:00:00', 'java,mysql', NULL, 'UNASSIGNED', 1, NOW(), NOW()),
       (3, '搭建项目脚手架', 'Spring Boot 3 + Spring MVC + MyBatis + MySQL，前后端分离', 'DONE', 'HIGH',
        '2026-11-03 18:00:00', 'java', NULL, 'UNASSIGNED', 1, NOW(), NOW());

-- 示例用户（密码均为 BCrypt 摘要：boss / boss123，alice|bob|carol / employee123，仅供演示）
INSERT IGNORE INTO `user` (id, username, password, nickname, role, created_at, updated_at)
VALUES (1, 'boss', '$2a$10$TgvEkuHJAEZy19fMhA2pVOsIySCN5Ue1Nm5w73npDbmOtTYm7QeoG', '王老板', 'BOSS', NOW(), NOW()),
       (2, 'alice', '$2a$10$j/yObssHjGf.btOfc2wQs.hjrMbfBmYj/54GU5QX0a6qZ/DrY1iJe', '后端·Alice', 'EMPLOYEE', NOW(), NOW()),
       (3, 'bob', '$2a$10$j/yObssHjGf.btOfc2wQs.hjrMbfBmYj/54GU5QX0a6qZ/DrY1iJe', '前端·Bob', 'EMPLOYEE', NOW(), NOW()),
       (4, 'carol', '$2a$10$j/yObssHjGf.btOfc2wQs.hjrMbfBmYj/54GU5QX0a6qZ/DrY1iJe', '算法·Carol', 'EMPLOYEE', NOW(), NOW());

-- 示例技能标签（与用户表主键对应）
INSERT IGNORE INTO user_skill (user_id, skill_name)
VALUES (2, 'java'), (2, 'python'), (2, 'mysql'),
       (3, 'javascript'), (3, 'css'), (3, 'html'),
       (4, 'python'), (4, 'c++');
