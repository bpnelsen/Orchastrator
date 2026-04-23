"""
Web Testing Agent — Orchestrator
Combines Firecrawl (crawl), Playwright (browser), requests (API), pytest (runner)
Designed for OpenClaw integration via tool calls or Telegram triggers.
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from firecrawl import FirecrawlApp
from playwright.async_api import async_playwright
import requests


# ── Config ──────────────────────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
BASE_URL           = os.getenv("TARGET_BASE_URL", "https://example.com")
REPORT_DIR         = Path(__file__).parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


# ── Firecrawl: Site Crawl & Link Discovery ───────────────────────────────────
class CrawlAgent:
    """Uses Firecrawl to discover pages, extract content, and seed test targets."""

    def __init__(self, api_key: str = FIRECRAWL_API_KEY):
        self.app = FirecrawlApp(api_key=api_key)

    def crawl_site(self, url: str, limit: int = 25) -> dict:
        """Crawl a site and return structured page data."""
        print(f"[Crawl] Starting crawl of {url} (limit={limit})")
        result = self.app.crawl_url(
            url,
            params={
                "limit": limit,
                "scrapeOptions": {"formats": ["markdown", "links"]},
            },
            poll_interval=5,
        )
        pages = result.get("data", [])
        print(f"[Crawl] Found {len(pages)} pages")
        return {"pages": pages, "count": len(pages), "base_url": url}

    def scrape_page(self, url: str) -> dict:
        """Scrape a single page for content and metadata."""
        return self.app.scrape_url(url, params={"formats": ["markdown", "links", "metadata"]})

    def extract_links(self, crawl_result: dict) -> list[str]:
        """Pull all discovered URLs from a crawl result."""
        links = []
        for page in crawl_result.get("pages", []):
            links.extend(page.get("links", []))
        return list(set(links))


# ── Playwright: Browser Automation ──────────────────────────────────────────
class BrowserAgent:
    """Playwright-based browser automation for UI and rendering tests."""

    async def check_page(self, url: str, headless: bool = True) -> dict:
        """Load a page and capture title, status, and screenshot."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page()

            response = await page.goto(url, wait_until="networkidle", timeout=15000)
            title = await page.title()

            screenshot_path = REPORT_DIR / f"screenshot_{datetime.now().strftime('%H%M%S')}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            await browser.close()

        return {
            "url": url,
            "status": response.status if response else None,
            "title": title,
            "screenshot": str(screenshot_path),
        }

    async def check_links(self, urls: list[str]) -> list[dict]:
        """Check a batch of URLs for load status."""
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            for url in urls:
                try:
                    page = await browser.new_page()
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                    results.append({"url": url, "status": resp.status if resp else "no_response", "ok": True})
                    await page.close()
                except Exception as e:
                    results.append({"url": url, "status": "error", "error": str(e), "ok": False})
            await browser.close()
        return results

    async def fill_and_submit(self, url: str, fields: dict, submit_selector: str) -> dict:
        """Fill a form and submit it, returning post-submit URL and title."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            for selector, value in fields.items():
                await page.fill(selector, value)
            await page.click(submit_selector)
            await page.wait_for_load_state("networkidle")
            result = {"final_url": page.url, "title": await page.title()}
            await browser.close()
        return result


# ── Requests: API Testing ────────────────────────────────────────────────────
class APIAgent:
    """HTTP-level API testing with requests."""

    def __init__(self, base_url: str = BASE_URL, headers: Optional[dict] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if headers:
            self.session.headers.update(headers)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(f"{self.base_url}{path}", timeout=10, **kwargs)

    def post(self, path: str, json_body: dict = None, **kwargs) -> requests.Response:
        return self.session.post(f"{self.base_url}{path}", json=json_body, timeout=10, **kwargs)

    def put(self, path: str, json_body: dict = None, **kwargs) -> requests.Response:
        return self.session.put(f"{self.base_url}{path}", json=json_body, timeout=10, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(f"{self.base_url}{path}", timeout=10, **kwargs)

    def health_check(self, path: str = "/health") -> dict:
        try:
            r = self.get(path)
            return {"status": r.status_code, "ok": r.ok, "body": r.text[:200]}
        except Exception as e:
            return {"status": "error", "ok": False, "error": str(e)}


# ── Pytest Runner ────────────────────────────────────────────────────────────
class TestRunner:
    """Triggers pytest programmatically and parses results."""

    def __init__(self, test_dir: str = "tests"):
        self.test_dir = Path(__file__).parent.parent / test_dir

    def run(self, marker: Optional[str] = None, verbose: bool = True) -> dict:
        """Run pytest and return pass/fail summary."""
        cmd = ["python", "-m", "pytest", str(self.test_dir), "--tb=short", "-q"]
        if marker:
            cmd += ["-m", marker]
        if verbose:
            cmd += ["-v"]

        report_path = REPORT_DIR / f"pytest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        cmd += [f"--json-report", f"--json-report-file={report_path}"]

        result = subprocess.run(cmd, capture_output=True, text=True)
        summary = {
            "returncode": result.returncode,
            "passed": result.stdout.count(" PASSED"),
            "failed": result.stdout.count(" FAILED"),
            "stdout": result.stdout[-2000:],
            "report_file": str(report_path),
        }
        return summary


# ── Master Orchestrator ──────────────────────────────────────────────────────
class WebTestingAgent:
    """
    Top-level agent. Can be called from OpenClaw tool definitions
    or triggered directly via CLI / Telegram bot message.
    """

    def __init__(self, target_url: str = BASE_URL):
        self.target_url = target_url
        self.crawl   = CrawlAgent()
        self.browser = BrowserAgent()
        self.api     = APIAgent(base_url=target_url)
        self.runner  = TestRunner()

    async def full_audit(self, limit: int = 20) -> dict:
        """
        Full site audit:
          1. Crawl with Firecrawl
          2. Browser-check discovered pages
          3. API health check
          4. Run pytest suite
        """
        print(f"\n{'='*60}")
        print(f"  Web Testing Agent — Full Audit")
        print(f"  Target: {self.target_url}")
        print(f"{'='*60}\n")

        # Step 1: Crawl
        crawl_result = self.crawl.crawl_site(self.target_url, limit=limit)
        links = self.crawl.extract_links(crawl_result)[:limit]

        # Step 2: Browser checks
        print(f"[Browser] Checking {len(links)} discovered links...")
        browser_results = await self.browser.check_links(links)
        broken = [r for r in browser_results if not r["ok"]]

        # Step 3: API health
        print("[API] Running health check...")
        health = self.api.health_check()

        # Step 4: pytest
        print("[Pytest] Running test suite...")
        test_results = self.runner.run()

        report = {
            "target": self.target_url,
            "timestamp": datetime.now().isoformat(),
            "crawl": {"pages_found": crawl_result["count"], "links_checked": len(links)},
            "browser": {"checked": len(browser_results), "broken": len(broken), "broken_urls": broken},
            "api_health": health,
            "tests": test_results,
        }

        # Save report
        report_path = REPORT_DIR / f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(report, indent=2))
        print(f"\n[Done] Report saved: {report_path}")
        return report


# ── OpenClaw Tool Definition (paste into Johnny's config) ───────────────────
OPENCLAW_TOOL = {
    "name": "run_web_audit",
    "description": "Run a full web testing audit (crawl, browser checks, API health, pytest) against a target URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The base URL to audit"},
            "limit": {"type": "integer", "description": "Max pages to crawl (default 20)", "default": 20},
        },
        "required": ["url"],
    },
}


# ── CLI Entry ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    agent = WebTestingAgent(target_url=url)
    asyncio.run(agent.full_audit())
