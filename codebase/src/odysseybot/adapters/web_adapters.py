"""Asynchronous Tavily & Firecrawl API client adapters."""

import asyncio
from typing import Any, Dict, List, Optional
import httpx

from odysseybot.config import settings


class WebSearchAdapter:
    """Provides Tavily search integration."""

    def __init__(self, api_key: Optional[str] = None):
        key_val = api_key or (settings.TAVILY_API_KEY.get_secret_value() if settings.TAVILY_API_KEY else None)
        self.api_key = key_val

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        if not self.api_key:
            return [{"title": "Demo Tavily Search", "url": "https://tavily.com", "content": f"Simulated search results for: {query}"}]

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("results", [])
            except Exception:
                pass

        return []


class WebReaderAdapter:
    """Provides Firecrawl web page reading integration."""

    def __init__(self, api_key: Optional[str] = None):
        key_val = api_key or (settings.FIRECRAWL_API_KEY.get_secret_value() if settings.FIRECRAWL_API_KEY else None)
        self.api_key = key_val

    async def read_page(self, page_url: str) -> Optional[str]:
        if not self.api_key:
            return f"Simulated Firecrawl Markdown Content for {page_url}"

        url = "https://api.firecrawl.dev/v1/scrape"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"url": page_url, "formats": ["markdown"]}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("markdown", "")
            except Exception:
                pass

        return None
