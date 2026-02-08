"""
Smart Deduplication for WebSearchPro
Removes duplicate and near-duplicate results using URL normalization and content similarity.
"""
import hashlib
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from difflib import SequenceMatcher

from config import DEDUP_THRESHOLD, DEDUP_METHOD


class ResultDeduplicator:
    """
    Intelligent deduplication for search results.
    
    Methods:
    - URL normalization: Canonicalizes URLs to detect duplicates
    - Content hashing: Detects identical content
    - Similarity matching: Finds near-duplicate content
    """
    
    # URL parameters to strip (tracking, session, etc.)
    STRIP_PARAMS = {
        # Tracking parameters
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'dclid',
        'ref', 'referer', 'referrer', 'source',
        # Session parameters
        'session', 'sessionid', 'sid', 'jsessionid',
        # Analytics
        'ga_source', 'ga_medium', 'ga_campaign',
        '_ga', '_gl', '_hsenc', '_hsmi',
        # Social
        'share', 'shared', 'social',
        # Misc
        'timestamp', 'ts', 'nocache', 'cache', 'cb',
        'ver', 'version', 'v',
    }
    
    # Domain aliases (same site, different domains)
    DOMAIN_ALIASES = {
        'www.reddit.com': 'reddit.com',
        'old.reddit.com': 'reddit.com',
        'np.reddit.com': 'reddit.com',
        'm.reddit.com': 'reddit.com',
        'www.twitter.com': 'twitter.com',
        'mobile.twitter.com': 'twitter.com',
        'm.youtube.com': 'youtube.com',
        'www.youtube.com': 'youtube.com',
        'youtu.be': 'youtube.com',
        'en.m.wikipedia.org': 'en.wikipedia.org',
        'amp.reddit.com': 'reddit.com',
    }
    
    def __init__(self, 
                 similarity_threshold: float = None,
                 method: str = None):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Minimum similarity for near-duplicate detection (0.0-1.0)
            method: Deduplication method ('url_only', 'content_only', 'url_and_content')
        """
        self.similarity_threshold = similarity_threshold or DEDUP_THRESHOLD
        self.method = method or DEDUP_METHOD
        
        # Caches
        self._url_cache: Dict[str, str] = {}  # original -> normalized
        self._content_hashes: Set[str] = set()
    
    def deduplicate(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """
        Remove duplicate results.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Tuple of (unique_results, duplicate_results)
        """
        if self.method == 'url_only':
            return self._dedupe_by_url(results)
        elif self.method == 'content_only':
            return self._dedupe_by_content(results)
        else:  # url_and_content
            return self._dedupe_combined(results)
    
    def _dedupe_by_url(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """Deduplicate by normalized URL only."""
        seen_urls: Set[str] = set()
        unique = []
        duplicates = []
        
        for result in results:
            url = result.get('url', '')
            normalized = self.normalize_url(url)
            
            if normalized in seen_urls:
                duplicates.append(result)
            else:
                seen_urls.add(normalized)
                result['normalized_url'] = normalized
                unique.append(result)
        
        return unique, duplicates
    
    def _dedupe_by_content(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """Deduplicate by content hash only."""
        seen_hashes: Set[str] = set()
        unique = []
        duplicates = []
        
        for result in results:
            content_hash = self.hash_content(result)
            
            if content_hash in seen_hashes:
                duplicates.append(result)
            else:
                seen_hashes.add(content_hash)
                result['content_hash'] = content_hash
                unique.append(result)
        
        return unique, duplicates
    
    def _dedupe_combined(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """Deduplicate using both URL and content similarity."""
        seen_urls: Set[str] = set()
        seen_hashes: Set[str] = set()
        unique = []
        duplicates = []
        
        for result in results:
            url = result.get('url', '')
            normalized_url = self.normalize_url(url)
            content_hash = self.hash_content(result)
            
            # Check URL duplicate
            if normalized_url in seen_urls:
                duplicates.append(result)
                continue
            
            # Check content hash duplicate
            if content_hash in seen_hashes:
                duplicates.append(result)
                continue
            
            # Check similarity with existing results
            is_similar = False
            for existing in unique:
                if self._is_similar(result, existing):
                    is_similar = True
                    duplicates.append(result)
                    break
            
            if not is_similar:
                seen_urls.add(normalized_url)
                seen_hashes.add(content_hash)
                result['normalized_url'] = normalized_url
                result['content_hash'] = content_hash
                unique.append(result)
        
        return unique, duplicates
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL to canonical form.
        
        Normalizations:
        - Lowercase scheme and host
        - Remove default ports
        - Remove tracking parameters
        - Normalize trailing slashes
        - Handle domain aliases
        - Remove fragments
        """
        if not url:
            return ''
        
        # Check cache
        if url in self._url_cache:
            return self._url_cache[url]
        
        try:
            parsed = urlparse(url)
            
            # Lowercase scheme and host
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Remove www. prefix
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Apply domain aliases
            if netloc in self.DOMAIN_ALIASES:
                netloc = self.DOMAIN_ALIASES[netloc]
            
            # Remove default ports
            if ':80' in netloc and scheme == 'http':
                netloc = netloc.replace(':80', '')
            if ':443' in netloc and scheme == 'https':
                netloc = netloc.replace(':443', '')
            
            # Normalize path
            path = parsed.path
            # Remove trailing slash (except for root)
            if path != '/' and path.endswith('/'):
                path = path.rstrip('/')
            # Remove index files
            for index in ['/index.html', '/index.htm', '/index.php', '/default.html']:
                if path.endswith(index):
                    path = path[:-len(index)] or '/'
            
            # Filter query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                # Remove tracking parameters
                filtered_params = {
                    k: v for k, v in params.items() 
                    if k.lower() not in self.STRIP_PARAMS
                }
                # Sort parameters for consistency
                query = urlencode(sorted(filtered_params.items()), doseq=True)
            else:
                query = ''
            
            # Reconstruct URL without fragment
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                '',  # params
                query,
                ''   # fragment (removed)
            ))
            
            # Cache and return
            self._url_cache[url] = normalized
            return normalized
            
        except Exception:
            return url
    
    def hash_content(self, result: Dict[str, Any]) -> str:
        """
        Create a hash of result content for duplicate detection.
        
        Uses title and snippet to create a fingerprint.
        """
        title = result.get('title', '').lower().strip()
        snippet = result.get('snippet', '').lower().strip()
        
        # Normalize whitespace
        title = re.sub(r'\s+', ' ', title)
        snippet = re.sub(r'\s+', ' ', snippet)
        
        # Create content string
        content = f"{title}|{snippet}"
        
        # Hash it
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _is_similar(self, result1: Dict[str, Any], result2: Dict[str, Any]) -> bool:
        """
        Check if two results are similar (near-duplicates).
        
        Uses SequenceMatcher for fuzzy matching.
        """
        # Compare titles
        title1 = result1.get('title', '').lower()
        title2 = result2.get('title', '').lower()
        
        title_similarity = SequenceMatcher(None, title1, title2).ratio()
        
        if title_similarity >= self.similarity_threshold:
            return True
        
        # Compare snippets if titles are somewhat similar
        if title_similarity >= 0.5:
            snippet1 = result1.get('snippet', '').lower()
            snippet2 = result2.get('snippet', '').lower()
            
            snippet_similarity = SequenceMatcher(None, snippet1, snippet2).ratio()
            
            # Combined similarity
            combined = (title_similarity * 0.6) + (snippet_similarity * 0.4)
            if combined >= self.similarity_threshold:
                return True
        
        return False
    
    def find_duplicates(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Find all duplicate groups in results.
        
        Returns a dict mapping canonical URL to list of duplicate results.
        """
        groups: Dict[str, List[Dict]] = {}
        
        for result in results:
            url = result.get('url', '')
            normalized = self.normalize_url(url)
            
            if normalized not in groups:
                groups[normalized] = []
            groups[normalized].append(result)
        
        # Filter to only groups with duplicates
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def merge_duplicates(self, duplicates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple duplicate results into one, keeping best data.
        
        Prefers:
        - Longer titles/snippets
        - Higher relevance scores
        - More metadata
        """
        if not duplicates:
            return {}
        
        if len(duplicates) == 1:
            return duplicates[0]
        
        # Sort by relevance score if available, otherwise by snippet length
        sorted_dupes = sorted(
            duplicates,
            key=lambda x: (
                x.get('relevance_score', 0),
                len(x.get('snippet', '')),
                len(x.get('title', ''))
            ),
            reverse=True
        )
        
        # Start with best result
        merged = sorted_dupes[0].copy()
        
        # Merge in data from other duplicates
        for dupe in sorted_dupes[1:]:
            # Keep longer snippet if current is short
            if len(merged.get('snippet', '')) < len(dupe.get('snippet', '')):
                merged['snippet'] = dupe['snippet']
            
            # Keep longer title if current is short
            if len(merged.get('title', '')) < len(dupe.get('title', '')):
                merged['title'] = dupe['title']
            
            # Merge sources
            if 'sources' not in merged:
                merged['sources'] = [merged.get('engine', 'unknown')]
            if dupe.get('engine') and dupe['engine'] not in merged['sources']:
                merged['sources'].append(dupe['engine'])
        
        return merged
    
    def get_dedup_stats(self, original_count: int, unique_count: int) -> Dict[str, Any]:
        """Get deduplication statistics."""
        duplicates_removed = original_count - unique_count
        reduction_percent = (duplicates_removed / original_count * 100) if original_count > 0 else 0
        
        return {
            'original_count': original_count,
            'unique_count': unique_count,
            'duplicates_removed': duplicates_removed,
            'reduction_percent': round(reduction_percent, 1),
            'method': self.method,
            'similarity_threshold': self.similarity_threshold,
        }
    
    def clear_cache(self):
        """Clear internal caches."""
        self._url_cache.clear()
        self._content_hashes.clear()


class URLNormalizer:
    """Utility class for URL normalization only."""
    
    def __init__(self):
        self._deduplicator = ResultDeduplicator()
    
    def normalize(self, url: str) -> str:
        """Normalize a URL."""
        return self._deduplicator.normalize_url(url)
    
    def are_same_page(self, url1: str, url2: str) -> bool:
        """Check if two URLs point to the same page."""
        return self.normalize(url1) == self.normalize(url2)
    
    def get_domain(self, url: str) -> str:
        """Extract normalized domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ''
