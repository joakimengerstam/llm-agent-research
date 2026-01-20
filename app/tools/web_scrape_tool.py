
import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from app.db.cache import Cache


console = Console()


class WebScrapeTool:
    """Extract clean text content from URLs"""

    def __init__(self):
        self.cache = Cache()

    async def scrape(self, url: str, max_length: int = 5000) -> str:
        # Check cache first
        cached = self.cache.get(url)
        if cached:
            console.print(f"[dim]📦 Using cached content for {url}[/dim]")
            return cached[:max_length]

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)

                # Cache the result
                self.cache.set(url, text)

                return text[:max_length]
        except Exception as e:
            console.print(f"[red]❌ Error scraping {url}: {e}[/red]")
            return ""
