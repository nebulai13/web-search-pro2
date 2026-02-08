"""
Configuration for Web Search Pro
Supports YAML configuration file with fallback to defaults.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Base directories
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
RESULTS_DIR = BASE_DIR / "results"
JOURNAL_DIR = BASE_DIR / "journal"
SESSIONS_DIR = BASE_DIR / "sessions"

# Ensure directories exist
for d in [CONFIG_DIR, LOGS_DIR, RESULTS_DIR, JOURNAL_DIR, SESSIONS_DIR]:
    d.mkdir(exist_ok=True)


class ConfigLoader:
    """Loads and manages configuration from YAML file with defaults."""
    
    _instance: Optional['ConfigLoader'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from YAML file."""
        config_file = CONFIG_DIR / "websearchpro.yaml"
        
        if YAML_AVAILABLE and config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'search.timeout')."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()


# Global config loader instance
_config = ConfigLoader()


def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value."""
    return _config.get(key, default)


def reload_config():
    """Reload configuration from file."""
    _config.reload()


# Tor Configuration (with YAML fallback)
TOR_SOCKS_HOST = get_config('sources.darknet.tor.socks_host', "127.0.0.1")
TOR_SOCKS_PORT = get_config('sources.darknet.tor.socks_port', 9050)
TOR_CONTROL_PORT = get_config('sources.darknet.tor.control_port', 9051)

# Search Configuration
DEFAULT_TIMEOUT = get_config('search.default_timeout', 600)
MAX_RESULTS_PER_ENGINE = get_config('search.max_results_per_engine', 50)
REQUEST_DELAY = get_config('search.request_delay', 2)

# User Agent rotation
USER_AGENTS = get_config('user_agents', [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
])

# Search engines configuration
CLEARNET_ENGINES = {
    "duckduckgo": {
        "url": get_config('sources.clearnet.duckduckgo.url', "https://html.duckduckgo.com/html/"),
        "enabled": get_config('sources.clearnet.duckduckgo.enabled', True),
    },
    "google": {
        "url": "https://www.google.com/search",
        "enabled": True,
    },
    "bing": {
        "url": get_config('sources.clearnet.bing.url', "https://www.bing.com/search"),
        "enabled": get_config('sources.clearnet.bing.enabled', True),
    },
    "brave": {
        "url": get_config('sources.clearnet.brave.url', "https://search.brave.com/search"),
        "enabled": get_config('sources.clearnet.brave.enabled', True),
    },
}

DARKNET_ENGINES = {
    "ahmia": {
        "url": get_config('sources.darknet.tor.ahmia.url', "https://ahmia.fi/search/"),
        "enabled": get_config('sources.darknet.tor.ahmia.enabled', True),
        "requires_tor": False,  # Ahmia is accessible via clearnet
    },
    "torch": {
        "url": get_config('sources.darknet.tor.torch.url', 
                         "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rber7cqskosuh7vqid.onion/search"),
        "enabled": get_config('sources.darknet.tor.torch.enabled', True),
        "requires_tor": True,
    },
    "haystack": {
        "url": get_config('sources.darknet.tor.haystack.url',
                         "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/"),
        "enabled": get_config('sources.darknet.tor.haystack.enabled', True),
        "requires_tor": True,
    },
}

# I2P Configuration
I2P_ENABLED = get_config('sources.darknet.i2p.enabled', False)
I2P_PROXY_HOST = get_config('sources.darknet.i2p.router_host', "127.0.0.1")
I2P_PROXY_PORT = get_config('sources.darknet.i2p.http_proxy_port', 4444)

# State management
STATE_ENABLED = get_config('state.enabled', True)
CHECKPOINT_DIR = SESSIONS_DIR
AUTO_CHECKPOINT = get_config('state.auto_checkpoint', True)
CHECKPOINT_INTERVAL = get_config('state.checkpoint_interval', 60)

# Ranking configuration
RANKING_ENABLED = get_config('results.ranking.enabled', True)
RANKING_WEIGHTS = get_config('results.ranking.weights', {
    'source_authority': 25,
    'keyword_density': 15,
    'keyword_proximity': 10,
    'title_match': 20,
    'domain_relevance': 10,
    'content_freshness': 10,
    'content_quality': 10,
})

# Deduplication
DEDUP_ENABLED = get_config('results.deduplication.enabled', True)
DEDUP_METHOD = get_config('results.deduplication.method', 'url_and_content')
DEDUP_THRESHOLD = get_config('results.deduplication.similarity_threshold', 0.85)

# Safety
SAFETY_ENABLED = get_config('safety.enabled', True)
BLACKLIST_FILE = CONFIG_DIR / get_config('safety.url_blacklist_file', 'blacklist.txt').replace('config/', '')

# Report generation
REPORT_AUTO_GENERATE = get_config('reports.auto_generate', True)
REPORT_FORMATS = get_config('reports.formats', ['markdown', 'json'])
