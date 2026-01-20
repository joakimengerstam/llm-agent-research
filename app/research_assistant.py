"""
Research Assistant - AI-powered research and information gathering tool
Usage: python research_assistant.py "your research query"
"""
import asyncio
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import sys

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

import app.llm.openai_client as openai_api
from app.config.settings import *


console = Console()

# Configuration
DATA_DIR = Path.home() / ".research_assistant"
DB_PATH = DATA_DIR / "cache.db"

# Initialize
DATA_DIR.mkdir(exist_ok=True)
client = openai_api.async_client()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    content: Optional[str] = None


@dataclass
class ResearchStep:
    action: str  # 'search', 'scrape', 'analyze'
    query: str
    reasoning: str


class Cache:
    """Simple SQLite cache for web content"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                url TEXT PRIMARY KEY,
                content TEXT,
                timestamp REAL
            )
        """)
        self.conn.commit()
    
    def get(self, url: str) -> Optional[str]:
        cursor = self.conn.execute("SELECT content FROM cache WHERE url = ?", (url,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def set(self, url: str, content: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (url, content, timestamp) VALUES (?, ?, ?)",
            (url, content, datetime.now().timestamp())
        )
        self.conn.commit()


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


class ResearchAgent:
    """Main research orchestrator"""
    
    def __init__(self):
        self.search_tool = WebSearchTool()
        self.scrape_tool = WebScrapeTool()
        self.conversation_history = []
    

    async def research(self, query: str) -> str:
        console.print(Panel(f"[bold cyan]🔍 Research Query:[/bold cyan] {query}", expand=False))
        
        # Step 1: Plan the research
        with Progress(SpinnerColumn(), TextColumn("[cyan]Planning research strategy...")) as progress:
            progress.add_task("planning", total=None)
            plan = await self._plan_research(query)
        
        console.print("\n[bold green]📋 Research Plan:[/bold green]")
        for i, step in enumerate(plan, 1):
            console.print(f"  {i}. {step.action.upper()}: {step.query}")
            console.print(f"     [dim]{step.reasoning}[/dim]")
        
        # Step 2: Execute the plan
        console.print("\n[bold green]🚀 Executing research...[/bold green]")
        results = []
        
        for step in plan:
            if step.action == "search":
                search_results = await self.search_tool.search(step.query)

                console.print(f"\n[cyan]🔎 Search: {step.query}[/cyan]")
                console.print(f"   Found {len(search_results)} results")
                results.append({
                    "type": "search",
                    "query": step.query,
                    "results": [asdict(r) for r in search_results]
                })
                
                # Scrape top results
                for i, result in enumerate(search_results[:3], 1):
                    console.print(f"   [{i}] Scraping: {result.title[:60]}...")
                    content = await self.scrape_tool.scrape(result.url)
                    result.content = content
            
            elif step.action == "analyze":
                # Let GPT analyze gathered information
                pass
        
        # Step 3: Synthesize final report
        with Progress(SpinnerColumn(), TextColumn("[cyan]Synthesizing final report...")) as progress:
            progress.add_task("synthesizing", total=None)
            report = await self._synthesize_report(query, results)
        
        return report

    
    async def _plan_research(self, query: str) -> List[ResearchStep]:
        """Use GPT to create a research plan"""
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a research planning assistant. Given a research query, create a step-by-step plan.
                    
Each step should be a JSON object with:
- action: "search" or "analyze"
- query: the search query or analysis task
- reasoning: why this step is important

Return ONLY a JSON array of steps, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Create a research plan for: {query}"
                }
            ],
            temperature=0.7
        )
        
        try:
            plan_json = json.loads(response.choices[0].message.content)
            return [ResearchStep(**step) for step in plan_json]
        except:
            # Fallback to simple search
            return [ResearchStep(
                action="search",
                query=query,
                reasoning="Direct search for the query"
            )]
    
    async def _synthesize_report(self, query: str, results: List[dict]) -> str:
        """Synthesize all findings into a coherent report"""

        # Prepare context from results
        context = []
        for result in results:
            if result["type"] == "search":
                for search_result in result["results"]:
                    if search_result.get("content"):
                        context.append(f"""
Source: {search_result['title']}
URL: {search_result['url']}
Content: {search_result['content'][:1000]}...
""")
        
        context_str = "\n---\n".join(context)

        prompt = [
            {
                "role": "system",
                "content": """You are a research analyst. Synthesize the provided information into a clear, comprehensive report.

Structure your report with:
1. Executive Summary
2. Key Findings (with bullet points)
3. Detailed Analysis
4. Examples
5. Sources including links to each scraped web site

Use markdown formatting. Be concise but thorough."""
            },
            {
                "role": "user",
                "content": f"""Research Query: {query}

Gathered Information:
{context_str}

Please create a comprehensive research report."""
            }
        ]

        print("Executing prompt:  ")
        print(prompt)

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=prompt,
            temperature=0.3
        )
        
        return response.choices[0].message.content


async def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: python research_assistant.py \"your research query\"[/red]")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    if not settings.key:
        console.print("[red]❌ Error: OPENAI_API_KEY environment variable not set[/red]")
        sys.exit(1)
    
    agent = ResearchAgent()
    
    try:
        report = await agent.research(query)
        
        console.print("\n" + "="*80 + "\n")
        console.print(Markdown(report))
        console.print("\n" + "="*80 + "\n")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = DATA_DIR / f"report_{timestamp}.md"
        report_path.write_text(report)
        console.print(f"[green]✅ Report saved to: {report_path}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
