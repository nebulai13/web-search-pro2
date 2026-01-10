# Web Search Pro

An advanced terminal-based search tool for the clearnet and darknet (Tor hidden services) with multi-language support and grep-like boolean syntax.

## Quick Start

```bash
# Install dependencies (use the SAME python you'll run with)
python3 -m pip install -r requirements.txt

# Run interactive mode
python3 websearch.py

# Run a single search
python3 websearch.py "your search query"

# Multi-language search (translates query to 12 languages)
python3 websearch.py -t "artificial intelligence"
```

## Important: Python Version

If you have multiple Python versions installed, make sure to install dependencies using:

```bash
python3 -m pip install -r requirements.txt
```

**NOT** just `pip install` - as this may install to a different Python version.

## Command Line Options

| Option | Description |
|--------|-------------|
| `query` | Search query (omit for interactive mode) |
| `-f, --filetype` | **File type filter**: pdf, epub, image, video, etc. |
| `--deep` | **Deep search**: use all 17 engines + specialized indexes |
| `-t, --translate` | Multi-language search + translate results to English |
| `-d, --darknet` | Include darknet search engines |
| `-v, --verbose` | Show verbose output (query parsing, translations) |
| `-o, --output` | Output format: `json`, `txt`, or `md` |
| `-e, --engines` | Specific engines to use |

## Search Syntax (Grep-like Boolean)

Web Search Pro supports grep-like boolean operators. **These are optional** - simple queries work fine too.

### Boolean Operators

| Operator | Alternative | Example | Description |
|----------|-------------|---------|-------------|
| `AND` | `&&`, `+` | `python AND java` | Both terms required |
| `OR` | `\|\|`, `\|` | `python OR java` | Either term matches |
| `NOT` | `!`, `-` | `python NOT tutorial` | Exclude term |
| `"..."` | | `"machine learning"` | Exact phrase |

### Filter Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `site:` | `site:github.com` | Limit to domain |
| `filetype:` | `filetype:pdf` | Filter by file type |
| `intitle:` | `intitle:guide` | Term must be in title |
| `inurl:` | `inurl:docs` | Term must be in URL |
| `after:` | `after:2024-01-01` | Results after date |
| `before:` | `before:2024-12-31` | Results before date |

### Example Queries

```bash
# Simple search (implicit AND)
python3 websearch.py "python tutorial"

# Grep-style AND
python3 websearch.py "python && machine learning"

# Grep-style OR
python3 websearch.py "python || java || rust"

# Exclude terms
python3 websearch.py "python tutorial -beginner"
python3 websearch.py "python NOT beginner"
python3 websearch.py "python !beginner"

# Exact phrase with exclusion
python3 websearch.py '"machine learning" && -tutorial'

# Complex query
python3 websearch.py '"neural network" OR "deep learning" site:arxiv.org filetype:pdf'

# Multiple OR groups
python3 websearch.py "AI || ML && python || java"
```

## File Type Search (-f, --filetype)

Search for specific file types using the `-f` or `--filetype` flag.

### Usage

```bash
# Search for PDFs
python3 websearch.py -f pdf "python tutorial"

# Search for multiple types
python3 websearch.py -f pdf epub "programming ebook"

# Use type aliases (expands to multiple extensions)
python3 websearch.py -f image "nature wallpaper"   # jpg, png, gif, webp, svg...
python3 websearch.py -f ebook "science fiction"    # pdf, epub, mobi, azw3
python3 websearch.py -f video "documentary"        # mp4, mkv, avi, mov...

# Combine with other flags
python3 websearch.py -f pdf --deep "machine learning"
python3 websearch.py -f pdf -t "künstliche Intelligenz"
```

### Supported File Types and Aliases

| Type | Alias | Extensions |
|------|-------|------------|
| **Documents** | `pdf` | pdf |
| | `doc` | doc, docx |
| | `docs` | doc, docx, pdf, odt, rtf |
| | `word` | doc, docx |
| | `excel` | xls, xlsx |
| | `powerpoint` | ppt, pptx |
| | `office` | doc, docx, xls, xlsx, ppt, pptx |
| **Ebooks** | `epub` | epub |
| | `mobi` | mobi |
| | `ebook` | pdf, epub, mobi, azw3 |
| **Images** | `jpg` | jpg, jpeg |
| | `png` | png |
| | `gif` | gif |
| | `svg` | svg |
| | `image` | jpg, jpeg, png, gif, webp, svg, bmp |
| | `photo` | jpg, jpeg, png, raw, cr2, nef |
| **Audio** | `mp3` | mp3 |
| | `audio` | mp3, wav, flac, ogg, m4a, aac |
| | `music` | mp3, flac, ogg, m4a |
| **Video** | `mp4` | mp4 |
| | `video` | mp4, mkv, avi, mov, webm, wmv |
| **Code** | `python` | py, ipynb |
| | `javascript` | js, ts, jsx, tsx |
| | `code` | py, js, ts, java, cpp, c, h, go, rs, rb |
| **Data** | `csv` | csv |
| | `json` | json |
| | `xml` | xml |
| | `data` | csv, json, xml, yaml, yml |
| **Archives** | `zip` | zip |
| | `archive` | zip, tar, gz, rar, 7z |

