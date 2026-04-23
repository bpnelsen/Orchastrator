"""
tests/browser/test_browser.py — Playwright browser automation tests.
"""

import pytest


@pytest.mark.browser
@pytest.mark.asyncio
class TestPageLoad:
    async def test_homepage_loads(self, browser_agent, base_url):
        result = await browser_agent.check_page(base_url)
        assert result["status"] == 200, f"Bad status: {result['status']}"
        assert result["title"], "Page title is empty"

    async def test_screenshot_saved(self, browser_agent, base_url):
        result = await browser_agent.check_page(base_url)
        from pathlib import Path
        assert Path(result["screenshot"]).exists(), "Screenshot not saved"

    async def test_no_console_errors(self, browser_agent, base_url):
        """Capture and assert no JS errors on load."""
        from playwright.async_api import async_playwright
        errors = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("pageerror", lambda err: errors.append(str(err)))
            await page.goto(base_url, wait_until="networkidle", timeout=15000)
            await browser.close()
        assert not errors, f"JS errors on page load: {errors}"


@pytest.mark.browser
@pytest.mark.asyncio
class TestNavigation:
    async def test_internal_links_reachable(self, browser_agent, crawl_agent, base_url):
        """Crawl home page links and verify none are broken."""
        crawl_result = crawl_agent.crawl_site(base_url, limit=10)
        links = crawl_agent.extract_links(crawl_result)[:10]
        results = await browser_agent.check_links(links)
        broken = [r for r in results if not r["ok"]]
        assert not broken, f"Broken links found: {broken}"
