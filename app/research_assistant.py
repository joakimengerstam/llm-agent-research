"""
Research Assistant - AI-powered research and information gathering tool
Usage: python research_assistant.py "your research query"
"""
import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
import sys

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

import app.llm.openai_client as openai_api
from app.config.settings import *
from app.tools.web_scrape_tool import WebScrapeTool
from app.tools.web_search_tool import WebSearchTool


console = Console()

# Initialize
client = openai_api.async_client()


@dataclass
class ResearchStep:
    action: str  # 'search', 'scrape', 'analyze'
    query: str
    reasoning: str


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
        report_path = settings.DATA_DIR / f"report_{timestamp}.md"
        report_path.write_text(report)
        console.print(f"[green]✅ Report saved to: {report_path}[/green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise


if __name__ == "__main__":
    asyncio.run(main())
