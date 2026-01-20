"""
Research Assistant - AI-powered research and information gathering tool
Usage: python research_assistant.py "your research query"
"""
import asyncio
from datetime import datetime
import sys

from rich.console import Console
from rich.markdown import Markdown

from app.config.settings import *
from app.agent.research_agent import ResearchAgent


console = Console()


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
