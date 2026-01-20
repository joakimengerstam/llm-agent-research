
import httpx
from typing import List, Optional
from dataclasses import dataclass
from rich.console import Console
from bs4 import BeautifulSoup

from app.config.settings import *


console = Console()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    content: Optional[str] = None


class WebSearchTool:
    """Web search using Brave Search API or fallback to DuckDuckGo"""

    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        if settings.brave_api_key:
            return await self._brave_search(query, num_results)
        else:
            console.print("[yellow]💡 Tip: Set BRAVE_API_KEY for better search results[/yellow]")
            return await self._duckduckgo_search(query, num_results)

    async def _brave_search(self, query: str, num_results: int) -> List[SearchResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": settings.brave_api_key},
                params={"q": query, "count": num_results}
            )
            data = response.json()

            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", "")
                ))
            return results

    async def _duckduckgo_search(self, query: str, num_results: int) -> List[SearchResult]:
        """Fallback search using DuckDuckGo HTML scraping"""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"}
            )

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            for result in soup.select('.result')[:num_results]:
                title_elem = result.select_one('.result__a')
                snippet_elem = result.select_one('.result__snippet')

                if title_elem:
                    results.append(SearchResult(
                        title=title_elem.get_text(strip=True),
                        url=title_elem.get('href', ''),
                        snippet=snippet_elem.get_text(strip=True) if snippet_elem else ""
                    ))

            return results