### Examples

```bash
# Find research papers in PDF format
python3 websearch.py -f pdf "quantum computing research"

# Find ebooks about programming
python3 websearch.py -f ebook "learn python programming"

# Find high-res images
python3 websearch.py -f image "4k wallpaper landscape"

# Find datasets
python3 websearch.py -f csv json "machine learning dataset"

# Find source code
python3 websearch.py -f code "sorting algorithm implementation"
```

## Deep Search Mode (--deep)

The `--deep` flag enables comprehensive searching across all 17 search engines and specialized indexes.

### What Deep Search Does

1. **Uses all search engines** (17 total instead of 3)
2. **Searches specialized indexes** for:
   - Academic papers (Google Scholar, Semantic Scholar, PubMed)
   - Code repositories (GitHub)
   - Q&A sites (StackOverflow)
   - Discussions (Reddit, Hacker News)
   - Encyclopedias (Wikipedia)
   - Archives (Internet Archive)
3. **Increases results per engine** from 30 to 50
4. **Takes longer** but finds more comprehensive results

### Usage

```bash
# Deep search for a research topic
python3 websearch.py --deep "quantum computing applications"

# Combine with translation for global academic search
python3 websearch.py --deep -t "CRISPR gene editing"

# Deep search with verbose output
python3 websearch.py --deep -v "machine learning optimization"

# Deep search + darknet
python3 websearch.py --deep -d "privacy tools"
```

### When to Use Deep Search

- **Research**: Finding academic papers, citations
- **Code**: Finding libraries, frameworks, examples
- **Troubleshooting**: Finding StackOverflow answers
- **Comprehensive**: When you need results from many sources
- **Obscure topics**: When standard search doesn't find enough

### Time Comparison

| Mode | Engines | Approx. Time |
|------|---------|--------------|
| Standard | 3 | ~10 seconds |
| Deep | 17 | ~60-90 seconds |
| Deep + Darknet | 20 | ~90-120 seconds |

## Multi-Language Translation (-t)

The `-t` or `--translate` flag enables powerful multi-language search:

### How It Works

1. **Query Translation**: Your search query is automatically translated into 12 languages:
   - English, German, French, Spanish, Italian, Portuguese
   - Russian, Chinese, Japanese, Korean, Arabic, Dutch

2. **Expanded Search**: All translations are combined with OR operators to find results in any language

3. **Result Translation**: Found results are translated back to English for easy reading

### Usage Examples

```bash
# Search "artificial intelligence" in all languages
python3 websearch.py -t "artificial intelligence"

# Verbose mode shows all translations
python3 websearch.py -t -v "machine learning"

# Output:
# Translating query to multiple languages...
#   German: maschinelles Lernen
#   French: apprentissage automatique
#   Spanish: aprendizaje automático
#   Chinese: 机器学习
#   Japanese: 機械学習
#   ...
# Searching in 10 language variants

# Search in your native language, find global results
python3 websearch.py -t "künstliche Intelligenz"
python3 websearch.py -t "人工智能"
python3 websearch.py -t "inteligencia artificial"
```

### Benefits

- Find research papers in any language
- Discover international sources
- Break language barriers in search
- Results displayed in English for readability

## Interactive Mode

```bash
python3 websearch.py
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/engines` | List available search engines |
| `/darknet` | Toggle darknet search on/off |
| `/tor` | Check Tor connection status |
| `/history` | Show search history |
| `/export [format]` | Export last results (json/txt/md) |
| `/status` | Show session statistics |
| `/verbose` | Toggle verbose mode |
| `/clear` | Clear screen |
| `/quit` | Exit program |

## Search Engines

Web Search Pro supports **17 search engines** across 4 categories.

### Standard Engines (Default - 3 engines)
Used in normal mode. Fast and reliable.

| Engine | Description |
|--------|-------------|
| **DuckDuckGo** | Privacy-focused search |
| **Bing** | Microsoft's search engine |
| **Brave** | Privacy-focused with independent index |

### Extended Engines (--deep mode - 5 engines)
Additional general search engines for broader coverage.

| Engine | Description |
|--------|-------------|
| **Yahoo** | Yahoo search |
| **Yandex** | Russian search engine (good for Eastern European content) |
| **Qwant** | European privacy-focused search |
| **Mojeek** | UK-based independent index |
| **Ecosia** | Bing-based, plants trees |

### Deep/Specialized Engines (--deep mode - 9 engines)
Specialized indexes for specific content types.

