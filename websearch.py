#!/usr/bin/env python3
"""
Web Search Pro - Advanced Web & Darknet Search Tool
Main entry point and search orchestration.
"""
import sys
import signal
import argparse
from typing import List, Optional, Dict, Any

from rich.console import Console

from config import CLEARNET_ENGINES, DARKNET_ENGINES
from search_engines import SearchEngineManager, SearchResult, SearchError
from query_parser import QueryParser, ParsedQuery, format_query_for_display
from journal import SearchJournal
from terminal_ui import TerminalUI, SearchProgressTracker

# Translation support
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False

# Target languages for multi-language search
SEARCH_LANGUAGES = [
    ('en', 'English'),
    ('de', 'German'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('it', 'Italian'),
    ('pt', 'Portuguese'),
    ('ru', 'Russian'),
    ('zh-CN', 'Chinese'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('ar', 'Arabic'),
    ('nl', 'Dutch'),
]


# Common file type aliases
FILETYPE_ALIASES = {
    # Documents
    "doc": ["doc", "docx"],
    "docs": ["doc", "docx", "pdf", "odt", "rtf"],
    "pdf": ["pdf"],
    "word": ["doc", "docx"],
    "excel": ["xls", "xlsx"],
    "powerpoint": ["ppt", "pptx"],
    "office": ["doc", "docx", "xls", "xlsx", "ppt", "pptx"],
    # Ebooks
    "ebook": ["pdf", "epub", "mobi", "azw3"],
    "epub": ["epub"],
    "mobi": ["mobi"],
    # Images
    "image": ["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"],
    "img": ["jpg", "jpeg", "png", "gif", "webp"],
    "photo": ["jpg", "jpeg", "png", "raw", "cr2", "nef"],
    "jpg": ["jpg", "jpeg"],
    "png": ["png"],
    "gif": ["gif"],
    "svg": ["svg"],
    # Audio
    "audio": ["mp3", "wav", "flac", "ogg", "m4a", "aac"],
    "music": ["mp3", "flac", "ogg", "m4a"],
    "mp3": ["mp3"],
    # Video
    "video": ["mp4", "mkv", "avi", "mov", "webm", "wmv"],
    "mp4": ["mp4"],
    # Code
    "code": ["py", "js", "ts", "java", "cpp", "c", "h", "go", "rs", "rb"],
    "python": ["py", "ipynb"],
    "javascript": ["js", "ts", "jsx", "tsx"],
    # Data
    "data": ["csv", "json", "xml", "yaml", "yml"],
    "csv": ["csv"],
    "json": ["json"],
    "xml": ["xml"],
    # Archives
    "archive": ["zip", "tar", "gz", "rar", "7z"],
    "zip": ["zip"],
}


class WebSearchPro:
    """Main application class for Web Search Pro."""

    def __init__(self, include_darknet: bool = False, verbose: bool = False,
                 translate: bool = False, deep: bool = False,
                 filetypes: List[str] = None):
        self.console = Console()
        self.ui = TerminalUI()
        self.engine_manager = SearchEngineManager()
        self.query_parser = QueryParser()
        self.journal = SearchJournal()

        self.include_darknet = include_darknet
        self.verbose = verbose
        self.translate = translate
        self.deep = deep
        self.filetypes = self._expand_filetypes(filetypes) if filetypes else []

        # Configure search parameters based on mode
        if deep:
            self.max_results_per_engine = 50
            self.console.print("[bold cyan]Deep Search Mode[/bold cyan] - Using all available indexes")
        else:
            self.max_results_per_engine = 30

        if self.filetypes:
            self.console.print(f"[bold magenta]File Type Filter:[/bold magenta] {', '.join(self.filetypes)}")

        self.enabled_engines: Dict[str, bool] = {
            name: True for name in self.engine_manager.clearnet_engines.keys()
        }
        if deep:
            for name in self.engine_manager.extended_engines.keys():
                self.enabled_engines[name] = True
            for name in self.engine_manager.deep_engines.keys():
                self.enabled_engines[name] = True
        if include_darknet:
            for name in self.engine_manager.darknet_engines.keys():
                self.enabled_engines[name] = True

        self.last_results: List[SearchResult] = []
        self.last_query: str = ""

        # Setup signal handler for graceful exit
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.console.print("\n[yellow]Interrupted. Saving session...[/yellow]")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Cleanup and save session."""
        try:
            summary = self.journal.close_session()
            self.ui.print_session_summary(summary)
        except Exception as e:
            self.console.print(f"[red]Error saving session: {e}[/red]")

    def _expand_filetypes(self, filetypes: List[str]) -> List[str]:
        """Expand filetype aliases to actual extensions."""
        expanded = []
        for ft in filetypes:
            ft_lower = ft.lower().lstrip('.')
            if ft_lower in FILETYPE_ALIASES:
                expanded.extend(FILETYPE_ALIASES[ft_lower])
            else:
                expanded.append(ft_lower)
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in expanded if not (x in seen or seen.add(x))]

    def _build_filetype_query(self, query: str) -> str:
        """Add filetype filters to query."""
        if not self.filetypes:
            return query

        if len(self.filetypes) == 1:
            return f"{query} filetype:{self.filetypes[0]}"
        else:
            # Multiple filetypes: use OR
            filetype_parts = [f"filetype:{ft}" for ft in self.filetypes]
            filetype_query = " OR ".join(filetype_parts)
            return f"{query} ({filetype_query})"

    def _translate_query_to_languages(self, query: str) -> Dict[str, str]:
        """
        Translate query into multiple languages for broader search coverage.

        Returns:
            Dict mapping language code to translated query
        """
        if not TRANSLATION_AVAILABLE:
            return {'original': query}

        translations = {'original': query}

        self.console.print("[cyan]Translating query to multiple languages...[/cyan]")

        for lang_code, lang_name in SEARCH_LANGUAGES:
            try:
                translator = GoogleTranslator(source='auto', target=lang_code)
                translated = translator.translate(query)
                if translated and translated.lower() != query.lower():
                    translations[lang_code] = translated
                    if self.verbose:
                        self.console.print(f"  [dim]{lang_name}: {translated}[/dim]")
            except Exception:
                continue

        return translations

    def _build_multilang_query(self, original_query: str) -> str:
        """
        Build a combined query with translations in multiple languages.
        Uses OR to search across all language variants.
        """
        if not self.translate:
            return original_query

        translations = self._translate_query_to_languages(original_query)

        if len(translations) <= 1:
            return original_query

        # Get unique translations
        unique_terms = list(set(translations.values()))

        # Build query with OR between different translations
        # Quote each translation to keep phrases together
        quoted_terms = [f'"{term}"' if ' ' in term else term for term in unique_terms]

        combined_query = " OR ".join(quoted_terms)
        self.console.print(f"[green]Searching in {len(unique_terms)} language variants[/green]")

        return combined_query

    def _translate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Translate result titles and snippets to English for display."""
        if not self.translate or not TRANSLATION_AVAILABLE:
            return results

        self.console.print("[cyan]Translating results to English...[/cyan]")

        translator = GoogleTranslator(source='auto', target='en')

        for result in results:
            try:
                if result.title and len(result.title) > 2:
                    translated_title = translator.translate(result.title)
                    if translated_title:
                        result.title = translated_title
                if result.snippet and len(result.snippet) > 2:
                    translated_snippet = translator.translate(result.snippet)
                    if translated_snippet:
                        result.snippet = translated_snippet
            except Exception:
                continue

        return results

    def search(self, query: str, engines: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Execute a search across configured engines.

        Args:
            query: Search query string
            engines: Optional list of specific engines to use

        Returns:
            List of search results
        """
        # Apply filetype filter first
        search_query = self._build_filetype_query(query)

        # Build multilingual query if translation is enabled
        if self.translate:
            search_query = self._build_multilang_query(search_query)

        # Parse the query
        parsed = self.query_parser.parse(search_query)

        if self.verbose:
            self.ui.print_query_info(parsed.get_display_info())

        # Determine which engines to use
        active_engines = engines or [
            name for name, enabled in self.enabled_engines.items() if enabled
        ]

        # Record search start
        search_id = self.journal.record_search_start(
            query=query,  # Log original query
            engines=active_engines,
            search_type="darknet" if self.include_darknet else "clearnet"
        )

        # Initialize progress tracker
        tracker = SearchProgressTracker(self.console)
        tracker.start(active_engines)

        self.console.print(f"\n[bold]Searching {len(active_engines)} engines...[/bold]\n")

        # Progress callback
        def progress_callback(engine: str, status: str, message: str):
            tracker.update(engine, status, message)
            self.journal.record_search_progress(
                search_id=search_id,
                engine=engine,
                status=status,
                message=message
            )

        # Execute search
        try:
            results = self.engine_manager.search_all(
                query=parsed.to_search_string(),
                include_darknet=self.include_darknet,
                include_deep=self.deep,
                max_results_per_engine=self.max_results_per_engine,
                progress_callback=progress_callback,
                engines=active_engines
            )

            # Record results
            for engine in active_engines:
                engine_results = [r for r in results if engine.lower() in r.engine.lower()]
                if engine_results:
                    self.journal.record_search_result(
                        search_id=search_id,
                        engine=engine,
                        results=[r.to_dict() for r in engine_results]
                    )

            # Translate results if enabled
            results = self._translate_results(results)

            # Store for later export
            self.last_results = results
            self.last_query = query

            # Print summary
            summary = tracker.get_summary()
            self.console.print(f"\n[green]Search complete![/green] "
                             f"Found {summary['total_results']} results "
                             f"in {summary['elapsed_seconds']:.1f}s")

            return results

        except SearchError as e:
            self.journal.record_error("search", str(e))
            self.ui.print_error("Search failed", str(e))
            return []

    def export_results(self, format: str = "json") -> Optional[str]:
        """Export last search results to file."""
        if not self.last_results:
            self.ui.print_warning("No results to export. Run a search first.")
            return None

        filepath = self.journal.save_results_to_file(
            query=self.last_query,
            results=[r.to_dict() for r in self.last_results],
            format=format
        )

        self.ui.print_export_success(str(filepath), format)
        return str(filepath)

    def handle_command(self, command: str) -> bool:
        """
        Handle special commands.

        Returns:
            True if should continue, False if should exit
        """
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/quit" or cmd == "/exit" or cmd == "/q":
            return False

        elif cmd == "/help" or cmd == "/?":
            self.ui.print_help()

        elif cmd == "/clear" or cmd == "/cls":
            self.ui.clear()
            self.ui.print_banner()

        elif cmd == "/engines":
            self.ui.print_engines(self.enabled_engines)

        elif cmd == "/darknet":
            self.include_darknet = not self.include_darknet
            status = "enabled" if self.include_darknet else "disabled"
            self.ui.print_info(f"Darknet search {status}")

            if self.include_darknet:
                for name in self.engine_manager.darknet_engines.keys():
                    self.enabled_engines[name] = True
            else:
                for name in self.engine_manager.darknet_engines.keys():
                    self.enabled_engines[name] = False

        elif cmd == "/tor":
            self.ui.print_info("Checking Tor connection...")
            is_connected = self.engine_manager.check_tor_connection()
            self.ui.print_tor_status(is_connected)

        elif cmd == "/history":
            self.ui.print_search_history()

        elif cmd == "/export":
            format = parts[1] if len(parts) > 1 else "json"
            if format not in ["json", "txt", "md"]:
                self.ui.print_warning(f"Unknown format: {format}. Using json.")
                format = "json"
            self.export_results(format)

        elif cmd == "/select":
            available = list(self.engine_manager.clearnet_engines.keys())
            if self.include_darknet:
                available.extend(self.engine_manager.darknet_engines.keys())
            current = [e for e, enabled in self.enabled_engines.items() if enabled]
            selected = self.ui.select_engines(available, current)

            self.enabled_engines = {name: (name in selected) for name in available}
            self.ui.print_success(f"Selected {len(selected)} engines")

        elif cmd == "/status":
            summary = self.journal.get_session_summary()
            self.ui.print_session_summary(summary)

        elif cmd == "/verbose":
            self.verbose = not self.verbose
            status = "enabled" if self.verbose else "disabled"
            self.ui.print_info(f"Verbose mode {status}")

        else:
            self.ui.print_warning(f"Unknown command: {cmd}. Type /help for help.")

        return True

    def run_interactive(self):
        """Run interactive search loop."""
        self.ui.clear()

        # Check Tor status and show in banner
        tor_available = self.engine_manager.check_tor_connection()
        self.ui.print_banner(tor_available=tor_available)

        self.ui.print_info("Type a search query or /help for commands")
        self.ui.print_info(f"Session ID: {self.journal.session_id}")

        while True:
            try:
                query = self.ui.get_search_input()

                if not query:
                    continue

                if query.startswith("/"):
                    if not self.handle_command(query):
                        break
                    continue

                # Execute search
                results = self.search(query)

                # Display results
                self.ui.print_results(results, query)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /quit to exit[/yellow]")
            except Exception as e:
                self.ui.print_error("Unexpected error", str(e))
                self.journal.record_error("runtime", str(e))

        self._cleanup()

    def run_single_search(self, query: str, output_format: str = "json"):
        """Run a single search and exit."""
        # Check and show Tor status
        tor_available = self.engine_manager.check_tor_connection()
        tor_status = "[green]ONLINE[/green]" if tor_available else "[red]OFFLINE[/red]"
        self.console.print(f"[dim]Darknet: {tor_status}[/dim]")

        if self.include_darknet and not tor_available:
            self.ui.print_tor_setup_instructions()

        self.console.print(f"\n[bold]Searching for:[/bold] {query}\n")

        results = self.search(query)

        if results:
            self.ui.print_results(results, query)

            # Auto-export
            filepath = self.export_results(output_format)
            if filepath:
                self.console.print(f"\n[green]Results saved to:[/green] {filepath}")

        self._cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Web Search Pro - Advanced Web & Darknet Search Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  websearch.py                           # Interactive mode
  websearch.py "zeiss microscope"        # Single search
  websearch.py -d "onion site"           # Include darknet
  websearch.py -o md "query"             # Export as markdown
  websearch.py -t "machine learning"     # Multi-language search
  websearch.py --deep "research topic"   # Deep search (17 engines)
  websearch.py -f pdf "python tutorial"  # Search for PDFs only
  websearch.py -f pdf epub "ebook"       # Search PDFs and EPUBs
  websearch.py -f image "wallpaper"      # Search all image types

File Types (-f):
  Documents:  pdf, doc, docx, docs, word, excel, powerpoint, office
  Ebooks:     epub, mobi, ebook (pdf+epub+mobi)
  Images:     jpg, png, gif, svg, image, photo
  Audio:      mp3, audio, music
  Video:      mp4, video
  Code:       py, python, js, javascript, code
  Data:       csv, json, xml, data
  Archives:   zip, archive

Search Syntax (grep-like):
  term1 term2           Both terms (implicit AND)
  term1 && term2        Both terms (explicit AND)
  term1 || term2        Either term (OR)
  "exact phrase"        Exact phrase match
  -excluded / !term     Exclude term
  NOT term              Exclude term
  site:example.com      Limit to site
  filetype:pdf          File type filter

Search Engines:
  Standard (3):   DuckDuckGo, Bing, Brave
  Extended (5):   Yahoo, Yandex, Qwant, Mojeek, Ecosia
  Deep (9):       Wikipedia, Reddit, GitHub, StackOverflow,
                  HackerNews, Scholar, SemanticScholar, PubMed, Archive.org
  Darknet (3):    Ahmia, Torch, Haystack
        """
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (omit for interactive mode)"
    )
    parser.add_argument(
        "-d", "--darknet",
        action="store_true",
        help="Include darknet search engines"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-o", "--output",
        choices=["json", "txt", "md"],
        default="json",
        help="Output format for results (default: json)"
    )
    parser.add_argument(
        "-e", "--engines",
        nargs="+",
        help="Specific engines to use"
    )
    parser.add_argument(
        "-t", "--translate",
        action="store_true",
        help="Multi-language search (translate query to 12 languages)"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Deep search: use all 17 search engines and specialized indexes"
    )
    parser.add_argument(
        "-f", "--filetype",
        nargs="+",
        metavar="TYPE",
        help="Filter by file type(s): pdf, epub, doc, image, video, etc."
    )

    args = parser.parse_args()

    # Create application
    app = WebSearchPro(
        include_darknet=args.darknet,
        verbose=args.verbose,
        translate=args.translate,
        deep=args.deep,
        filetypes=args.filetype
    )

    # Run
    if args.query:
        app.run_single_search(args.query, args.output)
    else:
        app.run_interactive()


if __name__ == "__main__":
    main()
