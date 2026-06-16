"""
Abstract base class for all scrapers.
"""
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """All scrapers inherit from this class."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.delay = self.config.get("delay", 2)
        self.max_retries = self.config.get("max_retries", 3)

    # ── public interface ──────────────────────────────────────────────────────

    def scrape(self, url: str) -> List[Dict[str, Any]]:
        """
        Scrape the given URL with automatic retry logic.
        Returns a list of record dicts.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("[%s] Scraping %s (attempt %d/%d)",
                            self.__class__.__name__, url, attempt, self.max_retries)
                results = self._scrape(url)
                logger.info("[%s] Got %d records from %s",
                            self.__class__.__name__, len(results), url)
                return results
            except Exception as exc:
                logger.warning("[%s] Attempt %d failed: %s",
                               self.__class__.__name__, attempt, exc)
                if attempt < self.max_retries:
                    wait = self.delay * attempt
                    logger.info("Retrying in %.1fs…", wait)
                    time.sleep(wait)
                else:
                    logger.error("[%s] All retries exhausted for %s",
                                 self.__class__.__name__, url)
                    raise
        return []

    def teardown(self):
        """Release any resources (override in subclasses)."""

    # ── abstract ─────────────────────────────────────────────────────────────

    @abstractmethod
    def _scrape(self, url: str) -> List[Dict[str, Any]]:
        """Perform the actual scraping — implement in subclasses."""
