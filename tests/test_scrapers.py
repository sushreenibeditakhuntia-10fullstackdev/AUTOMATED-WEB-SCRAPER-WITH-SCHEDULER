"""
Unit tests for the scraper layer (no real network calls — uses unittest.mock).
"""
from unittest.mock import MagicMock, patch

import pytest

from app.scrapers.requests_scraper import RequestsScraper


SAMPLE_HTML = """
<html><body>
  <article class="product_pod">
    <h3><a href="/cat/book1.html">My Book</a></h3>
    <p class="price_color">£12.99</p>
    <p class="star-rating Three"></p>
  </article>
  <article class="product_pod">
    <h3><a href="/cat/book2.html">Another Book</a></h3>
    <p class="price_color">£7.49</p>
  </article>
</body></html>
"""


class TestRequestsScraper:
    def setup_method(self):
        self.config = {
            "list_selector": "article.product_pod",
            "selectors": {
                "title": "h3 > a",
                "url": "h3 > a",
                "price": "p.price_color",
                "rating": "p.star-rating",
            },
        }

    @patch("app.scrapers.requests_scraper.requests.Session.get")
    def test_scrape_returns_records(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = SAMPLE_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        scraper = RequestsScraper(self.config)
        records = scraper.scrape("https://fake.example.com")
        scraper.teardown()

        assert len(records) == 2
        assert records[0]["title"] == "My Book"
        assert records[0]["price"] == "£12.99"

    @patch("app.scrapers.requests_scraper.requests.Session.get")
    def test_scrape_retries_on_error(self, mock_get):
        mock_get.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            Exception("Still down"),
        ]
        scraper = RequestsScraper({**self.config, "max_retries": 3, "delay": 0})
        with pytest.raises(Exception):
            scraper.scrape("https://fake.example.com")
        scraper.teardown()
        assert mock_get.call_count == 3

    def test_extract_fields_known_and_extra(self):
        from bs4 import BeautifulSoup
        html = '<div><h3><a href="/x">Title</a></h3><span class="custom">Extra</span></div>'
        soup = BeautifulSoup(html, "lxml")
        scraper = RequestsScraper({
            "selectors": {"title": "h3 > a", "custom_field": "span.custom"}
        })
        record = scraper._extract_fields(soup, scraper.config["selectors"])
        assert record["title"] == "Title"
        assert record["extra_data"]["custom_field"] == "Extra"
        scraper.teardown()


class TestHelpers:
    def test_is_valid_url(self):
        from app.utils.helpers import is_valid_url
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://sub.domain.org/path?q=1") is True
        assert is_valid_url("not-a-url") is False
        assert is_valid_url("ftp://files.example.com") is False

    def test_clean_text(self):
        from app.utils.helpers import clean_text
        assert clean_text("  hello   world  ") == "hello world"
        assert clean_text(None) is None
        assert clean_text("   ") is None

    def test_parse_price(self):
        from app.utils.helpers import parse_price
        assert parse_price("£12.99") == "£12.99"
        assert parse_price("  $  5.00  ") == "$  5.00"
        assert parse_price(None) is None

    def test_chunk_list(self):
        from app.utils.helpers import chunk_list
        result = list(chunk_list([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_flatten_dict(self):
        from app.utils.helpers import flatten_dict
        nested = {"a": {"b": {"c": 1}}, "d": 2}
        flat = flatten_dict(nested)
        assert flat == {"a.b.c": 1, "d": 2}