| Engine | Content Type | Description |
|--------|--------------|-------------|
| **Wikipedia** | Encyclopedia | Wikipedia articles |
| **Reddit** | Discussions | Reddit posts and communities |
| **GitHub** | Code | Open source repositories |
| **StackOverflow** | Q&A | Programming questions |
| **HackerNews** | Tech News | Tech/startup discussions |
| **GoogleScholar** | Academic | Research papers |
| **SemanticScholar** | Academic | AI-powered paper search |
| **PubMed** | Medical | Medical/life sciences papers |
| **Archive.org** | Archives | Internet Archive content |

### Darknet Engines (-d flag - 3 engines)
Tor hidden services.

| Engine | Requires Tor | Description |
|--------|--------------|-------------|
| **Ahmia** | No | Clearnet gateway to .onion index |
| **Torch** | Yes | Popular Tor search engine |
| **Haystack** | Yes | Comprehensive .onion search |

## Darknet Search Setup

To search .onion sites (Torch, Haystack), you need Tor running:

```bash
# macOS
brew install tor
brew services start tor

# Linux (Debian/Ubuntu)
sudo apt install tor
sudo systemctl start tor

# Linux (Fedora/RHEL)
sudo dnf install tor
sudo systemctl start tor
```

Then run with the `-d` flag:
```bash
python3 websearch.py -d "search query"
```

The banner shows Tor status on startup:
```
╔═══════════════════════════════════════════════════════════════════╗
║                    WEB SEARCH PRO v1.0                            ║
╠═══════════════════════════════════════════════════════════════════╣
║  Clearnet:  READY                                                 ║
║  Darknet:   ONLINE / OFFLINE                                      ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Output Files

All searches are automatically logged:

- **Log file**: `<query>_<timestamp>.log` - Saved in current directory with full URLs
- **Journal**: `journal/journal_<session_id>.json` - Complete activity log
- **Results**: `results/results_<query>_<timestamp>.<format>` - Exported results

### Log File Format

```
Search Results: python programming
Timestamp: 2024-01-15T10:30:00
Total Results: 25
================================================================================

[1] Python Tutorial - W3Schools
    Source: DuckDuckGo
    URL: https://www.w3schools.com/python/
    Snippet: Learn Python programming...

[2] Welcome to Python.org
    Source: Bing
    URL: https://www.python.org/
    Snippet: The official Python website...
```

## Progress Tracking

Real-time progress updates during searches:

```
  [  0.0s] manager: [1/3] Starting duckduckgo...
  [  0.0s] DuckDuckGo: Initiating search...
  [  0.9s] DuckDuckGo: Parsing results...
  [  0.9s] DuckDuckGo: Found 10 results
  [  2.9s] manager: [2/3] Starting bing...
  ...
```

## Troubleshooting

### "No module named 'requests'"

You installed packages for a different Python version. Fix with:
```bash
python3 -m pip install -r requirements.txt
```

### Tor Connection Issues

```bash
# Check if Tor is running
ps aux | grep tor

# Start Tor
brew services start tor  # macOS
sudo systemctl start tor # Linux

# Verify Tor works
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

### Rate Limiting / No Results

- Increase delay between requests in `config.py` (`REQUEST_DELAY`)
- Use fewer engines (`-e duckduckgo bing`)
- Try simpler queries
- Wait between searches

### Translation Not Working

```bash
# Ensure deep-translator is installed
python3 -m pip install deep-translator
```

## Configuration

Edit `config.py` to customize:

```python
# Tor settings
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050

# Search settings
DEFAULT_TIMEOUT = 30
MAX_RESULTS_PER_ENGINE = 50
REQUEST_DELAY = 2  # seconds between engines
```

## Files

```
web-search-pro/
├── websearch.py        # Main entry point
├── search_engines.py   # Search engine implementations
├── query_parser.py     # Query syntax parser (grep-like boolean)
├── journal.py          # Journaling system
├── terminal_ui.py      # Terminal interface
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── README.md           # This file
├── claude.md           # Full API documentation
├── journal/            # Search journals (auto-created)
├── logs/               # Log files (auto-created)
└── results/            # Saved results (auto-created)
```

## Examples

```bash
# Basic search
python3 websearch.py "quantum computing"

# Multi-language search for research
python3 websearch.py -t "CRISPR gene editing" -v

# Find PDFs on a specific site
python3 websearch.py "machine learning site:arxiv.org filetype:pdf"

# Grep-style complex query
python3 websearch.py '"deep learning" || "neural network" && python -tensorflow'

# Darknet search
python3 websearch.py -d "privacy tools"

# Export results as markdown
python3 websearch.py -o md "rust programming tutorial"

# Combine all options
python3 websearch.py -t -v -d -o md "cybersecurity best practices"
```

## License

MIT License
