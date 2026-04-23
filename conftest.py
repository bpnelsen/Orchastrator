"""
conftest.py — Shared pytest fixtures for all test modules.
"""

import os
import pytest
import asyncio
from agents.web_testing_agent import CrawlAgent, BrowserAgent, APIAgent

BASE_URL = os.getenv("TARGET_BASE_URL", "https://example.com")
FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY", "")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_agent(base_url):
    return APIAgent(base_url=base_url)


@pytest.fixture(scope="session")
def crawl_agent():
    return CrawlAgent(api_key=FIRECRAWL_KEY)


@pytest.fixture(scope="session")
def browser_agent():
    return BrowserAgent()


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
