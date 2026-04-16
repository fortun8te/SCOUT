"""Per-domain async token-bucket rate limiter."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# (rate tokens/sec, burst) per domain. Conservative defaults tuned for each API's
# documented limits; unauth github is the strictest (60/hr -> 1/min).
DEFAULT_DOMAIN_LIMITS: dict[str, tuple[float, int]] = {
    "api.github.com": (1 / 60, 5),
    "newsapi.org": (0.3, 3),
    "generativelanguage.googleapis.com": (1.0, 5),
    "hn.algolia.com": (5.0, 10),
    "export.arxiv.org": (1.0, 3),
    "www.reddit.com": (0.5, 3),
    "api.bsky.app": (5.0, 10),
    "dev.to": (3.0, 10),
    "api.producthunt.com": (1.0, 5),
}

FALLBACK_RATE = 3.0
FALLBACK_BURST = 10


def extract_domain(url: str) -> str:
    """Return the netloc (host) of a URL, lowercased, without port."""
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    if "@" in host:
        host = host.split("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host.lower()


class _Bucket:
    __slots__ = ("rate", "burst", "tokens", "updated", "lock")

    def __init__(self, rate: float, burst: int) -> None:
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.updated = time.monotonic()
        self.lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.updated
        if elapsed > 0:
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.updated = now


class RateLimiter:
    """Token-bucket limiter keyed by domain string."""

    def __init__(
        self,
        default_rate: float = FALLBACK_RATE,
        default_burst: int = FALLBACK_BURST,
        domain_limits: dict[str, tuple[float, int]] | None = None,
    ) -> None:
        self.default_rate = default_rate
        self.default_burst = default_burst
        self._limits: dict[str, tuple[float, int]] = dict(DEFAULT_DOMAIN_LIMITS)
        if domain_limits:
            self._limits.update(domain_limits)
        self._buckets: dict[str, _Bucket] = {}
        self._buckets_lock = asyncio.Lock()

    def configure(self, domain: str, rate: float, burst: int) -> None:
        self._limits[domain.lower()] = (rate, burst)
        self._buckets.pop(domain.lower(), None)

    async def _get_bucket(self, domain: str) -> _Bucket:
        bucket = self._buckets.get(domain)
        if bucket is not None:
            return bucket
        async with self._buckets_lock:
            bucket = self._buckets.get(domain)
            if bucket is None:
                rate, burst = self._limits.get(domain, (self.default_rate, self.default_burst))
                bucket = _Bucket(rate, burst)
                self._buckets[domain] = bucket
            return bucket

    async def wait(self, domain: str) -> None:
        domain = domain.lower()
        bucket = await self._get_bucket(domain)
        async with bucket.lock:
            bucket._refill()
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return
            needed = 1 - bucket.tokens
            wait_for = needed / bucket.rate if bucket.rate > 0 else 0
            logger.debug("Rate limit throttling %s: sleeping %.3fs", domain, wait_for)
            await asyncio.sleep(wait_for)
            bucket._refill()
            bucket.tokens = max(0.0, bucket.tokens - 1)

    @asynccontextmanager
    async def acquire(self, domain_or_url: str):
        domain = extract_domain(domain_or_url)
        await self.wait(domain)
        yield


global_limiter = RateLimiter()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

    async def _self_test() -> None:
        limiter = RateLimiter()
        limiter.configure("test.example.com", rate=5.0, burst=2)
        start = time.monotonic()
        hits: list[float] = []

        async def call(i: int) -> None:
            async with limiter.acquire("test.example.com"):
                hits.append(time.monotonic() - start)

        await asyncio.gather(*[call(i) for i in range(20)])
        elapsed = time.monotonic() - start
        # 20 calls, burst 2 free, then 18 more at 5/sec -> ~3.6s minimum.
        assert elapsed >= 3.0, f"Calls not paced: finished in {elapsed:.2f}s"
        print(f"20 calls paced over {elapsed:.2f}s (expected >= 3.0s) - OK")
        print(f"First 5 hit times: {[f'{h:.2f}' for h in hits[:5]]}")

    asyncio.run(_self_test())
