"""API key pool + rotation for rate-limit resilience.

Manages multiple API keys per service so the bot can transparently rotate
through them when one gets rate-limited or exhausts its free-tier quota.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


# Tokens in an exception string that indicate a rate-limit / quota error.
_RATE_LIMIT_MARKERS = ("429", "quota", "exhausted", "rate limit")


class APIKeyPool:
    """Pool of API keys with round-robin rotation and exhaustion tracking."""

    def __init__(self, service: str, env_prefix: str):
        """
        Args:
            service: Human-readable service name (for logging).
            env_prefix: Env var base name. Keys are loaded from
                ``{PREFIX}``, ``{PREFIX}_2``, ``{PREFIX}_3``, ... and also
                from comma-separated ``{PREFIX}S`` (e.g. ``GEMINI_API_KEYS``).
        """
        self.service = service
        self.env_prefix = env_prefix
        self.keys: list[str] = self._load_keys(env_prefix)
        self.index: int = 0
        # key -> datetime (UTC) until which it's considered exhausted.
        # None means "exhausted indefinitely" (until process restart).
        self.exhausted: dict[str, datetime | None] = {}

        if self.keys:
            logger.info(f"[POOL] {service}: loaded {len(self.keys)} key(s)")
        else:
            logger.warning(f"[POOL] {service}: no keys found for prefix {env_prefix}")

    @staticmethod
    def _load_keys(env_prefix: str) -> list[str]:
        """Collect keys from env. Dedupes while preserving order."""
        found: list[str] = []

        # Primary key + numbered variants: PREFIX, PREFIX_2, PREFIX_3, ...
        primary = os.environ.get(env_prefix)
        if primary:
            found.append(primary.strip())
        i = 2
        while True:
            val = os.environ.get(f"{env_prefix}_{i}")
            if not val:
                break
            found.append(val.strip())
            i += 1

        # Comma-separated bulk var, e.g. GEMINI_API_KEYS=k1,k2,k3
        bulk = os.environ.get(f"{env_prefix}S")
        if bulk:
            for part in bulk.split(","):
                part = part.strip()
                if part:
                    found.append(part)

        # Dedupe preserving order.
        seen: set[str] = set()
        out: list[str] = []
        for k in found:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _is_key_available(self, key: str) -> bool:
        """True if ``key`` is not marked exhausted, or its cooldown has expired."""
        if key not in self.exhausted:
            return True
        until = self.exhausted[key]
        if until is None:
            return False
        if self._now() >= until:
            # Cooldown elapsed — clear it.
            del self.exhausted[key]
            return True
        return False

    def get_current(self) -> str | None:
        if not self.keys:
            return None
        return self.keys[self.index]

    def rotate(self) -> str | None:
        """Advance to next available key. Returns new key or None if all dead."""
        if not self.keys:
            return None
        n = len(self.keys)
        for step in range(1, n + 1):
            candidate_idx = (self.index + step) % n
            if self._is_key_available(self.keys[candidate_idx]):
                self.index = candidate_idx
                logger.debug(
                    f"[POOL] {self.service}: rotated to key #{self.index + 1}/{n}"
                )
                return self.keys[self.index]
        logger.warning(f"[POOL] {self.service}: all {n} keys exhausted")
        return None

    def mark_exhausted(self, key: str, until: datetime | None = None) -> None:
        """Flag ``key`` as rate-limited and rotate away from it."""
        if key not in self.keys:
            logger.debug(f"[POOL] {self.service}: mark_exhausted for unknown key")
            return
        self.exhausted[key] = until
        until_str = until.isoformat() if until else "indefinite"
        logger.warning(
            f"[POOL] {self.service}: key #{self.keys.index(key) + 1} "
            f"exhausted until {until_str}"
        )
        # Rotate only if the exhausted key is the current one.
        if self.keys[self.index] == key:
            self.rotate()

    def is_exhausted(self) -> bool:
        if not self.keys:
            return True
        return not any(self._is_key_available(k) for k in self.keys)

    def __len__(self) -> int:
        return len(self.keys)

    def __bool__(self) -> bool:
        return bool(self.keys) and not self.is_exhausted()


# -- Module-level factory & preconfigured pools -------------------------------

_POOL_CACHE: dict[str, APIKeyPool] = {}

_SERVICE_PREFIXES = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "newsapi": "NEWSAPI_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


def pool_for(service: str) -> APIKeyPool:
    """Return cached pool for ``service``. Creates it on first call."""
    key = service.lower()
    if key not in _POOL_CACHE:
        prefix = _SERVICE_PREFIXES.get(key, f"{key.upper()}_API_KEY")
        _POOL_CACHE[key] = APIKeyPool(service=key, env_prefix=prefix)
    return _POOL_CACHE[key]


def gemini_pool() -> APIKeyPool:
    return pool_for("gemini")


def groq_pool() -> APIKeyPool:
    return pool_for("groq")


def newsapi_pool() -> APIKeyPool:
    return pool_for("newsapi")


def claude_pool() -> APIKeyPool:
    return pool_for("claude")


# -- Rotation helper ----------------------------------------------------------

def _looks_like_rate_limit(err: BaseException) -> bool:
    msg = str(err).lower()
    return any(marker in msg for marker in _RATE_LIMIT_MARKERS)


async def call_with_rotation(
    pool: APIKeyPool,
    fn: Callable[[str], Awaitable[Any]],
) -> Any:
    """Call ``fn(key)`` with rotation on rate-limit errors.

    On any exception whose string contains a rate-limit marker (429, quota,
    exhausted, rate limit), the current key is marked exhausted and the
    call is retried with the next key. Other exceptions propagate.
    Gives up once every key in the pool has been tried.
    """
    if not pool or pool.get_current() is None:
        raise RuntimeError(f"API key pool for '{pool.service}' is empty")

    last_error: BaseException | None = None
    tried: set[str] = set()
    total = len(pool)

    for _ in range(total):
        key = pool.get_current()
        if key is None or key in tried:
            break
        tried.add(key)
        try:
            return await fn(key)
        except Exception as e:
            if _looks_like_rate_limit(e):
                logger.warning(
                    f"[POOL] {pool.service}: rate-limit hit, rotating. err={e}"
                )
                pool.mark_exhausted(key)
                last_error = e
                if pool.get_current() is None:
                    break
                continue
            raise

    raise RuntimeError(
        f"All {total} keys for '{pool.service}' exhausted. "
        f"Last error: {last_error}"
    )


# -- Self-test ----------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s %(message)s")

    async def _main() -> int:
        # Seed env if caller didn't provide keys, so the test is reproducible.
        os.environ.setdefault("GEMINI_API_KEY", "a")
        os.environ.setdefault("GEMINI_API_KEY_2", "b")
        os.environ.setdefault("GEMINI_API_KEY_3", "c")

        # Fresh pool bypassing cache.
        pool = APIKeyPool("gemini", "GEMINI_API_KEY")
        assert len(pool) >= 3, f"expected >=3 keys, got {len(pool)}"
        assert bool(pool)

        first = pool.get_current()
        second = pool.rotate()
        assert first != second, "rotate() must advance"

        # Force two rate-limit failures; third call should succeed.
        calls: list[str] = []

        async def flaky(key: str) -> str:
            calls.append(key)
            if len(calls) < 3:
                raise RuntimeError("HTTP 429 quota exceeded")
            return f"ok:{key}"

        result = await call_with_rotation(pool, flaky)
        assert result.startswith("ok:"), f"unexpected result {result}"
        assert len(calls) == 3, f"expected 3 calls, got {len(calls)}"
        print(f"[selftest] rotation OK: calls={calls} result={result}")

        # All-exhausted path.
        dead = APIKeyPool("gemini", "GEMINI_API_KEY")

        async def always_fail(key: str) -> str:
            raise RuntimeError("429 rate limit")

        try:
            await call_with_rotation(dead, always_fail)
        except RuntimeError as e:
            assert "exhausted" in str(e).lower()
            print(f"[selftest] exhaustion OK: {e}")
        else:
            raise AssertionError("expected RuntimeError when all keys fail")

        assert dead.is_exhausted()
        assert not bool(dead)

        # Non-rate-limit error should propagate.
        fresh = APIKeyPool("gemini", "GEMINI_API_KEY")

        async def other_error(key: str) -> str:
            raise ValueError("bad request")

        try:
            await call_with_rotation(fresh, other_error)
        except ValueError:
            print("[selftest] non-rate-limit errors propagate OK")
        else:
            raise AssertionError("expected ValueError to propagate")

        print("[selftest] all checks passed")
        return 0

    raise SystemExit(asyncio.run(_main()))
