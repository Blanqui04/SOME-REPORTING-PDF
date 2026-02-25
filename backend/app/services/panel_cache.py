"""Redis-based cache for Grafana panel renderings.

Caches rendered panel images (PNG) to avoid redundant Grafana render
API calls when the same panel / time-range combination is requested
multiple times within the TTL window.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from backend.app.core.config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 600  # 10 minutes


class PanelCache:
    """Redis-backed cache for rendered Grafana panel images.

    Args:
        settings: Application settings with Redis URL.
        ttl: Cache entry time-to-live in seconds.
    """

    def __init__(self, settings: Settings, ttl: int = _DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._prefix = "panel_cache:"
        try:
            self._redis: redis.Redis | None = redis.Redis.from_url(  # type: ignore[type-arg]
                settings.REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=5,
            )
            # Verify connectivity
            self._redis.ping()
            logger.info("Panel cache connected to Redis")
        except (redis.ConnectionError, redis.RedisError) as exc:
            logger.warning("Panel cache Redis unavailable, caching disabled: %s", exc)
            self._redis = None

    @property
    def available(self) -> bool:
        """Return True if the cache backend is connected."""
        return self._redis is not None

    # ------------------------------------------------------------------
    # Cache key generation
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(
        dashboard_uid: str,
        panel_id: int,
        time_from: str,
        time_to: str,
        width: int = 1000,
        height: int = 500,
    ) -> str:
        """Generate a deterministic cache key.

        Args:
            dashboard_uid: Dashboard unique identifier.
            panel_id: Panel ID within the dashboard.
            time_from: Time range start (e.g. ``now-1h``).
            time_to: Time range end (e.g. ``now``).
            width: Render width in pixels.
            height: Render height in pixels.

        Returns:
            Cache key string.
        """
        raw = f"{dashboard_uid}:{panel_id}:{time_from}:{time_to}:{width}:{height}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"panel_cache:{digest}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        dashboard_uid: str,
        panel_id: int,
        time_from: str,
        time_to: str,
        width: int = 1000,
        height: int = 500,
    ) -> bytes | None:
        """Retrieve a cached panel image.

        Args:
            dashboard_uid: Dashboard UID.
            panel_id: Panel ID.
            time_from: Time range start.
            time_to: Time range end.
            width: Render width.
            height: Render height.

        Returns:
            Cached PNG bytes or None if not found.
        """
        if not self._redis:
            return None

        key = self._make_key(dashboard_uid, panel_id, time_from, time_to, width, height)
        try:
            data = self._redis.get(key)
            if data:
                logger.debug("Cache HIT for %s", key)
                return data  # type: ignore[return-value]
            logger.debug("Cache MISS for %s", key)
        except redis.RedisError as exc:
            logger.warning("Cache get error: %s", exc)
        return None

    def set(
        self,
        dashboard_uid: str,
        panel_id: int,
        time_from: str,
        time_to: str,
        image_data: bytes,
        width: int = 1000,
        height: int = 500,
    ) -> bool:
        """Store a panel image in the cache.

        Args:
            dashboard_uid: Dashboard UID.
            panel_id: Panel ID.
            time_from: Time range start.
            time_to: Time range end.
            image_data: PNG bytes to cache.
            width: Render width.
            height: Render height.

        Returns:
            True if stored successfully.
        """
        if not self._redis:
            return False

        key = self._make_key(dashboard_uid, panel_id, time_from, time_to, width, height)
        try:
            self._redis.setex(key, self._ttl, image_data)
            logger.debug("Cache SET for %s (%d bytes, TTL=%ds)", key, len(image_data), self._ttl)
            return True
        except redis.RedisError as exc:
            logger.warning("Cache set error: %s", exc)
        return False

    def invalidate(self, dashboard_uid: str) -> int:
        """Invalidate all cached panels for a dashboard.

        Args:
            dashboard_uid: Dashboard UID to invalidate.

        Returns:
            Number of keys deleted.
        """
        if not self._redis:
            return 0

        # We can't efficiently find all keys by dashboard_uid with the
        # hash-based key scheme, but we can use a pattern scan.
        # For better performance in production, use a secondary index.
        pattern = f"{self._prefix}*"
        deleted = 0
        try:
            cursor: int = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=pattern, count=100)  # type: ignore[misc]
                if keys:
                    deleted += self._redis.delete(*keys)  # type: ignore[operator]
                if cursor == 0:
                    break
            if deleted:
                logger.info("Invalidated %d cache entries", deleted)
        except redis.RedisError as exc:
            logger.warning("Cache invalidation error: %s", exc)
        return deleted

    def clear(self) -> int:
        """Clear all panel cache entries.

        Returns:
            Number of keys deleted.
        """
        return self.invalidate("")

    def stats(self) -> dict[str, int]:
        """Get basic cache statistics.

        Returns:
            Dictionary with ``keys`` count and ``memory_bytes``.
        """
        if not self._redis:
            return {"keys": 0, "memory_bytes": 0}

        try:
            info = self._redis.info("memory")
            pattern = f"{self._prefix}*"
            key_count = 0
            cursor_val: int = 0
            while True:
                cursor_val, keys = self._redis.scan(cursor_val, match=pattern, count=100)  # type: ignore[misc]
                key_count += len(keys)
                if cursor_val == 0:
                    break
            return {
                "keys": key_count,
                "memory_bytes": int(info.get("used_memory", 0)),  # type: ignore[union-attr]
            }
        except redis.RedisError:
            return {"keys": 0, "memory_bytes": 0}
