"""
Search Engines Module for Web Search Pro
Handles both clearnet (WWW) and darknet (Tor) searches.
"""
import asyncio
import random
import re
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

try:
    import aiohttp
    from aiohttp_socks import ProxyConnector
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

from config import (
    TOR_SOCKS_HOST, TOR_SOCKS_PORT, DEFAULT_TIMEOUT,
    USER_AGENTS, REQUEST_DELAY, MAX_RESULTS_PER_ENGINE
)


class SearchResult:
    """Represents a single search result."""

    def __init__(self, title: str, url: str, snippet: str = "",
                 engine: str = "", relevance: float = 0.0):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.engine = engine
        self.relevance = relevance
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "engine": self.engine,
            "relevance": self.relevance,
            "timestamp": self.timestamp
        }


class BaseSearchEngine(ABC):
    """Abstract base class for search engines."""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def _get_user_agent(self) -> str:
        return random.choice(USER_AGENTS)

    @abstractmethod
    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        """Execute search and return results."""
        pass

    def _make_request(self, url: str, params: Dict = None,
                      use_tor: bool = False) -> Optional[requests.Response]:
        """Make HTTP request with optional Tor proxy."""
        try:
            proxies = None
            if use_tor:
                proxies = {
                    "http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
                    "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}"
                }

            self.session.headers["User-Agent"] = self._get_user_agent()
            response = self.session.get(
                url,
                params=params,
                proxies=proxies,
                timeout=DEFAULT_TIMEOUT,
                verify=not use_tor  # Skip SSL verification for .onion
            )
            response.raise_for_status()
            return response
        except Exception as e:
            raise SearchError(f"Request failed: {str(e)}")


class SearchError(Exception):
    """Custom exception for search errors."""
    pass


# ============= CLEARNET SEARCH ENGINES =============

class DuckDuckGoSearch(BaseSearchEngine):
    """DuckDuckGo HTML search engine."""

    def __init__(self):
        super().__init__("DuckDuckGo", "https://html.duckduckgo.com/html/")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating search...")

        try:
            response = self._make_request(self.base_url, params={"q": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_divs = soup.select(".result")

            for i, div in enumerate(result_divs[:max_results]):
                title_elem = div.select_one(".result__a")
                snippet_elem = div.select_one(".result__snippet")
                url_elem = div.select_one(".result__url")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # DuckDuckGo uses redirect URLs, extract actual URL
                    if "uddg=" in url:
                        url_match = re.search(r"uddg=([^&]+)", url)
                        if url_match:
                            from urllib.parse import unquote
                            url = unquote(url_match.group(1))

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(self.name, "progress",
                                     f"Processed {i + 1}/{len(result_divs[:max_results])} results")

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"DuckDuckGo search failed: {e}")

        return results


class BingSearch(BaseSearchEngine):
    """Bing search engine."""

    def __init__(self):
        super().__init__("Bing", "https://www.bing.com/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating search...")

        try:
            response = self._make_request(self.base_url, params={"q": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("li.b_algo")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("h2 a")
                snippet_elem = item.select_one(".b_caption p")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"Bing search failed: {e}")

        return results


class BraveSearch(BaseSearchEngine):
    """Brave Search engine."""

    def __init__(self):
        super().__init__("Brave", "https://search.brave.com/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating search...")

        try:
            response = self._make_request(self.base_url, params={"q": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select(".snippet")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one(".snippet-title")
                url_elem = item.select_one(".snippet-url")
                snippet_elem = item.select_one(".snippet-description")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = url_elem.get_text(strip=True) if url_elem else ""
                    if not url.startswith("http"):
                        url = "https://" + url
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"Brave search failed: {e}")

        return results


# ============= DARKNET SEARCH ENGINES =============

class AhmiaSearch(BaseSearchEngine):
    """Ahmia.fi - Clearnet gateway to search Tor hidden services."""

    def __init__(self):
        super().__init__("Ahmia", "https://ahmia.fi/search/")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching darknet index...")

        try:
            response = self._make_request(self.base_url, params={"q": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing darknet results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("li.result")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("h4 a")
                snippet_elem = item.select_one("p")
                url_elem = item.select_one(".onion a")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = url_elem.get("href", "") if url_elem else title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=f"{self.name} (Darknet)",
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} darknet results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"Ahmia search failed: {e}")

        return results


class TorchSearch(BaseSearchEngine):
    """Torch - Tor network search engine (requires Tor)."""

    def __init__(self):
        super().__init__("Torch", "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rber7cqskosuh7vqid.onion/search")
        self.requires_tor = True

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Connecting via Tor...")

        try:
            params = {"query": query, "action": "search"}
            response = self._make_request(self.base_url, params=params, use_tor=True)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing Torch results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select(".result")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("a")
                snippet_elem = item.select_one("p")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=f"{self.name} (Tor)",
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} onion results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"Torch search failed: {e}")

        return results


class HaystackSearch(BaseSearchEngine):
    """Haystack - Another Tor search engine."""

    def __init__(self):
        super().__init__("Haystack", "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/")
        self.requires_tor = True

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Connecting via Tor to Haystack...")

        try:
            params = {"q": query}
            response = self._make_request(self.base_url, params=params, use_tor=True)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing Haystack results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select(".result")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("a")
                snippet_elem = item.select_one("p, .description")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=f"{self.name} (Tor)",
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))
            raise SearchError(f"Haystack search failed: {e}")

        return results


