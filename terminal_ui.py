"""
Terminal UI for Web Search Pro
Rich terminal interface with progress tracking and interactive search.
"""
import sys
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.markdown import Markdown
from rich.tree import Tree
from rich.prompt import Prompt, Confirm
from rich import box

from search_engines import SearchResult


class TerminalUI:
    """Rich terminal interface for Web Search Pro."""

    def __init__(self):
        self.console = Console()
        self.search_history: List[str] = []

    def clear(self):
        """Clear the terminal."""
        self.console.clear()

    def print_banner(self, tor_available: bool = False, i2p_available: bool = False):
        """Print application banner with status indicators."""
        tor_status = "[green]ONLINE[/green]" if tor_available else "[red]OFFLINE[/red]"
        i2p_status = "[green]ONLINE[/green]" if i2p_available else "[dim]OFFLINE[/dim]"

        banner = f"""
╔═══════════════════════════════════════════════════════════════════╗
║                    WEB SEARCH PRO v2.0                            ║
║           Advanced Web & Darknet Search Tool                      ║
╠═══════════════════════════════════════════════════════════════════╣
║  Clearnet:  [green]READY[/green]                                              ║
║  Darknet:   {tor_status}                                            ║
║  I2P:       {i2p_status}                                            ║
╚═══════════════════════════════════════════════════════════════════╝
        """
        self.console.print(Panel(banner, style="bold cyan", box=box.DOUBLE))

        if not tor_available:
            self.print_tor_setup_instructions()

    def print_help(self):
        """Print help information."""
        help_text = """
## Search Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `term1 term2` | Search for both terms | `zeiss microscope` |
| `+term` | Required term | `+zeiss +kinevo` |
| `"phrase"` | Exact phrase | `"Kinevo 900"` |
| `-term` | Exclude term | `zeiss -leica` |
| `site:` | Limit to site | `site:zeiss.com` |
| `filetype:` | File type filter | `filetype:pdf` |
| `after:` | Date filter | `after:2023-01-01` |
| `term~3` | Proximity search | `python~3 tutorial` |
| `term^2` | Boost importance | `important^2` |

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/engines` | List available search engines |
| `/darknet` | Toggle darknet search |
| `/i2p` | Toggle I2P network search |
| `/tor` | Check Tor connection status |
| `/history` | Show search history |
| `/export [format]` | Export last results (json/txt/md) |
| `/report` | Generate HTML/Markdown reports |
| `/pause` | Pause search and checkpoint |
| `/resume [id]` | Resume paused search |
| `/sessions` | List saved sessions |
| `/clear` | Clear screen |
| `/quit` | Exit program |

## Examples

```
zeiss + "Kinevo 900"
"surgical microscope" site:ncbi.nlm.nih.gov filetype:pdf
neural network -tutorial after:2024-01-01
machine~5 learning  # terms within 5 words
important^3 query   # boost "important"
```
        """
        md = Markdown(help_text)
        self.console.print(Panel(md, title="Help", border_style="green"))

    def print_engines(self, engines: Dict[str, bool]):
        """Print available engines and their status."""
        table = Table(title="Available Search Engines", box=box.ROUNDED)
        table.add_column("Engine", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")

        clearnet = ["duckduckgo", "bing", "brave"]
        darknet = ["ahmia", "torch", "haystack"]

        for engine in clearnet:
            status = "[green]Enabled[/green]" if engines.get(engine, False) else "[red]Disabled[/red]"
            table.add_row(engine.title(), "Clearnet", status)

        for engine in darknet:
            requires_tor = engine in ["torch", "haystack"]
            engine_type = "Darknet (Tor)" if requires_tor else "Darknet (Clearnet gateway)"
            status = "[green]Enabled[/green]" if engines.get(engine, False) else "[red]Disabled[/red]"
            table.add_row(engine.title(), engine_type, status)

        self.console.print(table)

    def print_tor_status(self, is_connected: bool, ip: str = ""):
        """Print Tor connection status."""
        if is_connected:
            status = Panel(
                f"[green]Tor Connected[/green]\nExit IP: {ip}",
                title="Tor Status",
                border_style="green"
            )
            self.console.print(status)
        else:
            self.console.print(Panel(
                "[red]Tor Not Connected[/red]",
                title="Tor Status",
                border_style="red"
            ))
            self.print_tor_setup_instructions()

    def print_tor_setup_instructions(self):
        """Print instructions for setting up Tor."""
        instructions = """
[yellow]Darknet search requires Tor to be running.[/yellow]

[bold]To enable darknet searches:[/bold]

[cyan]macOS:[/cyan]
  brew install tor
  brew services start tor

[cyan]Linux (Debian/Ubuntu):[/cyan]
  sudo apt install tor
  sudo systemctl start tor

[cyan]Linux (Fedora/RHEL):[/cyan]
  sudo dnf install tor
  sudo systemctl start tor

[cyan]Windows:[/cyan]
  Download Tor Browser from https://www.torproject.org
  Or install Tor Expert Bundle

[dim]After starting Tor, use -d flag or /darknet command to enable darknet search.[/dim]
        """
        self.console.print(Panel(instructions, title="Tor Setup", border_style="yellow"))

    def print_query_info(self, query_info: Dict[str, Any]):
        """Print parsed query information."""
        tree = Tree("[bold]Query Analysis[/bold]")

        if query_info.get("terms"):
            terms_branch = tree.add("[cyan]Required Terms (AND)[/cyan]")
            for term in query_info["terms"]:
                terms_branch.add(f"[green]{term}[/green]")

        if query_info.get("or_groups"):
            or_branch = tree.add("[cyan]Alternative Terms (OR)[/cyan]")
            for group in query_info["or_groups"]:
                or_branch.add(f"[yellow]{' OR '.join(group)}[/yellow]")

        if query_info.get("phrases"):
            phrases_branch = tree.add("[cyan]Exact Phrases[/cyan]")
            for phrase in query_info["phrases"]:
                phrases_branch.add(f'[yellow]"{phrase}"[/yellow]')

        if query_info.get("excluded"):
            excluded_branch = tree.add("[cyan]Excluded (NOT)[/cyan]")
            for term in query_info["excluded"]:
                excluded_branch.add(f"[red]-{term}[/red]")

        filters = query_info.get("filters", {})
        active_filters = {k: v for k, v in filters.items() if v}
        if active_filters:
            filters_branch = tree.add("[cyan]Filters[/cyan]")
            for key, value in active_filters.items():
                filters_branch.add(f"[magenta]{key}:[/magenta] {value}")

        self.console.print(tree)

    def get_search_input(self) -> str:
        """Get search query from user."""
        self.console.print()
        query = Prompt.ask("[bold cyan]Search[/bold cyan]")
        if query.strip():
            self.search_history.append(query)
        return query.strip()

    def print_search_history(self):
        """Print search history."""
        if not self.search_history:
            self.console.print("[yellow]No search history yet.[/yellow]")
            return

        table = Table(title="Search History", box=box.ROUNDED)
        table.add_column("#", style="dim")
        table.add_column("Query", style="cyan")

        for i, query in enumerate(self.search_history, 1):
            table.add_row(str(i), query)

        self.console.print(table)

    def create_progress_display(self):
        """Create a progress display for search operations."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False
        )

    def print_progress(self, engine: str, status: str, message: str):
        """Print progress update."""
        status_colors = {
            "starting": "yellow",
            "parsing": "cyan",
            "progress": "blue",
            "complete": "green",
            "error": "red",
            "skipped": "dim",
            "engine_start": "yellow",
            "engine_complete": "green",
        }
        color = status_colors.get(status, "white")
        self.console.print(f"  [{color}][{engine}][/{color}] {message}")

    def print_results(self, results: List[SearchResult], query: str):
        """Print search results with full URLs."""
        if not results:
            self.console.print(Panel(
                "[yellow]No results found.[/yellow]\n"
                "Try:\n"
                "  - Using different keywords\n"
                "  - Removing filters\n"
                "  - Checking spelling",
                title="No Results",
                border_style="yellow"
            ))
            return

        # Summary panel
        engines_used = list(set(r.engine for r in results))
        summary = f"[green]{len(results)}[/green] results from [cyan]{len(engines_used)}[/cyan] engines"
        self.console.print(Panel(summary, title=f"Results for: {query}", border_style="green"))

        # Print each result with full URL on separate line
        for i, result in enumerate(results[:50], 1):  # Show first 50
            self.console.print(f"\n[dim]{i}.[/dim] [cyan]{result.title}[/cyan]")
            self.console.print(f"   [magenta]{result.engine}[/magenta]")
            self.console.print(f"   [blue]{result.url}[/blue]")
            if result.snippet:
                snippet = result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet
                self.console.print(f"   [dim]{snippet}[/dim]")

        if len(results) > 50:
            self.console.print(f"\n[dim]... and {len(results) - 50} more results (use /export to save all)[/dim]")

        # Save to log file
        self.save_results_log(results, query)

    def save_results_log(self, results: List[SearchResult], query: str):
        """Save search results to a log file in current directory."""
        from pathlib import Path

        # Create safe filename from query
        safe_query = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_query}_{timestamp}.log"
        filepath = Path.cwd() / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Search Results: {query}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Total Results: {len(results)}\n")
            f.write("=" * 80 + "\n\n")

            for i, result in enumerate(results, 1):
                f.write(f"[{i}] {result.title}\n")
                f.write(f"    Source: {result.engine}\n")
                f.write(f"    URL: {result.url}\n")
                if result.snippet:
                    f.write(f"    Snippet: {result.snippet}\n")
                f.write("\n")

        self.console.print(f"\n[green]Results saved to:[/green] [blue]{filename}[/blue]")

    def print_result_detail(self, result: SearchResult, index: int):
        """Print detailed view of a single result."""
        panel_content = f"""
[bold]{result.title}[/bold]

[blue]URL:[/blue] {result.url}
[magenta]Source:[/magenta] {result.engine}
[yellow]Relevance:[/yellow] {result.relevance:.2f}

[dim]Snippet:[/dim]
{result.snippet or 'No snippet available'}
        """
        self.console.print(Panel(panel_content, title=f"Result #{index}", border_style="cyan"))

    def print_export_success(self, filepath: str, format: str):
        """Print export success message."""
        self.console.print(Panel(
            f"[green]Results exported successfully![/green]\n\n"
            f"Format: {format.upper()}\n"
            f"File: [blue]{filepath}[/blue]",
            title="Export Complete",
            border_style="green"
        ))

    def print_session_summary(self, summary: Dict[str, Any]):
        """Print session summary."""
        table = Table(title="Session Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Session ID", summary.get("session_id", "N/A"))
        table.add_row("Duration", str(summary.get("duration", "N/A")))
        table.add_row("Total Searches", str(summary.get("total_searches", 0)))
        table.add_row("Total Results", str(summary.get("total_results", 0)))
        table.add_row("Errors", str(summary.get("total_errors", 0)))
        table.add_row("Journal File", summary.get("journal_file", "N/A"))
        table.add_row("Log File", summary.get("log_file", "N/A"))

        self.console.print(table)

    def print_error(self, message: str, details: str = ""):
        """Print error message."""
        error_text = f"[red]{message}[/red]"
        if details:
            error_text += f"\n[dim]{details}[/dim]"
        self.console.print(Panel(error_text, title="Error", border_style="red"))

    def print_info(self, message: str):
        """Print info message."""
        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def print_success(self, message: str):
        """Print success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def print_warning(self, message: str):
        """Print warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def confirm(self, message: str) -> bool:
        """Ask for confirmation."""
        return Confirm.ask(message)

    def select_engines(self, available: List[str], current: List[str]) -> List[str]:
        """Interactive engine selection."""
        self.console.print("\n[bold]Select search engines:[/bold]")

        for i, engine in enumerate(available, 1):
            status = "[green]✓[/green]" if engine in current else "[red]✗[/red]"
            self.console.print(f"  {i}. {status} {engine}")

        self.console.print("\nEnter numbers separated by commas (e.g., 1,2,3) or 'all':")
        selection = Prompt.ask("Selection")

        if selection.lower() == "all":
            return available

        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            return [available[i] for i in indices if 0 <= i < len(available)]
        except (ValueError, IndexError):
            self.print_warning("Invalid selection, keeping current engines")
            return current


class SearchProgressTracker:
    """Tracks and displays search progress with live updates."""

    def __init__(self, console: Console):
        self.console = console
        self.start_time = None
        self.engine_status: Dict[str, str] = {}
        self.results_count: Dict[str, int] = {}

    def start(self, engines: List[str]):
        """Initialize progress tracking."""
        self.start_time = time.time()
        self.engine_status = {e: "pending" for e in engines}
        self.results_count = {e: 0 for e in engines}

    def update(self, engine: str, status: str, message: str = "", count: int = 0):
        """Update progress for an engine."""
        self.engine_status[engine] = status
        if count > 0:
            self.results_count[engine] = count

        # Print update
        elapsed = time.time() - self.start_time if self.start_time else 0

        status_icon = {
            "pending": "[dim]○[/dim]",
            "starting": "[yellow]◐[/yellow]",
            "running": "[cyan]◑[/cyan]",
            "parsing": "[blue]◒[/blue]",
            "complete": "[green]●[/green]",
            "error": "[red]✗[/red]",
            "skipped": "[dim]○[/dim]",
        }.get(status, "[white]○[/white]")

        self.console.print(
            f"  {status_icon} [{elapsed:5.1f}s] [bold]{engine}[/bold]: {message}"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get progress summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        total_results = sum(self.results_count.values())
        completed = sum(1 for s in self.engine_status.values() if s == "complete")
        errors = sum(1 for s in self.engine_status.values() if s == "error")

        return {
            "elapsed_seconds": elapsed,
            "engines_completed": completed,
            "engines_failed": errors,
            "total_results": total_results,
            "results_by_engine": self.results_count.copy()
        }


class TieredProgressTracker:
    """Tracks and displays tiered search progress."""
    
    TIER_NAMES = {
        1: "Authoritative",
        2: "Major Engines",
        3: "Extended",
        4: "Specialized",
        5: "Tor Network",
        6: "I2P Network",
    }
    
    def __init__(self, console: Console):
        self.console = console
        self.start_time = None
        self.tier_status: Dict[int, str] = {}
        self.tier_results: Dict[int, int] = {}
        self.current_tier = 0
    
    def start(self, tiers: List[int]):
        """Initialize tiered progress tracking."""
        self.start_time = time.time()
        self.tier_status = {t: "pending" for t in tiers}
        self.tier_results = {t: 0 for t in tiers}
        self._print_header()
    
    def _print_header(self):
        """Print tier progress header."""
        self.console.print("\n[bold]Tiered Search Progress:[/bold]")
        for tier in sorted(self.tier_status.keys()):
            name = self.TIER_NAMES.get(tier, f"Tier {tier}")
            self.console.print(f"  [dim]○[/dim] Tier {tier}: {name}")
    
    def start_tier(self, tier: int, engines: List[str]):
        """Mark a tier as starting."""
        self.current_tier = tier
        self.tier_status[tier] = "running"
        name = self.TIER_NAMES.get(tier, f"Tier {tier}")
        self.console.print(f"\n[yellow]▶[/yellow] [bold]Tier {tier}:[/bold] {name} ({len(engines)} engines)")
    
    def update_tier(self, tier: int, status: str, results: int = 0, message: str = ""):
        """Update tier progress."""
        self.tier_status[tier] = status
        if results > 0:
            self.tier_results[tier] = results
        
        status_icon = {
            "pending": "[dim]○[/dim]",
            "running": "[yellow]◐[/yellow]",
            "complete": "[green]●[/green]",
            "skipped": "[dim]⊘[/dim]",
            "failed": "[red]✗[/red]",
        }.get(status, "[white]○[/white]")
        
        if message:
            self.console.print(f"  {status_icon} {message}")
    
    def complete_tier(self, tier: int, results_count: int, elapsed: float):
        """Mark a tier as complete."""
        self.tier_status[tier] = "complete"
        self.tier_results[tier] = results_count
        name = self.TIER_NAMES.get(tier, f"Tier {tier}")
        self.console.print(f"  [green]●[/green] {name}: {results_count} results in {elapsed:.1f}s")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get tiered progress summary."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        total_results = sum(self.tier_results.values())
        completed = sum(1 for s in self.tier_status.values() if s == "complete")
        
        return {
            "elapsed_seconds": elapsed,
            "tiers_completed": completed,
            "total_tiers": len(self.tier_status),
            "total_results": total_results,
            "results_by_tier": self.tier_results.copy()
        }
