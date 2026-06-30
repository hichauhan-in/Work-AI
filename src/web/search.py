"""Web search adapter.

Default provider is a self-hosted **SearXNG** instance, which keeps queries on your own
machine. A ``duckduckgo`` fallback is available if the ``duckduckgo_search`` package is
installed. Only the search *query* ever leaves the machine — never your note content.

All network errors are swallowed and return ``[]`` so a web hiccup never breaks a query.
"""
from __future__ import annotations

from ..logging_setup import get_logger

log = get_logger("web")


class WebSearch:
    def __init__(
        self,
        provider: str = "searxng",
        searxng_url: str = "http://localhost:8888",
        max_results: int = 5,
        fetch_pages: bool = False,
        fetch_timeout: int = 15,
    ):
        self.provider = provider
        self.searxng_url = searxng_url.rstrip("/")
        self.max_results = max_results
        self.fetch_pages = fetch_pages
        self.fetch_timeout = fetch_timeout

    @classmethod
    def from_config(cls, cfg) -> "WebSearch":
        return cls(
            provider=cfg.get("web.provider", "searxng"),
            searxng_url=cfg.get("web.searxng_url", "http://localhost:8888"),
            max_results=int(cfg.get("web.max_results", 5)),
            fetch_pages=bool(cfg.get("web.fetch_pages", False)),
            fetch_timeout=int(cfg.get("web.fetch_timeout", 15)),
        )

    def search(self, query: str) -> list[dict]:
        try:
            if self.provider == "searxng":
                results = self._searxng(query)
            elif self.provider == "duckduckgo":
                results = self._duckduckgo(query)
            else:
                log.warning("Unknown web provider: %s", self.provider)
                return []
        except Exception as exc:
            log.warning("Web search failed (%s): %s", self.provider, exc)
            return []

        if self.fetch_pages:
            for result in results:
                page_text = self._fetch_page(result.get("url", ""))
                if page_text:
                    result["content"] = page_text
        return results

    def _searxng(self, query: str) -> list[dict]:
        import requests  # lazy

        response = requests.get(
            f"{self.searxng_url}/search",
            params={"q": query, "format": "json"},
            timeout=self.fetch_timeout,
            headers={"User-Agent": "PersonalAI/0.1"},
        )
        response.raise_for_status()
        data = response.json()
        results: list[dict] = []
        for item in data.get("results", [])[: self.max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                }
            )
        return results

    def _duckduckgo(self, query: str) -> list[dict]:
        try:
            from duckduckgo_search import DDGS  # optional dependency
        except ImportError:
            log.warning(
                "duckduckgo provider selected but 'duckduckgo_search' is not installed."
            )
            return []
        results: list[dict] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=self.max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href", ""),
                        "content": item.get("body", ""),
                    }
                )
        return results

    def _fetch_page(self, url: str) -> str:
        if not url:
            return ""
        try:
            import requests  # lazy
            from bs4 import BeautifulSoup  # lazy

            response = requests.get(
                url, timeout=self.fetch_timeout, headers={"User-Agent": "PersonalAI/0.1"}
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ").strip()
            return " ".join(text.split())[:4000]
        except Exception as exc:
            log.debug("Page fetch failed for %s: %s", url, exc)
            return ""
