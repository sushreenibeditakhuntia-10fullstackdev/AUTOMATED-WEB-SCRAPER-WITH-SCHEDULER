"""
Lightweight scraper using requests + BeautifulSoup.
Great for static HTML pages that don't require JavaScript.
"""
import json
import time
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper
from app.utils.logger import get_logger
from config.settings import active_config

logger = get_logger(__name__)


class RequestsScraper(BaseScraper):
    """
    Scrape static pages with requests + BeautifulSoup.

    config keys:
        selectors   – dict mapping field -> CSS selector
        list_selector – CSS selector for the repeating item container
        pagination  – dict with 'next_selector' and optional 'max_pages'
        delay       – seconds to wait between requests
        headers     – extra HTTP headers
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": active_config.USER_AGENT,
            **(self.config.get("headers") or {}),
        })
        self.timeout = active_config.REQUEST_TIMEOUT

    # ── private ───────────────────────────────────────────────────────────────

    def _scrape(self, url: str) -> List[Dict[str, Any]]:
        selectors: Dict[str, str] = self.config.get("selectors", {})
        list_sel: str = self.config.get("list_selector", "")
        pagination: Dict = self.config.get("pagination", {})
        max_pages: int = pagination.get("max_pages", 1)
        next_sel: str = pagination.get("next_selector", "")

        all_records: List[Dict[str, Any]] = []
        current_url: Optional[str] = url
        page = 0

        while current_url and page < max_pages:
            page += 1
            logger.debug("Fetching page %d: %s", page, current_url)

            response = self.session.get(current_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            records = self._extract_records(soup, selectors, list_sel)
            all_records.extend(records)
            logger.debug("Page %d: extracted %d records", page, len(records))

            # Pagination
            current_url = None
            if next_sel and page < max_pages:
                next_tag = soup.select_one(next_sel)
                if next_tag and next_tag.get("href"):
                    href = next_tag["href"]
                    current_url = href if href.startswith("http") else url.rstrip("/") + href
                    time.sleep(self.delay)

        return all_records

    def _extract_records(
        self,
        soup: BeautifulSoup,
        selectors: Dict[str, str],
        list_selector: str,
    ) -> List[Dict[str, Any]]:
        records = []

        if list_selector:
            containers = soup.select(list_selector)
            for container in containers:
                record = self._extract_fields(container, selectors)
                if record:
                    records.append(record)
        else:
            # Fallback: extract single record from the whole page
            record = self._extract_fields(soup, selectors)
            if record:
                records.append(record)

        return records

    def _extract_fields(
        self,
        container: BeautifulSoup,
        selectors: Dict[str, str],
    ) -> Dict[str, Any]:
        record: Dict[str, Any] = {}
        extra: Dict[str, Any] = {}

        known = {"title", "url", "price", "description", "category", "rating"}

        for field, selector in selectors.items():
            element = container.select_one(selector)
            if not element:
                value = None
            elif field == "url":
                value = element.get("href") or element.get_text(strip=True)
            else:
                value = element.get_text(strip=True)

            if field in known:
                record[field] = value
            else:
                extra[field] = value

        record["extra_data"] = extra
        return record

    def teardown(self):
        self.session.close()
