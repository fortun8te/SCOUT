"""Smart caching to reduce API calls and data transfer"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CacheManager:
    """Cache API responses with smart invalidation"""

    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Get cached data if fresh"""
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)

            # Check age
            cached_at = datetime.fromisoformat(cached["_cached_at"])
            age = datetime.utcnow() - cached_at
            age_hours = age.total_seconds() / 3600

            if age_hours < max_age_hours:
                logger.debug(f"Cache hit for {key} (age: {age_hours:.1f}h)")
                return cached.get("data")
            else:
                logger.debug(f"Cache expired for {key} (age: {age_hours:.1f}h)")
                return None

        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None

    def set(self, key: str, data: Dict) -> None:
        """Store data in cache"""
        try:
            cache_file = self.cache_dir / f"{key}.json"
            cache_data = {
                "_cached_at": datetime.utcnow().isoformat() + "Z",
                "data": data
            }
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
            logger.debug(f"Cached {key}")
        except Exception as e:
            logger.warning(f"Cache write error for {key}: {e}")

    def clear(self, older_than_hours: int = 48) -> None:
        """Remove old cache files"""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                cached_at = datetime.fromisoformat(cached["_cached_at"])

                if cached_at < cutoff:
                    cache_file.unlink()
                    logger.debug(f"Cleared old cache: {cache_file.name}")
            except Exception as e:
                logger.warning(f"Error clearing cache {cache_file}: {e}")
