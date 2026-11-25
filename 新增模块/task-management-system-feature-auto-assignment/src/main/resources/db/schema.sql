-- 任务表（每次启动都会执行，必须幂等）
CREATE TABLE IF NOT EXISTS task
(
    id              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    title           VARCHAR(100) NOT NULL COMMENT '任务标题',
    description     VARCHAR(500) DEFAULT NULL COMMENT '任务描述',
    status          VARCHAR(20)  NOT NULL DEFAULT 'TODO' COMMENT '状态：TODO/IN_PROGRESS/DONE',
    priority        VARCHAR(20)  NOT NULL DEFAULT 'MEDIUM' COMMENT '优先级：LOW/MEDIUM/HIGH',
    due_date        DATETIME     DEFAULT NULL COMMENT '截止时间',
    required_skills VARCHAR(200) DEFAULT NULL COMMENT '所需技能标签，多个用英文逗号分隔，小写：java,python',
    assignee_id     BIGINT       DEFAULT NULL COMMENT '被分配雇员的用户ID，未分配时为 NULL',
    assign_status   VARCHAR(20)  NOT NULL DEFAULT 'UNASSIGNED' COMMENT '分配方式：UNASSIGNED/AUTO/MANUAL',
    publisher_id    BIGINT       DEFAULT NULL COMMENT '发布者（老板）用户ID',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_task_status (status),
    KEY idx_task_priority (priority),
    KEY idx_task_due_date (due_date),
    KEY idx_task_assignee (assignee_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='任务表';

-- 用户表（每次启动都会执行，必须幂等）
CREATE TABLE IF NOT EXISTS `user`
(
    id         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    username   VARCHAR(50)  NOT NULL COMMENT '登录名，唯一',
    password   VARCHAR(100) NOT NULL COMMENT 'BCrypt 密码摘要，不存明文',
    nickname   VARCHAR(50)  DEFAULT NULL COMMENT '显示昵称',
    role       VARCHAR(20)  NOT NULL DEFAULT 'EMPLOYEE' COMMENT '角色：BOSS（发布任务）/ EMPLOYEE（承接任务）',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_username (username)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='用户表';

-- 用户技能标签表（每次启动都会执行，必须幂等）
CREATE TABLE IF NOT EXISTS user_skill
(
    id         BIGINT      NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    user_id    BIGINT      NOT NULL COMMENT '所属用户ID',
    skill_name VARCHAR(50) NOT NULL COMMENT '技能标签，小写：java/python/c++ 等，与标签字典保持一致',
    PRIMARY KEY (id),
    UNIQUE KEY uk_user_skill (user_id, skill_name),
    KEY idx_user_skill_name (skill_name)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='用户技能标签表';

-- 通知表（每次启动都会执行，必须幂等；实体与接口在通知模块实现）
CREATE TABLE IF NOT EXISTS notification
(
    id         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '通知ID',
    user_id    BIGINT       NOT NULL COMMENT '接收者用户ID',
    task_id    BIGINT       DEFAULT NULL COMMENT '关联任务ID，可为空',
    title      VARCHAR(100) NOT NULL COMMENT '通知标题',
    content    VARCHAR(500) DEFAULT NULL COMMENT '通知内容',
    read_flag  TINYINT      NOT NULL DEFAULT 0 COMMENT '是否已读：0 未读 / 1 已读',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_notification_user (user_id, read_flag)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4 COMMENT ='站内通知表';

-- ---------------------------------------------------------------------------
-- 已有库的增量升级（幂等）：给老版本的 task 表补齐自动分配相关列。
-- MySQL 8 不支持 ADD COLUMN IF NOT EXISTS，这里用 INFORMATION_SCHEMA 判断后动态执行。
-- 全新建库时 task 表的 CREATE TABLE 已包含这些列，下面三个块各自等价于空操作。
-- ---------------------------------------------------------------------------
SET @col_exists = (SELECT COUNT(*)
                   FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'task'
                     AND COLUMN_NAME = 'required_skills');
SET @ddl = IF(@col_exists = 0,
              'ALTER TABLE task ADD COLUMN required_skills VARCHAR(200) DEFAULT NULL COMMENT ''所需技能标签，多个用英文逗号分隔，小写：java,python'' AFTER due_date',
              'SELECT 1');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*)
                   FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'task'
                     AND COLUMN_NAME = 'assignee_id');
SET @ddl = IF(@col_exists = 0,
              'ALTER TABLE task ADD COLUMN assignee_id BIGINT DEFAULT NULL COMMENT ''被分配雇员的用户ID，未分配时为 NULL'' AFTER required_skills',
              'SELECT 1');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*)
                   FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'task'
                     AND COLUMN_NAME = 'assign_status');
SET @ddl = IF(@col_exists = 0,
              'ALTER TABLE task ADD COLUMN assign_status VARCHAR(20) NOT NULL DEFAULT ''UNASSIGNED'' COMMENT ''分配方式：UNASSIGNED/AUTO/MANUAL'' AFTER assignee_id',
              'SELECT 1');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*)
                   FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE()
                     AND TABLE_NAME = 'task'
                     AND COLUMN_NAME = 'publisher_id');
SET @ddl = IF(@col_exists = 0,
              'ALTER TABLE task ADD COLUMN publisher_id BIGINT DEFAULT NULL COMMENT ''发布者（老板）用户ID'' AFTER assign_status',
              'SELECT 1');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
