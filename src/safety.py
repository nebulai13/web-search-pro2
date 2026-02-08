"""
Safety Module for WebSearchPro
URL blacklisting, content filtering, and security features.
"""
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from config import BLACKLIST_FILE, SAFETY_ENABLED


class SafetyChecker:
    """
    Security and safety checking for search results.
    
    Features:
    - URL blacklist/whitelist
    - Domain reputation checking
    - Content filtering
    - Malware signature detection (basic)
    """
    
    # Known suspicious TLDs
    SUSPICIOUS_TLDS = {
        '.xyz', '.top', '.club', '.work', '.click', '.link',
        '.gdn', '.men', '.loan', '.win', '.review', '.stream',
    }
    
    # Known phishing patterns in URLs
    PHISHING_PATTERNS = [
        r'login.*verify',
        r'secure.*update',
        r'account.*confirm',
        r'paypal.*login',
        r'bank.*verify',
        r'signin.*secure',
        r'update.*billing',
        r'verify.*identity',
    ]
    
    # Suspicious content patterns
    SUSPICIOUS_CONTENT = [
        r'your account has been (suspended|compromised)',
        r'verify your (identity|account|payment)',
        r'click here (immediately|now|urgently)',
        r'winner.*lottery',
        r'free (iphone|gift|prize)',
        r'limited time offer',
        r'act now before',
        r'wire transfer',
        r'nigerian prince',
    ]
    
    # Safe content indicators
    SAFE_INDICATORS = [
        'https://',
        '.gov',
        '.edu',
        'wikipedia.org',
        'github.com',
        'stackoverflow.com',
    ]
    
    def __init__(self, 
                 blacklist_file: Path = None,
                 enabled: bool = None):
        """
        Initialize safety checker.
        
        Args:
            blacklist_file: Path to blacklist file
            enabled: Whether safety checking is enabled
        """
        self.enabled = enabled if enabled is not None else SAFETY_ENABLED
        self.blacklist_file = blacklist_file or BLACKLIST_FILE
        
        self._blacklist: Set[str] = set()
        self._whitelist: Set[str] = set()
        self._pattern_cache: Dict[str, re.Pattern] = {}
        
        if self.enabled:
            self._load_blacklist()
            self._compile_patterns()
    
    def _load_blacklist(self):
        """Load blacklist from file."""
        if self.blacklist_file and self.blacklist_file.exists():
            with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self._blacklist.add(line.lower())
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        for pattern in self.PHISHING_PATTERNS:
            self._pattern_cache[pattern] = re.compile(pattern, re.IGNORECASE)
        
        for pattern in self.SUSPICIOUS_CONTENT:
            self._pattern_cache[pattern] = re.compile(pattern, re.IGNORECASE)
    
    def add_to_blacklist(self, domain_or_url: str):
        """Add domain or URL to blacklist."""
        domain = self._extract_domain(domain_or_url)
        self._blacklist.add(domain.lower())
    
    def add_to_whitelist(self, domain_or_url: str):
        """Add domain or URL to whitelist."""
        domain = self._extract_domain(domain_or_url)
        self._whitelist.add(domain.lower())
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if '://' not in url:
            url = f'http://{url}'
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url.lower()
    
    def check_url(self, url: str) -> Tuple[bool, str, float]:
        """
        Check if URL is safe.
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (is_safe, reason, safety_score)
            safety_score: 0.0 (dangerous) to 1.0 (safe)
        """
        if not self.enabled:
            return True, "Safety checking disabled", 1.0
        
        if not url:
            return True, "No URL", 0.5
        
        domain = self._extract_domain(url)
        score = 0.7  # Base score
        
        # Check whitelist first
        if domain in self._whitelist:
            return True, "Whitelisted", 1.0
        
        # Check blacklist
        if domain in self._blacklist:
            return False, "Blacklisted domain", 0.0
        
        # Check for partial blacklist matches
        for blacklisted in self._blacklist:
            if blacklisted in domain or domain in blacklisted:
                return False, f"Similar to blacklisted: {blacklisted}", 0.1
        
        # Check suspicious TLDs
        for tld in self.SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                score -= 0.3
        
        # Check phishing patterns
        for pattern in self.PHISHING_PATTERNS:
            if self._pattern_cache.get(pattern, re.compile(pattern)).search(url):
                return False, f"Phishing pattern: {pattern}", 0.1
        
        # Check safe indicators
        for indicator in self.SAFE_INDICATORS:
            if indicator in url.lower():
                score += 0.1
        
        # Check for suspicious URL characteristics
        if self._has_suspicious_url_chars(url):
            score -= 0.2
        
        # Cap score
        score = max(0.0, min(1.0, score))
        
        if score < 0.3:
            return False, "Low safety score", score
        elif score < 0.5:
            return True, "Caution advised", score
        else:
            return True, "Appears safe", score
    
    def check_content(self, title: str, snippet: str) -> Tuple[bool, str, float]:
        """
        Check if content appears safe.
        
        Args:
            title: Result title
            snippet: Result snippet
            
        Returns:
            Tuple of (is_safe, reason, safety_score)
        """
        if not self.enabled:
            return True, "Safety checking disabled", 1.0
        
        content = f"{title} {snippet}".lower()
        score = 0.8  # Base score
        
        # Check suspicious content patterns
        for pattern in self.SUSPICIOUS_CONTENT:
            compiled = self._pattern_cache.get(pattern, re.compile(pattern, re.IGNORECASE))
            if compiled.search(content):
                score -= 0.3
                if score < 0.3:
                    return False, f"Suspicious content: {pattern}", score
        
        # Check for excessive urgency/pressure
        urgency_words = ['urgent', 'immediately', 'now', 'hurry', 'limited', 'act fast']
        urgency_count = sum(1 for word in urgency_words if word in content)
        if urgency_count >= 2:
            score -= 0.2
        
        # Check for all caps (often spam)
        if title and title.isupper() and len(title) > 10:
            score -= 0.2
        
        score = max(0.0, min(1.0, score))
        
        if score < 0.3:
            return False, "Suspicious content detected", score
        elif score < 0.5:
            return True, "Content flagged for review", score
        else:
            return True, "Content appears safe", score
    
    def _has_suspicious_url_chars(self, url: str) -> bool:
        """Check for suspicious characters in URL."""
        suspicious = [
            '@',  # Embedded credentials
            '%00', '%0d', '%0a',  # Null bytes, CRLF
            '\\',  # Backslash
            '..',  # Directory traversal
        ]
        url_lower = url.lower()
        return any(s in url_lower for s in suspicious)
    
    def check_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a search result for safety.
        
        Args:
            result: Search result dictionary
            
        Returns:
            Result with added safety information
        """
        url = result.get('url', '')
        title = result.get('title', '')
        snippet = result.get('snippet', '')
        
        url_safe, url_reason, url_score = self.check_url(url)
        content_safe, content_reason, content_score = self.check_content(title, snippet)
        
        # Combined score
        combined_score = (url_score * 0.6) + (content_score * 0.4)
        is_safe = url_safe and content_safe and combined_score >= 0.4
        
        result['safety'] = {
            'is_safe': is_safe,
            'score': round(combined_score, 2),
            'url_check': {
                'safe': url_safe,
                'reason': url_reason,
                'score': round(url_score, 2),
            },
            'content_check': {
                'safe': content_safe,
                'reason': content_reason,
                'score': round(content_score, 2),
            },
        }
        
        return result
    
    def filter_results(self, 
                       results: List[Dict[str, Any]],
                       min_score: float = 0.3) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter results by safety score.
        
        Args:
            results: List of search results
            min_score: Minimum safety score to pass
            
        Returns:
            Tuple of (safe_results, flagged_results)
        """
        safe = []
        flagged = []
        
        for result in results:
            checked = self.check_result(result)
            safety_score = checked.get('safety', {}).get('score', 1.0)
            
            if safety_score >= min_score:
                safe.append(checked)
            else:
                flagged.append(checked)
        
        return safe, flagged
    
    def get_domain_reputation(self, domain: str) -> Dict[str, Any]:
        """
        Get reputation information for a domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Reputation information
        """
        domain = self._extract_domain(domain)
        
        is_blacklisted = domain in self._blacklist
        is_whitelisted = domain in self._whitelist
        
        # Check TLD
        suspicious_tld = any(domain.endswith(tld) for tld in self.SUSPICIOUS_TLDS)
        
        # Check for safe indicators in domain
        safe_domain = any(
            indicator.replace('https://', '').replace('http://', '') in domain 
            for indicator in self.SAFE_INDICATORS if '://' not in indicator
        )
        
        # Calculate reputation score
        score = 0.5
        if is_whitelisted:
            score = 1.0
        elif is_blacklisted:
            score = 0.0
        else:
            if suspicious_tld:
                score -= 0.2
            if safe_domain:
                score += 0.3
            if domain.endswith('.gov') or domain.endswith('.edu'):
                score += 0.3
        
        return {
            'domain': domain,
            'is_blacklisted': is_blacklisted,
            'is_whitelisted': is_whitelisted,
            'suspicious_tld': suspicious_tld,
            'reputation_score': round(max(0.0, min(1.0, score)), 2),
        }
    
    def save_blacklist(self):
        """Save blacklist to file."""
        if self.blacklist_file:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                f.write("# WebSearchPro URL Blacklist\n")
                f.write("# One domain/URL per line\n\n")
                for entry in sorted(self._blacklist):
                    f.write(f"{entry}\n")
    
    @property
    def blacklist_count(self) -> int:
        """Get number of blacklisted entries."""
        return len(self._blacklist)
    
    @property
    def whitelist_count(self) -> int:
        """Get number of whitelisted entries."""
        return len(self._whitelist)
