-- 本地开发数据库初始化：创建业务库、测试库与开发账号
CREATE DATABASE IF NOT EXISTS task_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS task_management_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'taskadmin'@'localhost' IDENTIFIED BY 'taskadmin123';
CREATE USER IF NOT EXISTS 'taskadmin'@'127.0.0.1' IDENTIFIED BY 'taskadmin123';

GRANT ALL PRIVILEGES ON task_management.* TO 'taskadmin'@'localhost';
GRANT ALL PRIVILEGES ON task_management.* TO 'taskadmin'@'127.0.0.1';

-- 允许测试使用独立数据库（task_management_test_xxx）以隔离并行开发
GRANT ALL PRIVILEGES ON `task_management_test%`.* TO 'taskadmin'@'localhost';
GRANT ALL PRIVILEGES ON `task_management_test%`.* TO 'taskadmin'@'127.0.0.1';

FLUSH PRIVILEGES;
