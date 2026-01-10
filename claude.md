# Web Search Pro

## Overview

Web Search Pro is an advanced terminal-based search tool that searches both the clearnet (regular web) and darknet (Tor hidden services). It features comprehensive journaling, progress tracking, and supports advanced search syntax.

## Project Structure

```
web-search-pro/
├── websearch.py        # Main entry point
├── search_engines.py   # Search engine implementations
├── query_parser.py     # Advanced query syntax parser
├── journal.py          # Journaling and logging system
├── terminal_ui.py      # Rich terminal interface
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── claude.md           # This documentation
├── instruction.txt     # Original task requirements
├── logs/               # Search logs (auto-created)
├── results/            # Saved search results (auto-created)
└── journal/            # Search journals (auto-created)
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# For darknet searches, install and start Tor
# macOS:
brew install tor
brew services start tor

# Linux:
sudo apt install tor
sudo systemctl start tor
```

## Usage

### Interactive Mode

```bash
python websearch.py
```

This launches an interactive terminal with:
- Real-time search progress
- Command interface
- Result browsing and export

### Single Search Mode

```bash
# Basic search
python websearch.py "zeiss microscope"

# With darknet
python websearch.py -d "hidden wiki"

# Export as markdown
python websearch.py -o md "neural networks"

# Verbose mode
python websearch.py -v "quantum computing"
```

### Command Line Arguments

| Argument | Description |
|----------|-------------|
| `query` | Search query (omit for interactive mode) |
| `-d, --darknet` | Include darknet search engines |
| `-v, --verbose` | Enable verbose output |
| `-o, --output` | Output format: json, txt, md |
| `-e, --engines` | Specific engines to use |

## Search Syntax

Web Search Pro supports advanced search operators:

| Operator | Example | Description |
|----------|---------|-------------|
| `term1 term2` | `zeiss microscope` | Search for both terms |
| `+term` | `+zeiss +kinevo` | Required term (must appear) |
| `"phrase"` | `"Kinevo 900"` | Exact phrase match |
| `-term` | `zeiss -leica` | Exclude term from results |
| `NOT term` | `zeiss NOT leica` | Alternative exclusion syntax |
| `site:` | `site:zeiss.com` | Limit to specific domain |
| `filetype:` | `filetype:pdf` | Filter by file type |
| `intitle:` | `intitle:microscope` | Term must be in title |
| `inurl:` | `inurl:specs` | Term must be in URL |
| `after:` | `after:2023-01-01` | Results after date |
| `before:` | `before:2024-12-31` | Results before date |

### Example Queries

```
zeiss + "Kinevo 900"
"surgical microscope" site:ncbi.nlm.nih.gov filetype:pdf
neural network -tutorial after:2024-01-01
machine learning OR "deep learning" site:arxiv.org
cybersecurity intitle:guide -beginner
```

## Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/engines` | List available search engines |
| `/darknet` | Toggle darknet search on/off |
| `/tor` | Check Tor connection status |
| `/history` | Show search history |
| `/export [format]` | Export last results (json/txt/md) |
| `/select` | Interactive engine selection |
| `/status` | Show session statistics |
| `/verbose` | Toggle verbose mode |
| `/clear` | Clear screen |
| `/quit` | Exit program |

## Search Engines

### Clearnet Engines

| Engine | Description |
|--------|-------------|
| DuckDuckGo | Privacy-focused search engine |
| Bing | Microsoft's search engine |
| Brave | Privacy-focused with own index |

### Darknet Engines

| Engine | Requires Tor | Description |
|--------|--------------|-------------|
| Ahmia | No | Clearnet gateway to .onion index |
| Torch | Yes | Popular Tor search engine |
| Haystack | Yes | Comprehensive .onion search |

## Journaling System

All searches are automatically journaled:

- **Journal files**: `journal/journal_<session_id>.json`
- **Log files**: `logs/search_<session_id>.log`
- **Results**: `results/results_<query>_<timestamp>.<format>`

### Journal Entry Types

