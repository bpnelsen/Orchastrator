"""
tests/crawl/test_crawl.py — Firecrawl content and structure tests.
"""

import pytest


@pytest.mark.crawl
class TestCrawlDiscovery:
    def test_crawl_returns_pages(self, crawl_agent, base_url):
        result = crawl_agent.crawl_site(base_url, limit=5)
        assert result["count"] > 0, "Crawl returned no pages"

    def test_crawl_extracts_links(self, crawl_agent, base_url):
        result = crawl_agent.crawl_site(base_url, limit=5)
        links = crawl_agent.extract_links(result)
        assert len(links) > 0, "No links extracted from crawl"

    def test_pages_have_markdown_content(self, crawl_agent, base_url):
        result = crawl_agent.crawl_site(base_url, limit=3)
        for page in result["pages"]:
            assert page.get("markdown"), f"Page missing markdown content: {page.get('url')}"


@pytest.mark.crawl
class TestContentQuality:
    def test_homepage_has_expected_content(self, crawl_agent, base_url):
        """Scrape home page and check for key content signals."""
        page = crawl_agent.scrape_page(base_url)
        content = page.get("markdown", "").lower()
        # Customize these keywords for your target site
        assert len(content) > 100, "Home page content is too short"

    def test_no_404_pages_in_crawl(self, crawl_agent, base_url):
        result = crawl_agent.crawl_site(base_url, limit=10)
        for page in result["pages"]:
            status = page.get("metadata", {}).get("statusCode")
            assert status != 404, f"404 found during crawl: {page.get('url')}"
