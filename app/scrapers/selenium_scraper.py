"""
JavaScript-capable scraper built on Selenium + BeautifulSoup.
Use for SPAs, lazy-loaded content, or pages requiring interaction.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False

from app.scrapers.base_scraper import BaseScraper
from app.utils.logger import get_logger
from config.settings import active_config

logger = get_logger(__name__)


class SeleniumScraper(BaseScraper):
    """
    Scrape dynamic pages using Selenium + Chrome.

    config keys:
        selectors        – dict mapping field -> CSS selector
        list_selector    – CSS selector for repeating item containers
        wait_selector    – CSS selector to wait for before parsing
        scroll_to_bottom – bool; scroll page to load lazy content
        screenshot       – bool; save screenshot after load
        actions          – list of action dicts (click / input / wait)
        pagination       – dict with 'next_selector' and 'max_pages'
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.driver: Optional[webdriver.Chrome] = None
        self._init_driver()

    # ── driver lifecycle ─────────────────────────────────────────────────────

    def _init_driver(self):
        options = Options()
        if active_config.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"user-agent={active_config.USER_AGENT}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            if USE_WDM:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_page_load_timeout(active_config.PAGE_LOAD_TIMEOUT)
            self.wait = WebDriverWait(self.driver, active_config.WEBDRIVER_TIMEOUT)
            logger.info("Selenium ChromeDriver initialised (headless=%s)", active_config.HEADLESS)
        except WebDriverException as e:
            logger.error("Failed to initialise ChromeDriver: %s", e)
            raise

    def teardown(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("ChromeDriver closed")
            except Exception:
                pass
            self.driver = None

    # ── private ───────────────────────────────────────────────────────────────

    def _scrape(self, url: str) -> List[Dict[str, Any]]:
        selectors: Dict[str, str] = self.config.get("selectors", {})
        list_sel: str = self.config.get("list_selector", "")
        wait_sel: str = self.config.get("wait_selector", "")
        scroll: bool = self.config.get("scroll_to_bottom", False)
        screenshot: bool = self.config.get("screenshot", False)
        actions: List[Dict] = self.config.get("actions", [])
        pagination: Dict = self.config.get("pagination", {})
        max_pages: int = pagination.get("max_pages", 1)
        next_sel: str = pagination.get("next_selector", "")

        all_records: List[Dict[str, Any]] = []
        current_url: Optional[str] = url
        page = 0

        while current_url and page < max_pages:
            page += 1
            logger.debug("Selenium — page %d: %s", page, current_url)
            self.driver.get(current_url)

            if wait_sel:
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_sel)))
                except TimeoutException:
                    logger.warning("Timed out waiting for selector '%s'", wait_sel)

            self._run_actions(actions)

            if scroll:
                self._scroll_to_bottom()

            if screenshot:
                self._take_screenshot(page)

            time.sleep(self.delay)

            soup = BeautifulSoup(self.driver.page_source, "lxml")
            records = self._extract_records(soup, selectors, list_sel)
            all_records.extend(records)
            logger.debug("Page %d: extracted %d records", page, len(records))

            # Pagination
            current_url = None
            if next_sel and page < max_pages:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, next_sel)
                    next_href = btn.get_attribute("href")
                    if next_href:
                        current_url = next_href
                    else:
                        btn.click()
                        time.sleep(self.delay)
                        current_url = self.driver.current_url
                except NoSuchElementException:
                    logger.debug("No next-page element found — stopping pagination")

        return all_records

    def _run_actions(self, actions: List[Dict]):
        for action in actions:
            action_type = action.get("type", "")
            selector = action.get("selector", "")
            try:
                if action_type == "click":
                    el = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    el.click()
                elif action_type == "input":
                    el = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    el.clear()
                    el.send_keys(action.get("value", ""))
                elif action_type == "wait":
                    time.sleep(float(action.get("seconds", 1)))
            except (NoSuchElementException, TimeoutException) as e:
                logger.warning("Action '%s' on '%s' failed: %s", action_type, selector, e)

    def _scroll_to_bottom(self):
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(10):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _take_screenshot(self, page: int):
        os.makedirs("data/screenshots", exist_ok=True)
        path = f"data/screenshots/screenshot_page{page}_{int(time.time())}.png"
        self.driver.save_screenshot(path)
        logger.debug("Screenshot saved: %s", path)

    def _extract_records(
        self,
        soup: BeautifulSoup,
        selectors: Dict[str, str],
        list_selector: str,
    ) -> List[Dict[str, Any]]:
        records = []
        known = {"title", "url", "price", "description", "category", "rating"}

        containers = soup.select(list_selector) if list_selector else [soup]
        for container in containers:
            record: Dict[str, Any] = {}
            extra: Dict[str, Any] = {}
            for field, selector in selectors.items():
                el = container.select_one(selector)
                if not el:
                    value = None
                elif field == "url":
                    value = el.get("href") or el.get_text(strip=True)
                else:
                    value = el.get_text(strip=True)

                if field in known:
                    record[field] = value
                else:
                    extra[field] = value
            record["extra_data"] = extra
            if record:
                records.append(record)

        return records
