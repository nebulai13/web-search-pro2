"""
Configuration for Web Search Pro
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
JOURNAL_DIR = BASE_DIR / "journal"

# Ensure directories exist
for d in [LOGS_DIR, RESULTS_DIR, JOURNAL_DIR]:
    d.mkdir(exist_ok=True)

# Tor Configuration
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051

# Search Configuration
DEFAULT_TIMEOUT = 30
MAX_RESULTS_PER_ENGINE = 50
REQUEST_DELAY = 2  # seconds between requests to avoid rate limiting

# User Agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Search engines configuration
CLEARNET_ENGINES = {
    "duckduckgo": {
        "url": "https://html.duckduckgo.com/html/",
        "enabled": True,
    },
    "google": {
        "url": "https://www.google.com/search",
        "enabled": True,
    },
    "bing": {
        "url": "https://www.bing.com/search",
        "enabled": True,
    },
    "brave": {
        "url": "https://search.brave.com/search",
        "enabled": True,
    },
}

DARKNET_ENGINES = {
    "ahmia": {
        "url": "https://ahmia.fi/search/",
        "enabled": True,
        "requires_tor": False,  # Ahmia is accessible via clearnet
    },
    "torch": {
        "url": "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rber7cqskosuh7vqid.onion/search",
        "enabled": True,
        "requires_tor": True,
    },
    "haystack": {
        "url": "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/",
        "enabled": True,
        "requires_tor": True,
    },
}
