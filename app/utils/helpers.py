"""
Miscellaneous utility helpers shared across the project.
"""
import json
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse


def is_valid_url(url: str) -> bool:
    """Return True if *url* is an absolute HTTP/HTTPS URL."""
    try:
        result = urlparse(url)
        return result.scheme in {"http", "https"} and bool(result.netloc)
    except ValueError:
        return False


def make_absolute_url(base: str, href: str) -> str:
    """Resolve *href* relative to *base* and return an absolute URL."""
    if href.startswith(("http://", "https://")):
        return href
    return urljoin(base, href)


def clean_text(text: Optional[str]) -> Optional[str]:
    """Strip extra whitespace and normalise unicode spaces."""
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text)
    return text.strip() or None


def parse_price(raw: Optional[str]) -> Optional[str]:
    """
    Extract a price string like '$12.99' or '€ 5,99' from messy text.
    Returns the cleaned string or None.
    """
    if not raw:
        return None
    match = re.search(r"[\$€£¥₹]?\s*\d[\d,]*\.?\d*", raw)
    return match.group(0).strip() if match else clean_text(raw)


def safe_json_loads(text: Optional[str], default: Any = None) -> Any:
    """Parse JSON without raising; return *default* on failure."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def retry(max_attempts: int = 3, delay: float = 2.0, exceptions=(Exception,)):
    """
    Decorator that retries the wrapped function on specified exceptions.

    Usage::

        @retry(max_attempts=3, delay=1.5)
        def fetch(url):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay * attempt)
        return wrapper
    return decorator


def chunk_list(lst: list, size: int):
    """Yield successive *size*-sized chunks from *lst*."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def flatten_dict(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
    """Recursively flatten a nested dict using *sep* as key separator."""
    items: Dict = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep))
        else:
            items[new_key] = v
    return items
