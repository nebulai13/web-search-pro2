"""
I2P Client for WebSearchPro
Provides I2P network integration for searching eepsites.
"""
import socket
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urljoin

import requests

from config import I2P_PROXY_HOST, I2P_PROXY_PORT, I2P_ENABLED


class I2PClient:
    """
    Client for I2P network communication.
    
    Supports:
    - HTTP proxy through I2P router
    - Eepsite access (.i2p domains)
    - Connection health checking
    """
    
    # Known I2P search engines
    I2P_SEARCH_ENGINES = {
        'i2psearch': {
            'name': 'I2P Search',
            'url': 'http://i2psearch.i2p/',
            'search_path': '/search?q={query}',
        },
        'legwork': {
            'name': 'Legwork',
            'url': 'http://legwork.i2p/',
            'search_path': '/yacysearch.html?query={query}',
        },
        'epsilon': {
            'name': 'Epsilon',
            'url': 'http://epsilon.i2p/',
            'search_path': '/search?q={query}',
        },
    }
    
    def __init__(self, 
                 proxy_host: str = None,
                 proxy_port: int = None,
                 timeout: int = 60):
        """
        Initialize I2P client.
        
        Args:
            proxy_host: I2P HTTP proxy host
            proxy_port: I2P HTTP proxy port
            timeout: Request timeout in seconds
        """
        self.proxy_host = proxy_host or I2P_PROXY_HOST
        self.proxy_port = proxy_port or I2P_PROXY_PORT
        self.timeout = timeout
        self.enabled = I2P_ENABLED
        
        self._session = None
        self._is_connected = False
    
    @property
    def proxy_url(self) -> str:
        """Get proxy URL."""
        return f"http://{self.proxy_host}:{self.proxy_port}"
    
    @property
    def session(self) -> requests.Session:
        """Get or create requests session with I2P proxy."""
        if self._session is None:
            self._session = requests.Session()
            self._session.proxies = {
                'http': self.proxy_url,
                'https': self.proxy_url,
            }
            self._session.headers.update({
                'User-Agent': 'WebSearchPro/2.0 I2P Client',
            })
        return self._session
    
    def check_connection(self) -> bool:
        """
        Check if I2P connection is available.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try to connect to proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.proxy_host, self.proxy_port))
            sock.close()
            
            if result != 0:
                self._is_connected = False
                return False
            
            # Try to access I2P router console (optional)
            try:
                response = self.session.get(
                    'http://127.0.0.1:7657/',
                    timeout=10
                )
                self._is_connected = response.status_code == 200
            except Exception:
                # Proxy is up but console might not be accessible
                self._is_connected = True
            
            return self._is_connected
            
        except Exception:
            self._is_connected = False
            return False
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._is_connected
    
    def get_eepsite(self, url: str, timeout: int = None) -> Optional[requests.Response]:
        """
        Fetch an eepsite (.i2p domain).
        
        Args:
            url: Eepsite URL (must be .i2p domain)
            timeout: Request timeout
            
        Returns:
            Response object or None on failure
        """
        if not self.is_connected and not self.check_connection():
            return None
        
        try:
            response = self.session.get(
                url,
                timeout=timeout or self.timeout,
                allow_redirects=True,
            )
            return response
        except Exception:
            return None
    
    def search(self, 
               query: str,
               engine: str = 'i2psearch',
               max_results: int = 20,
               progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        Search I2P network using search engine.
        
        Args:
            query: Search query
            engine: Search engine to use
            max_results: Maximum results to return
            progress_callback: Progress callback function
            
        Returns:
            List of search results
        """
        if not self.enabled:
            return []
        
        if engine not in self.I2P_SEARCH_ENGINES:
            engine = 'i2psearch'
        
        engine_config = self.I2P_SEARCH_ENGINES[engine]
        
        if progress_callback:
            progress_callback("starting", f"Connecting to {engine_config['name']}...")
        
        if not self.check_connection():
            if progress_callback:
                progress_callback("error", "I2P connection not available")
            return []
        
        try:
            # Build search URL
            search_url = urljoin(
                engine_config['url'],
                engine_config['search_path'].format(query=query)
            )
            
            if progress_callback:
                progress_callback("searching", f"Searching {engine_config['name']}...")
            
            # Make request
            response = self.session.get(search_url, timeout=self.timeout)
            
            if response.status_code != 200:
                if progress_callback:
                    progress_callback("error", f"HTTP {response.status_code}")
                return []
            
            # Parse results
            results = self._parse_search_results(response.text, engine, max_results)
            
            if progress_callback:
                progress_callback("complete", f"Found {len(results)} results")
            
            return results
            
        except Exception as e:
            if progress_callback:
                progress_callback("error", str(e))
            return []
    
    def _parse_search_results(self, 
                              html: str, 
                              engine: str,
                              max_results: int) -> List[Dict[str, Any]]:
        """Parse search results from HTML."""
        # Basic parser - would need engine-specific parsing
        from bs4 import BeautifulSoup
        
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Generic parsing - look for links
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Only include .i2p links
            if '.i2p' not in href:
                continue
            
            title = link.get_text(strip=True) or href
            
            # Skip navigation links
            if len(title) < 5 or title.lower() in ('home', 'search', 'next', 'prev'):
                continue
            
            results.append({
                'title': title[:200],
                'url': href if href.startswith('http') else f'http://{href}',
                'snippet': '',
                'engine': f'I2P/{engine}',
                'is_darknet': True,
                'network': 'i2p',
            })
            
            if len(results) >= max_results:
                break
        
        return results
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get I2P connection information."""
        return {
            'enabled': self.enabled,
            'connected': self.is_connected,
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port,
            'proxy_url': self.proxy_url,
        }
    
    def close(self):
        """Close the client session."""
        if self._session:
            self._session.close()
            self._session = None
        self._is_connected = False


class I2PSearchEngine:
    """
    I2P Search Engine wrapper for SearchEngineManager compatibility.
    """
    
    def __init__(self, name: str = "I2P Search"):
        self.name = name
        self.client = I2PClient()
    
    def search(self, 
               query: str, 
               max_results: int = 20,
               progress_callback: Callable = None) -> List[Dict[str, Any]]:
        """
        Execute I2P search.
        
        Args:
            query: Search query
            max_results: Maximum results
            progress_callback: Progress callback
            
        Returns:
            List of search results
        """
        return self.client.search(
            query=query,
            max_results=max_results,
            progress_callback=progress_callback
        )
    
    def check_connection(self) -> bool:
        """Check I2P connection."""
        return self.client.check_connection()
    
    @property
    def is_available(self) -> bool:
        """Check if I2P search is available."""
        return self.client.enabled and self.client.is_connected
