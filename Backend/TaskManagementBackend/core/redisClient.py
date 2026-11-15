"""缓存客户端：优先 Redis，不可用时降级为进程内内存缓存。

设计说明：
    1. 生产/团队模式使用 Redis，用于登录限流、token 黑名单、仪表盘缓存；
    2. 单机或测试环境若 Redis 不可用，自动降级内存实现，保证系统仍可运行；
    3. 对外统一暴露 get/set/delete/exists/increment/expire 等简单方法。
"""

import threading
import time

from TaskManagementBackend.config.settings import settings


class MemoryCacheClient:
    """进程内缓存实现：字典 + 过期时间戳，线程安全。"""

    def __init__(self) -> None:
        """初始化空缓存与互斥锁。"""
        self._storage: dict[str, tuple[object, float | None]] = {}
        self._lock = threading.Lock()

    def _purgeExpired(self, key: str) -> None:
        """内部方法：若键已过期则删除（调用方需持有锁）。"""
        item = self._storage.get(key)
        if item is not None and item[1] is not None and item[1] <= time.time():
            self._storage.pop(key, None)

    def get(self, key: str) -> str | None:
        """读取字符串值，不存在或过期返回 None。"""
        with self._lock:
            self._purgeExpired(key)
            item = self._storage.get(key)
            return None if item is None else str(item[0])

    def set(self, key: str, value: object, expireSeconds: int | None = None) -> None:
        """写入字符串值，可选过期秒数。"""
        with self._lock:
            deadline = None if expireSeconds is None else time.time() + expireSeconds
            self._storage[key] = (str(value), deadline)

    def delete(self, key: str) -> None:
        """删除键。"""
        with self._lock:
            self._storage.pop(key, None)

    def exists(self, key: str) -> bool:
        """判断键是否存在且未过期。"""
        with self._lock:
            self._purgeExpired(key)
            return key in self._storage

    def increment(self, key: str, expireSeconds: int | None = None) -> int:
        """自增计数：键不存在时从 1 开始，可设置过期时间。"""
        with self._lock:
            self._purgeExpired(key)
            item = self._storage.get(key)
            if item is None:
                count, deadline = 1, (
                    None if expireSeconds is None else time.time() + expireSeconds
                )
            else:
                count = int(item[0]) + 1
                deadline = item[1]
            self._storage[key] = (count, deadline)
            return count

    def expire(self, key: str, expireSeconds: int) -> None:
        """为已有键设置过期时间。"""
        with self._lock:
            item = self._storage.get(key)
            if item is not None:
                self._storage[key] = (item[0], time.time() + expireSeconds)

    def flushNamespace(self, prefix: str) -> None:
        """按前缀清空键（测试与运维使用）。"""
        with self._lock:
            for key in [item for item in self._storage if item.startswith(prefix)]:
                self._storage.pop(key, None)

    def ping(self) -> bool:
        """健康检查：内存实现始终可用。"""
        return True

    def close(self) -> None:
        """释放资源：内存实现无需处理。"""
        self._storage.clear()


class CacheClient:
    """统一缓存客户端：初始化时探测 Redis，失败则降级为内存缓存。"""

    def __init__(self) -> None:
        """连接 Redis；不可用时使用内存实现。"""
        self._memory = MemoryCacheClient()
        self._redis = None
        self.mode = "memory"
        self._connect()

    def _connect(self) -> None:
        """尝试建立 Redis 连接并执行 ping 探测。"""
        try:
            import redis

            candidate = redis.Redis.from_url(
                settings.redisUrl,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=2,
            )
            candidate.ping()
            self._redis = candidate
            self.mode = "redis"
        except Exception:
            self._redis = None
            self.mode = "memory"

    def get(self, key: str) -> str | None:
        """读取字符串值。"""
        if self._redis is not None:
            return self._redis.get(key)
        return self._memory.get(key)

    def set(self, key: str, value: object, expireSeconds: int | None = None) -> None:
        """写入字符串值，可选过期秒数。"""
        if self._redis is not None:
            if expireSeconds is None:
                self._redis.set(key, str(value))
            else:
                self._redis.set(key, str(value), ex=expireSeconds)
            return
        self._memory.set(key, value, expireSeconds)

    def delete(self, key: str) -> None:
        """删除键。"""
        if self._redis is not None:
            self._redis.delete(key)
            return
        self._memory.delete(key)

    def exists(self, key: str) -> bool:
        """判断键是否存在。"""
        if self._redis is not None:
            return bool(self._redis.exists(key))
        return self._memory.exists(key)

    def increment(self, key: str, expireSeconds: int | None = None) -> int:
        """原子自增计数。"""
        if self._redis is not None:
            count = int(self._redis.incr(key))
            if expireSeconds is not None and count == 1:
                self._redis.expire(key, expireSeconds)
            return count
        return self._memory.increment(key, expireSeconds)

    def expire(self, key: str, expireSeconds: int) -> None:
        """设置键过期时间。"""
        if self._redis is not None:
            self._redis.expire(key, expireSeconds)
            return
        self._memory.expire(key, expireSeconds)

    def flushNamespace(self, prefix: str) -> None:
        """按前缀批量删除键。

        Redis 模式使用 scan 迭代避免阻塞；内存模式直接遍历。
        """
        if self._redis is not None:
            for key in self._redis.scan_iter(match=f"{prefix}*", count=200):
                self._redis.delete(key)
            return
        self._memory.flushNamespace(prefix)

    def ping(self) -> bool:
        """健康检查：Redis 不通时返回内存实现的状态。"""
        if self._redis is not None:
            try:
                return bool(self._redis.ping())
            except Exception:
                return False
        return self._memory.ping()

    def close(self) -> None:
        """关闭 Redis 连接。"""
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass


# 全局缓存单例
cacheClient = CacheClient()