# ============= ADDITIONAL CLEARNET ENGINES =============

class YahooSearch(BaseSearchEngine):
    """Yahoo search engine."""

    def __init__(self):
        super().__init__("Yahoo", "https://search.yahoo.com/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating Yahoo search...")

        try:
            response = self._make_request(self.base_url, params={"p": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("div.algo-sr") or soup.select("div.dd.algo")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("h3 a") or item.select_one("a.ac-algo")
                snippet_elem = item.select_one("p") or item.select_one(".compText")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class YandexSearch(BaseSearchEngine):
    """Yandex search engine (Russian)."""

    def __init__(self):
        super().__init__("Yandex", "https://yandex.com/search/")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating Yandex search...")

        try:
            response = self._make_request(self.base_url, params={"text": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("li.serp-item")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("h2 a") or item.select_one("a.organic__url")
                snippet_elem = item.select_one(".organic__content-wrapper") or item.select_one(".text-container")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class QwantSearch(BaseSearchEngine):
    """Qwant search engine (European, privacy-focused)."""

    def __init__(self):
        super().__init__("Qwant", "https://www.qwant.com/")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating Qwant search...")

        try:
            # Qwant uses API
            api_url = "https://api.qwant.com/v3/search/web"
            params = {"q": query, "count": max_results, "locale": "en_US", "offset": 0}
            self.session.headers["Origin"] = "https://www.qwant.com"

            response = self._make_request(api_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            try:
                data = response.json()
                items = data.get("data", {}).get("result", {}).get("items", {}).get("mainline", [])

                for group in items:
                    if group.get("type") == "web":
                        for i, item in enumerate(group.get("items", [])[:max_results]):
                            results.append(SearchResult(
                                title=item.get("title", ""),
                                url=item.get("url", ""),
                                snippet=item.get("desc", ""),
                                engine=self.name,
                                relevance=1.0 - (i / max_results)
                            ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class MojeekSearch(BaseSearchEngine):
    """Mojeek search engine (UK, independent index)."""

    def __init__(self):
        super().__init__("Mojeek", "https://www.mojeek.com/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating Mojeek search...")

        try:
            response = self._make_request(self.base_url, params={"q": query})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("ul.results-standard li")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("a.title")
                snippet_elem = item.select_one("p.s")
                url_elem = item.select_one("a.title")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = url_elem.get("href", "") if url_elem else ""
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class EcosiaSearch(BaseSearchEngine):
    """Ecosia search engine (Bing-based, plants trees)."""

    def __init__(self):
        super().__init__("Ecosia", "https://www.ecosia.org/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Initiating Ecosia search...")

        try:
            response = self._make_request(self.base_url, params={"q": query, "method": "index"})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("div.result")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("a.result-title") or item.select_one("h2 a")
                snippet_elem = item.select_one("p.result-snippet") or item.select_one(".result-body")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} results")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


# ============= DEEP SEARCH ENGINES (Specialized) =============

class GoogleScholarSearch(BaseSearchEngine):
    """Google Scholar for academic papers."""

    def __init__(self):
        super().__init__("GoogleScholar", "https://scholar.google.com/scholar")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching academic papers...")

        try:
            response = self._make_request(self.base_url, params={"q": query, "hl": "en"})
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing academic results...")

            soup = BeautifulSoup(response.text, "lxml")
            result_items = soup.select("div.gs_r.gs_or.gs_scl")

            for i, item in enumerate(result_items[:max_results]):
                title_elem = item.select_one("h3.gs_rt a")
                snippet_elem = item.select_one("div.gs_rs")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=f"[Scholar] {title}",
                        url=url,
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} academic papers")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class ArchiveOrgSearch(BaseSearchEngine):
    """Internet Archive (Wayback Machine) search."""

    def __init__(self):
        super().__init__("Archive.org", "https://archive.org/advancedsearch.php")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching Internet Archive...")

        try:
            params = {
                "q": query,
                "fl[]": ["identifier", "title", "description"],
                "rows": max_results,
                "output": "json"
            }
            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing archive results...")

            try:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])

                for i, doc in enumerate(docs[:max_results]):
                    identifier = doc.get("identifier", "")
                    title = doc.get("title", identifier)
                    description = doc.get("description", "")
                    if isinstance(description, list):
                        description = " ".join(description)

                    results.append(SearchResult(
                        title=f"[Archive] {title}",
                        url=f"https://archive.org/details/{identifier}",
                        snippet=description[:300] if description else "",
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} archived items")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class WikipediaSearch(BaseSearchEngine):
    """Wikipedia search."""

    def __init__(self):
        super().__init__("Wikipedia", "https://en.wikipedia.org/w/api.php")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching Wikipedia...")

        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": max_results,
                "format": "json"
            }
            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing Wikipedia results...")

            try:
                data = response.json()
                items = data.get("query", {}).get("search", [])

                for i, item in enumerate(items):
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    # Clean HTML from snippet
                    snippet = re.sub(r'<[^>]+>', '', snippet)

                    results.append(SearchResult(
                        title=f"[Wikipedia] {title}",
                        url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        snippet=snippet,
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} Wikipedia articles")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class RedditSearch(BaseSearchEngine):
    """Reddit search."""

    def __init__(self):
        super().__init__("Reddit", "https://www.reddit.com/search.json")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching Reddit...")

        try:
            params = {"q": query, "limit": max_results, "sort": "relevance"}
            self.session.headers["User-Agent"] = "Mozilla/5.0 (compatible; WebSearchPro/1.0)"

            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing Reddit posts...")

            try:
                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for i, post in enumerate(posts[:max_results]):
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    subreddit = post_data.get("subreddit", "")
                    selftext = post_data.get("selftext", "")[:200]
                    permalink = post_data.get("permalink", "")

                    results.append(SearchResult(
                        title=f"[r/{subreddit}] {title}",
                        url=f"https://www.reddit.com{permalink}",
                        snippet=selftext if selftext else f"Posted in r/{subreddit}",
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} Reddit posts")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class GitHubSearch(BaseSearchEngine):
    """GitHub repository search."""

    def __init__(self):
        super().__init__("GitHub", "https://api.github.com/search/repositories")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching GitHub repositories...")

        try:
            params = {"q": query, "per_page": max_results, "sort": "stars"}
            self.session.headers["Accept"] = "application/vnd.github.v3+json"

            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing GitHub repos...")

            try:
                data = response.json()
                repos = data.get("items", [])

                for i, repo in enumerate(repos[:max_results]):
                    name = repo.get("full_name", "")
                    description = repo.get("description", "") or ""
                    stars = repo.get("stargazers_count", 0)
                    url = repo.get("html_url", "")

                    results.append(SearchResult(
                        title=f"[GitHub] {name} ⭐{stars}",
                        url=url,
                        snippet=description[:200],
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} GitHub repos")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class StackOverflowSearch(BaseSearchEngine):
    """StackOverflow search."""

    def __init__(self):
        super().__init__("StackOverflow", "https://api.stackexchange.com/2.3/search/advanced")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching StackOverflow...")

        try:
            params = {
                "q": query,
                "pagesize": max_results,
                "order": "desc",
                "sort": "relevance",
                "site": "stackoverflow"
            }
            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing StackOverflow questions...")

            try:
                data = response.json()
                items = data.get("items", [])

                for i, item in enumerate(items[:max_results]):
                    title = item.get("title", "")
                    link = item.get("link", "")
                    score = item.get("score", 0)
                    answered = "✓" if item.get("is_answered") else ""

                    results.append(SearchResult(
                        title=f"[SO {answered}] {title} ({score} votes)",
                        url=link,
                        snippet=f"Tags: {', '.join(item.get('tags', [])[:5])}",
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} StackOverflow questions")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class HackerNewsSearch(BaseSearchEngine):
    """Hacker News search via Algolia API."""

    def __init__(self):
        super().__init__("HackerNews", "https://hn.algolia.com/api/v1/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching Hacker News...")

        try:
            params = {"query": query, "hitsPerPage": max_results}
            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing HN posts...")

            try:
                data = response.json()
                hits = data.get("hits", [])

                for i, hit in enumerate(hits[:max_results]):
                    title = hit.get("title", "") or hit.get("story_title", "")
                    url = hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                    points = hit.get("points", 0)
                    num_comments = hit.get("num_comments", 0)

                    if title:
                        results.append(SearchResult(
                            title=f"[HN] {title} ({points}↑ {num_comments}💬)",
                            url=url,
                            snippet=f"Posted on Hacker News",
                            engine=self.name,
                            relevance=1.0 - (i / max_results)
                        ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} HN posts")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class SemanticScholarSearch(BaseSearchEngine):
    """Semantic Scholar academic search."""

    def __init__(self):
        super().__init__("SemanticScholar", "https://api.semanticscholar.org/graph/v1/paper/search")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching Semantic Scholar...")

        try:
            params = {
                "query": query,
                "limit": max_results,
                "fields": "title,abstract,url,citationCount,year"
            }
            response = self._make_request(self.base_url, params=params)
            if not response:
                return results

            if progress_callback:
                progress_callback(self.name, "parsing", "Parsing academic papers...")

            try:
                data = response.json()
                papers = data.get("data", [])

                for i, paper in enumerate(papers[:max_results]):
                    title = paper.get("title", "")
                    abstract = paper.get("abstract", "") or ""
                    url = paper.get("url", "")
                    citations = paper.get("citationCount", 0)
                    year = paper.get("year", "")

                    results.append(SearchResult(
                        title=f"[Paper {year}] {title} ({citations} citations)",
                        url=url,
                        snippet=abstract[:250] if abstract else "No abstract available",
                        engine=self.name,
                        relevance=1.0 - (i / max_results)
                    ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} papers")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


class PubMedSearch(BaseSearchEngine):
    """PubMed medical/life sciences search."""

    def __init__(self):
        super().__init__("PubMed", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi")

    def search(self, query: str, max_results: int = 20,
               progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        results = []

        if progress_callback:
            progress_callback(self.name, "starting", "Searching PubMed medical database...")

        try:
            # First get IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            response = self._make_request(self.base_url, params=search_params)
            if not response:
                return results

            try:
                data = response.json()
                ids = data.get("esearchresult", {}).get("idlist", [])

                if ids:
                    if progress_callback:
                        progress_callback(self.name, "parsing", f"Fetching {len(ids)} paper details...")

                    # Fetch summaries
                    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    summary_params = {
                        "db": "pubmed",
                        "id": ",".join(ids),
                        "retmode": "json"
                    }
                    summary_response = self._make_request(summary_url, params=summary_params)

                    if summary_response:
                        summary_data = summary_response.json()
                        result_data = summary_data.get("result", {})

                        for i, pmid in enumerate(ids[:max_results]):
                            paper = result_data.get(pmid, {})
                            title = paper.get("title", "")
                            source = paper.get("source", "")
                            pubdate = paper.get("pubdate", "")

                            if title:
                                results.append(SearchResult(
                                    title=f"[PubMed] {title}",
                                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                    snippet=f"Published in {source}, {pubdate}",
                                    engine=self.name,
                                    relevance=1.0 - (i / max_results)
                                ))
            except:
                pass

            if progress_callback:
                progress_callback(self.name, "complete", f"Found {len(results)} medical papers")

        except Exception as e:
            if progress_callback:
                progress_callback(self.name, "error", str(e))

        return results


# ============= SEARCH ENGINE MANAGER =============

class SearchEngineManager:
    """Manages multiple search engines and coordinates searches."""

    def __init__(self):
        # Standard clearnet engines (fast, reliable)
        self.clearnet_engines: Dict[str, BaseSearchEngine] = {
            "duckduckgo": DuckDuckGoSearch(),
            "bing": BingSearch(),
            "brave": BraveSearch(),
        }

        # Extended clearnet engines (for --deep mode)
        self.extended_engines: Dict[str, BaseSearchEngine] = {
            "yahoo": YahooSearch(),
            "yandex": YandexSearch(),
            "qwant": QwantSearch(),
            "mojeek": MojeekSearch(),
            "ecosia": EcosiaSearch(),
        }

        # Deep search engines - specialized indexes (for --deep mode)
        self.deep_engines: Dict[str, BaseSearchEngine] = {
            "wikipedia": WikipediaSearch(),
            "reddit": RedditSearch(),
            "github": GitHubSearch(),
            "stackoverflow": StackOverflowSearch(),
            "hackernews": HackerNewsSearch(),
            "scholar": GoogleScholarSearch(),
            "semantic": SemanticScholarSearch(),
            "pubmed": PubMedSearch(),
            "archive": ArchiveOrgSearch(),
        }

        # Darknet engines
        self.darknet_engines: Dict[str, BaseSearchEngine] = {
            "ahmia": AhmiaSearch(),
            "torch": TorchSearch(),
            "haystack": HaystackSearch(),
        }

        self._tor_available = None

    def check_tor_connection(self) -> bool:
        """Check if Tor is available and connected."""
        if self._tor_available is not None:
            return self._tor_available

        try:
            proxies = {
                "http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
                "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}"
            }
            response = requests.get(
                "https://check.torproject.org/api/ip",
                proxies=proxies,
                timeout=10
            )
            data = response.json()
            self._tor_available = data.get("IsTor", False)
        except:
            self._tor_available = False

        return self._tor_available

    def get_available_engines(self, include_tor: bool = False, include_deep: bool = False) -> List[str]:
        """Get list of available engine names."""
        engines = list(self.clearnet_engines.keys())
        if include_deep:
            engines.extend(self.extended_engines.keys())
            engines.extend(self.deep_engines.keys())
        if include_tor:
            engines.extend(self.darknet_engines.keys())
        return engines

    def get_all_engines(self) -> Dict[str, BaseSearchEngine]:
        """Get all engines as a single dictionary."""
        all_engines = {}
        all_engines.update(self.clearnet_engines)
        all_engines.update(self.extended_engines)
        all_engines.update(self.deep_engines)
        all_engines.update(self.darknet_engines)
        return all_engines

    def search_single(self, engine_name: str, query: str, max_results: int = 20,
                      progress_callback: Optional[Callable] = None) -> List[SearchResult]:
        """Search using a single engine."""
        all_engines = self.get_all_engines()
        engine = all_engines.get(engine_name)
        if not engine:
            raise ValueError(f"Unknown engine: {engine_name}")

        # Check Tor requirement
        if hasattr(engine, 'requires_tor') and engine.requires_tor:
            if not self.check_tor_connection():
                raise SearchError(f"{engine_name} requires Tor connection")

        return engine.search(query, max_results, progress_callback)

    def search_all(self, query: str, include_darknet: bool = False,
                   include_deep: bool = False,
                   max_results_per_engine: int = 20,
                   progress_callback: Optional[Callable] = None,
                   engines: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Search across multiple engines.

        Args:
            query: Search query
            include_darknet: Include darknet engines
            include_deep: Include extended and deep search engines
            max_results_per_engine: Max results per engine
            progress_callback: Callback for progress updates
            engines: Optional list of specific engines to use

        Returns:
            Combined list of search results
        """
        all_results = []

        # Determine which engines to use
        if engines:
            all_available = self.get_all_engines()
            target_engines = {
                name: engine for name, engine in all_available.items()
                if name in engines
            }
        else:
            target_engines = dict(self.clearnet_engines)
            if include_deep:
                target_engines.update(self.extended_engines)
                target_engines.update(self.deep_engines)
            if include_darknet:
                target_engines.update(self.darknet_engines)

        total_engines = len(target_engines)

        for i, (name, engine) in enumerate(target_engines.items()):
            if progress_callback:
                progress_callback("manager", "engine_start",
                                 f"[{i+1}/{total_engines}] Starting {name}...")

            try:
                # Check Tor for darknet engines
                if hasattr(engine, 'requires_tor') and engine.requires_tor:
                    if not self.check_tor_connection():
                        if progress_callback:
                            progress_callback(name, "skipped", "Tor not available")
                        continue

                results = engine.search(query, max_results_per_engine, progress_callback)
                all_results.extend(results)

                if progress_callback:
                    progress_callback("manager", "engine_complete",
                                     f"{name}: {len(results)} results")

                # Rate limiting between engines
                if i < total_engines - 1:
                    time.sleep(REQUEST_DELAY)

            except SearchError as e:
                if progress_callback:
                    progress_callback(name, "error", str(e))
                continue

        # Sort by relevance
        all_results.sort(key=lambda r: r.relevance, reverse=True)

        return all_results
