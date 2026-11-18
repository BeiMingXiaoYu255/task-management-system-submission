#!/usr/bin/env bash
# Linux/macOS 系统运行时初始化：创建业务数据库、账号并给出 Redis 配置建议。
#
# 使用方法：
#   sudo bash packaging/setupSystemRuntime.sh
#   （可选）MYSQL_PORT=3307 sudo -E bash packaging/setupSystemRuntime.sh
#
# 说明：
#   1. 需要系统已安装并启动 MariaDB/MySQL（Ubuntu: sudo apt-get install -y mariadb-server）；
#   2. 脚本创建库 task_management（utf8mb4）与账号 taskadmin/taskadmin123（仅本机访问），
#      与桌面应用的约定一致；生产环境请自行修改密码并同步配置 TASK_MANAGEMENT_DATABASE_URL；
#   3. Redis 只需系统已启动 redis-server（默认 6379 或手动改为 6380），应用会自动探测。

set -euo pipefail

MYSQL_PORT="${MYSQL_PORT:-3307}"
MYSQL_ROOT_USER="${MYSQL_ROOT_USER:-root}"

if ! command -v mysql >/dev/null 2>&1; then
  echo "错误：未找到 mysql 客户端，请先安装 MariaDB/MySQL（Ubuntu: sudo apt-get install -y mariadb-server）" >&2
  exit 1
fi

echo "正在初始化数据库（端口 ${MYSQL_PORT}，账号 taskadmin）..."
mysql -h 127.0.0.1 -P "${MYSQL_PORT}" -u "${MYSQL_ROOT_USER}" <<'SQL'
CREATE DATABASE IF NOT EXISTS task_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'taskadmin'@'127.0.0.1' IDENTIFIED BY 'taskadmin123';
CREATE USER IF NOT EXISTS 'taskadmin'@'localhost' IDENTIFIED BY 'taskadmin123';
ALTER USER 'taskadmin'@'127.0.0.1' IDENTIFIED BY 'taskadmin123';
ALTER USER 'taskadmin'@'localhost' IDENTIFIED BY 'taskadmin123';
GRANT ALL PRIVILEGES ON task_management.* TO 'taskadmin'@'127.0.0.1';
GRANT ALL PRIVILEGES ON task_management.* TO 'taskadmin'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "数据库初始化完成：task_management / taskadmin@127.0.0.1:${MYSQL_PORT}"
if command -v redis-cli >/dev/null 2>&1; then
  if redis-cli -p 6380 ping >/dev/null 2>&1; then
    echo "Redis 就绪：127.0.0.1:6380"
  elif redis-cli -p 6379 ping >/dev/null 2>&1; then
    echo "Redis 就绪：127.0.0.1:6379（应用会自动探测该端口）"
  else
    echo "提示：未检测到运行中的 Redis，应用会降级为内存缓存（如需完整功能请启动 redis-server）"
  fi
else
  echo "提示：未安装 redis-cli，跳过 Redis 检测"
fi
