# Web Search Pro v2.0

## Overview

Web Search Pro is an advanced terminal-based search tool that searches both the clearnet (regular web) and darknet (Tor hidden services, I2P). It features comprehensive journaling, progress tracking, tiered search orchestration, intelligent result ranking, and supports advanced search syntax with query expansion.

## Project Structure

```
web-search-pro/
├── websearch.py        # Main entry point
├── search_engines.py   # Search engine implementations
├── query_parser.py     # Advanced query syntax parser with expansion
├── journal.py          # Journaling and logging system
├── terminal_ui.py      # Rich terminal interface
├── config.py           # Configuration settings (loads from YAML)
├── requirements.txt    # Python dependencies
├── claude.md           # This documentation
├── config/
│   ├── websearchpro.yaml  # Main YAML configuration
│   └── blacklist.txt      # URL blacklist for safety
├── src/
│   ├── state_manager.py   # Pause/resume & checkpointing
│   ├── orchestrator.py    # Tiered search orchestration
│   ├── ranker.py          # Multi-factor result ranking
│   ├── deduplicator.py    # Intelligent deduplication
│   ├── report_generator.py # Markdown/HTML report generation
│   ├── i2p_client.py      # I2P network integration
│   ├── safety.py          # URL blacklisting & content safety
│   └── archive_links.py   # Archive.org/Archive.is links
├── sessions/           # Search state checkpoints (auto-created)
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
| `-t, --translate` | Multi-language search |
| `--deep` | Deep search using all 17 engines |
| `-f, --filetype` | Filter by file type(s) |

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
| `term*` | `micro*` | Wildcard (any characters) |
| `"phrase"~N` | `"optical quality"~5` | Proximity search (within N words) |
| `term^N` | `kinevo^2` | Boost term importance |

### Example Queries

```
zeiss + "Kinevo 900"
"surgical microscope" site:ncbi.nlm.nih.gov filetype:pdf
neural network -tutorial after:2024-01-01
machine learning OR "deep learning" site:arxiv.org
cybersecurity intitle:guide -beginner
micro* AND "high precision"~5
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

**Tier 2 - Major Engines:**
| Engine | Description |
|--------|-------------|
| DuckDuckGo | Privacy-focused search engine |
| Bing | Microsoft's search engine |
| Brave | Privacy-focused with own index |

**Tier 3 - Extended Engines:**
| Engine | Description |
|--------|-------------|
| Yahoo | General search |
| Yandex | Russian search engine |
| Qwant | European privacy search |
| Mojeek | Independent crawler |
| Ecosia | Environmental search |

**Tier 4 - Specialized Engines:**
| Engine | Description |
|--------|-------------|
| Wikipedia | Encyclopedia search |
| Reddit | Community discussions |
| GitHub | Code repositories |
| StackOverflow | Programming Q&A |
| HackerNews | Tech news |
| Scholar | Academic papers |
| SemanticScholar | AI research papers |
| PubMed | Medical research |
| Archive.org | Historical archives |

### Darknet Engines

**Tier 5 - Tor Hidden Services:**
| Engine | Requires Tor | Description |
|--------|--------------|-------------|
| Ahmia | No | Clearnet gateway to .onion index |
| Torch | Yes | Popular Tor search engine |
| Haystack | Yes | Comprehensive .onion search |

**Tier 6 - I2P Network:**
| Engine | Description |
|--------|-------------|
| I2P Search | Eepsite search engine |

## New v2.0 Features

### State Management (Pause/Resume)

Search sessions can be paused and resumed:

```python
from src.state_manager import StateManager

sm = StateManager()
state = sm.create_session('my_search', 'python tutorial')

# ... search runs ...

# Pause and create checkpoint
checkpoint = sm.pause_search()

# Later, resume
state = sm.resume_search('my_search')
```

### Multi-Factor Result Ranking

Results are scored using multiple factors:

- **Source Authority** (25%): Domain reputation
- **Title Match** (20%): Query terms in title
- **Keyword Density** (15%): Term frequency
- **Keyword Proximity** (10%): Term closeness
- **Domain Relevance** (10%): URL matches query
- **Content Freshness** (10%): Recency
- **Content Quality** (10%): Quality indicators

### Intelligent Deduplication

Removes duplicate results using:
- URL normalization (strips tracking params, www prefix)
- Content hashing (title + snippet)
- Similarity matching (configurable threshold)

### Report Generation

Generate comprehensive reports:

```python
from src.report_generator import ReportGenerator

gen = ReportGenerator()
files = gen.generate_report(
    query='python tutorial',
    results=search_results,
    formats=['markdown', 'html', 'json']
)
```

### Safety Features

URL blacklisting and content filtering:

```python
from src.safety import SafetyChecker

safety = SafetyChecker()
is_safe, reason, score = safety.check_url(url)
safe_results, flagged = safety.filter_results(results)
```

### Archive Links

Automatic archive.org/archive.is link generation:

```python
from src.archive_links import add_archive_links

results = add_archive_links(results)
# Each result now has archive_links field
```

## Configuration

Configuration is now in `config/websearchpro.yaml`:

```yaml
# Search settings
search:
  default_timeout: 600
  max_results_per_engine: 50
  deduplication: true

# Tiered search
tiers:
  tier2_major:
    enabled: true
    engines: [duckduckgo, bing, brave]
  tier5_tor:
    enabled: false  # Enable with --darknet

# Result ranking weights
results:
  ranking:
    weights:
      source_authority: 25
      title_match: 20
      keyword_density: 15

# Safety
safety:
  enabled: true
  url_blacklist_enabled: true
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