- `search_start`: Records query, engines, search type
- `search_progress`: Records progress updates per engine
- `search_result`: Records results from each engine
- `error`: Records any errors encountered
- `session_end`: Records session summary

## Configuration

Edit `config.py` to customize:

```python
# Tor settings
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050

# Search settings
DEFAULT_TIMEOUT = 30
MAX_RESULTS_PER_ENGINE = 50
REQUEST_DELAY = 2  # Rate limiting

# Enable/disable specific engines
CLEARNET_ENGINES = {
    "duckduckgo": {"enabled": True, ...},
    "google": {"enabled": True, ...},
    ...
}
```

## Output Formats

### JSON (default)
```json
{
  "query": "zeiss microscope",
  "timestamp": "2024-01-15T10:30:00",
  "results_count": 45,
  "results": [
    {
      "title": "ZEISS Microscopy",
      "url": "https://...",
      "snippet": "...",
      "engine": "DuckDuckGo",
      "relevance": 0.95
    }
  ]
}
```

### Markdown
Creates formatted markdown with linked results.

### Text
Simple text format for easy reading.

## API Reference

### SearchEngineManager

```python
from search_engines import SearchEngineManager

manager = SearchEngineManager()

# Check Tor
is_tor = manager.check_tor_connection()

# Search single engine
results = manager.search_single("duckduckgo", "query")

# Search all engines
results = manager.search_all(
    query="search terms",
    include_darknet=True,
    progress_callback=lambda e, s, m: print(f"{e}: {m}")
)
```

### QueryParser

```python
from query_parser import QueryParser

parser = QueryParser()
parsed = parser.parse('zeiss + "Kinevo 900" -leica site:zeiss.com')

print(parsed.required_terms)  # ['zeiss', 'Kinevo 900']
print(parsed.excluded_terms)  # ['leica']
print(parsed.site_filter)     # 'zeiss.com'

# Convert to search string
search_string = parsed.to_search_string(engine="duckduckgo")
```

### SearchJournal

```python
from journal import SearchJournal

journal = SearchJournal()

# Record search
search_id = journal.record_search_start("query", ["engine1"], "clearnet")
journal.record_search_progress(search_id, "engine1", "complete")
journal.record_search_result(search_id, "engine1", results)

# Save results
filepath = journal.save_results_to_file("query", results, format="md")

# Close session
summary = journal.close_session()
```

## Troubleshooting

### Tor Connection Issues

```bash
# Check if Tor is running
ps aux | grep tor

# Start Tor service
# macOS:
brew services start tor
# Linux:
sudo systemctl start tor

# Verify Tor is working
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

### No Results Found

1. Try simpler queries
2. Remove restrictive filters
3. Check spelling
4. Try different engines
5. Verify network connectivity

### Rate Limiting

If you're getting blocked:
1. Increase `REQUEST_DELAY` in config.py
2. Use fewer engines simultaneously
3. Wait between searches

## Security Considerations

- **Tor Privacy**: While Tor provides anonymity, your queries may still be logged by exit nodes or search engines
- **Local Logging**: Search journals contain your queries - secure or delete as needed
- **Network**: Clearnet searches reveal your IP to search engines
- **Legal**: Ensure compliance with local laws regarding darknet access

## Development

### Adding a New Search Engine

1. Create a class extending `BaseSearchEngine` in `search_engines.py`
2. Implement the `search()` method
3. Add to `SearchEngineManager` in `__init__`
4. Add configuration in `config.py`

```python
class NewEngineSearch(BaseSearchEngine):
    def __init__(self):
        super().__init__("NewEngine", "https://example.com/search")

    def search(self, query, max_results=20, progress_callback=None):
        # Implementation
        pass
```

### Running Tests

```bash
python -m pytest tests/
```

## License

MIT License - See LICENSE file for details.

## Version History

- **1.0.0** - Initial release
  - Clearnet search (DuckDuckGo, Bing, Brave)
  - Darknet search (Ahmia, Torch, Haystack)
  - Advanced query syntax
  - Journaling system
  - Rich terminal UI
