"""
Archive Links Module for WebSearchPro
Generates archive.org and archive.is links for search results.
"""
import hashlib
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import requests


class ArchiveLinkGenerator:
    """
    Generates and checks archive links for URLs.
    
    Supports:
    - Wayback Machine (archive.org)
    - Archive.today (archive.is/archive.ph)
    """
    
    WAYBACK_API = "https://archive.org/wayback/available"
    WAYBACK_SAVE = "https://web.archive.org/save/"
    ARCHIVE_IS = "https://archive.is/"
    ARCHIVE_TODAY = "https://archive.today/"
    
    def __init__(self, timeout: int = 10):
        """
        Initialize archive link generator.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'WebSearchPro/2.0 Archive Checker'
        })
    
    def get_wayback_link(self, url: str, check_availability: bool = True) -> Optional[str]:
        """
        Get Wayback Machine link for URL.
        
        Args:
            url: URL to find archive for
            check_availability: Check if archive exists (slower but accurate)
            
        Returns:
            Archive URL or None if not available
        """
        if check_availability:
            try:
                response = self._session.get(
                    self.WAYBACK_API,
                    params={'url': url},
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    snapshot = data.get('archived_snapshots', {}).get('closest', {})
                    if snapshot.get('available'):
                        return snapshot.get('url')
            except Exception:
                pass
            
            return None
        else:
            # Generate potential archive URL without checking
            encoded = quote(url, safe='')
            return f"https://web.archive.org/web/*/{encoded}"
    
    def get_archive_is_link(self, url: str) -> str:
        """
        Get archive.is link for URL.
        
        Args:
            url: URL to create archive link for
            
        Returns:
            Archive.is search URL
        """
        encoded = quote(url, safe='')
        return f"{self.ARCHIVE_IS}{encoded}"
    
    def get_archive_today_link(self, url: str) -> str:
        """
        Get archive.today link for URL.
        
        Args:
            url: URL to create archive link for
            
        Returns:
            Archive.today search URL
        """
        encoded = quote(url, safe='')
        return f"{self.ARCHIVE_TODAY}{encoded}"
    
    def generate_all_archive_links(self, url: str, check_wayback: bool = False) -> Dict[str, str]:
        """
        Generate all archive links for a URL.
        
        Args:
            url: URL to generate links for
            check_wayback: Check Wayback availability (slower)
            
        Returns:
            Dict with archive service names and URLs
        """
        links = {}
        
        # Wayback Machine
        wayback = self.get_wayback_link(url, check_availability=check_wayback)
        if wayback:
            links['wayback_machine'] = wayback
        else:
            # Provide search URL even if no archive found
            links['wayback_search'] = f"https://web.archive.org/web/*/{quote(url, safe='')}"
        
        # Archive.is
        links['archive_is'] = self.get_archive_is_link(url)
        
        # Archive.today (same service, different domain)
        links['archive_today'] = self.get_archive_today_link(url)
        
        return links
    
    def add_archive_links_to_result(self, result: Dict[str, Any], 
                                     check_wayback: bool = False) -> Dict[str, Any]:
        """
        Add archive links to a search result.
        
        Args:
            result: Search result dictionary
            check_wayback: Check Wayback availability
            
        Returns:
            Result with added archive_links field
        """
        url = result.get('url', '')
        if url:
            result['archive_links'] = self.generate_all_archive_links(url, check_wayback)
        return result
    
    def add_archive_links_to_results(self, results: List[Dict[str, Any]],
                                      check_wayback: bool = False,
                                      limit: int = 50) -> List[Dict[str, Any]]:
        """
        Add archive links to multiple results.
        
        Args:
            results: List of search results
            check_wayback: Check Wayback availability (slow for many results)
            limit: Maximum results to process with Wayback check
            
        Returns:
            Results with added archive links
        """
        for i, result in enumerate(results):
            # Only check Wayback for first N results to avoid slowdown
            check = check_wayback and i < limit
            self.add_archive_links_to_result(result, check_wayback=check)
        
        return results
    
    def save_to_wayback(self, url: str) -> Optional[str]:
        """
        Request Wayback Machine to save a URL.
        
        Args:
            url: URL to save
            
        Returns:
            Saved archive URL or None on failure
        """
        try:
            save_url = f"{self.WAYBACK_SAVE}{url}"
            response = self._session.get(save_url, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                # Return the final URL after redirects
                return response.url
        except Exception:
            pass
        
        return None
    
    def batch_check_wayback(self, urls: List[str]) -> Dict[str, Optional[str]]:
        """
        Check multiple URLs against Wayback Machine.
        
        Args:
            urls: List of URLs to check
            
        Returns:
            Dict mapping URLs to their archive URLs (or None)
        """
        results = {}
        
        for url in urls:
            archive_url = self.get_wayback_link(url, check_availability=True)
            results[url] = archive_url
            # Rate limiting
            time.sleep(0.5)
        
        return results
    
    def get_wayback_timestamps(self, url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get available Wayback Machine timestamps for a URL.
        
        Args:
            url: URL to check
            limit: Maximum timestamps to return
            
        Returns:
            List of available snapshots with timestamps
        """
        try:
            cdx_api = f"https://web.archive.org/cdx/search/cdx"
            response = self._session.get(
                cdx_api,
                params={
                    'url': url,
                    'output': 'json',
                    'limit': limit,
                    'fl': 'timestamp,statuscode,mimetype',
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            if len(data) <= 1:  # First row is headers
                return []
            
            headers = data[0]
            snapshots = []
            
            for row in data[1:]:
                snapshot = dict(zip(headers, row))
                timestamp = snapshot.get('timestamp', '')
                
                if timestamp:
                    # Parse timestamp (format: YYYYMMDDHHmmss)
                    try:
                        dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                        snapshot['datetime'] = dt.isoformat()
                        snapshot['archive_url'] = f"https://web.archive.org/web/{timestamp}/{url}"
                        snapshots.append(snapshot)
                    except ValueError:
                        continue
            
            return snapshots
            
        except Exception:
            return []
    
    def close(self):
        """Close the session."""
        self._session.close()


def add_archive_links(results: List[Dict[str, Any]], 
                      check_availability: bool = False) -> List[Dict[str, Any]]:
    """
    Convenience function to add archive links to results.
    
    Args:
        results: List of search results
        check_availability: Check Wayback availability
        
    Returns:
        Results with archive links added
    """
    generator = ArchiveLinkGenerator()
    try:
        return generator.add_archive_links_to_results(results, check_availability)
    finally:
        generator.close()
