# Web Testing Agent

A Python agent that combines **Firecrawl** (crawling), **Playwright** (browser automation), **requests** (API testing), and **pytest** (test runner) into a unified web QA tool. Built to integrate with the **OpenClaw/Johnny** setup on `srv1416234`.

---

## Structure

```
web-testing-agent/
├── agents/
│   └── web_testing_agent.py   # Core agent classes + orchestrator
├── tests/
│   ├── conftest.py             # Shared pytest fixtures
│   ├── api/
│   │   └── test_api.py         # API / HTTP tests
│   ├── browser/
│   │   └── test_browser.py     # Playwright browser tests
│   └── crawl/
│       └── test_crawl.py       # Firecrawl content tests
├── reports/                    # Auto-generated JSON + screenshots
├── config/
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
# 1. Clone / copy to VPS
scp -r web-testing-agent/ user@93.188.160.45:~/

# 2. Install deps
pip install -r requirements.txt
playwright install chromium

# 3. Configure environment
cp .env.example .env
nano .env   # Set FIRECRAWL_API_KEY and TARGET_BASE_URL
```

---

## Usage

### Full audit (CLI)
```bash
python agents/web_testing_agent.py https://your-site.com
```

### Run specific test groups
```bash
pytest -m api        # API tests only
pytest -m browser    # Playwright tests only
pytest -m crawl      # Firecrawl content tests only
pytest               # All tests
```

---

## OpenClaw / Johnny Integration

Add the following to your OpenClaw tool config so Johnny can trigger audits via Telegram:

```json
{
  "name": "run_web_audit",
  "description": "Run a full web testing audit against a target URL using Firecrawl, Playwright, and pytest.",
  "parameters": {
    "type": "object",
    "properties": {
      "url": { "type": "string", "description": "The base URL to audit" },
      "limit": { "type": "integer", "description": "Max pages to crawl", "default": 20 }
    },
    "required": ["url"]
  }
}
```

In your OpenClaw agent executor, wire it to:
```python
from agents.web_testing_agent import WebTestingAgent
import asyncio

def run_web_audit(url: str, limit: int = 20):
    agent = WebTestingAgent(target_url=url)
    return asyncio.run(agent.full_audit(limit=limit))
```

Then message Johnny:
> `audit https://your-site.com`

---

## Reports

All reports saved to `reports/`:
- `audit_YYYYMMDD_HHMMSS.json` — full audit JSON
- `pytest_YYYYMMDD_HHMMSS.json` — pytest results
- `screenshot_HHMMSS.png` — Playwright page screenshots
