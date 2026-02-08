"""
Multi-Factor Result Ranker for WebSearchPro
Calculates relevance scores based on multiple factors.
"""
import re
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass

from config import RANKING_WEIGHTS


@dataclass
class RankingFactors:
    """Individual ranking factor scores."""
    source_authority: float = 0.0
    keyword_density: float = 0.0
    keyword_proximity: float = 0.0
    title_match: float = 0.0
    domain_relevance: float = 0.0
    content_freshness: float = 0.0
    content_quality: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'source_authority': round(self.source_authority, 2),
            'keyword_density': round(self.keyword_density, 2),
            'keyword_proximity': round(self.keyword_proximity, 2),
            'title_match': round(self.title_match, 2),
            'domain_relevance': round(self.domain_relevance, 2),
            'content_freshness': round(self.content_freshness, 2),
            'content_quality': round(self.content_quality, 2),
        }


class ResultRanker:
    """
    Multi-factor relevance ranking for search results.
    
    Factors considered:
    - Source authority: How authoritative is the source
    - Keyword density: How often query terms appear
    - Keyword proximity: How close query terms are to each other
    - Title match: How well title matches query
    - Domain relevance: How relevant the domain is
    - Content freshness: How recent the content is
    - Content quality: Estimated content quality
    """
    
    # Authority scores for known domains (0-100)
    AUTHORITY_SCORES = {
        # Official/Government
        '.gov': 95,
        '.edu': 90,
        '.org': 70,
        
        # Major tech companies
        'github.com': 85,
        'stackoverflow.com': 85,
        'microsoft.com': 80,
        'apple.com': 80,
        'google.com': 80,
        
        # Academic/Research
        'arxiv.org': 90,
        'scholar.google.com': 85,
        'pubmed.ncbi.nlm.nih.gov': 90,
        'ncbi.nlm.nih.gov': 90,
        'researchgate.net': 75,
        'semanticscholar.org': 80,
        'nature.com': 90,
        'sciencedirect.com': 85,
        'ieee.org': 85,
        'acm.org': 85,
        
        # News/Media
        'reuters.com': 80,
        'bbc.com': 75,
        'nytimes.com': 75,
        'washingtonpost.com': 75,
        'theguardian.com': 75,
        
        # Tech/Dev
        'docs.python.org': 85,
        'developer.mozilla.org': 85,
        'w3.org': 90,
        'wikipedia.org': 75,
        
        # Archives
        'archive.org': 80,
        'web.archive.org': 80,
        
        # Community
        'reddit.com': 60,
        'medium.com': 55,
        'dev.to': 60,
        'hackernews.com': 65,
        'news.ycombinator.com': 65,
        
        # Default for unknown
        '_default': 50,
    }
    
    # Quality indicators in content
    QUALITY_POSITIVE = [
        'documentation', 'tutorial', 'guide', 'official',
        'reference', 'manual', 'specification', 'research',
        'peer-reviewed', 'published', 'study', 'analysis',
    ]
    
    QUALITY_NEGATIVE = [
        'spam', 'click here', 'buy now', 'advertisement',
        'sponsored', 'affiliate', 'cheap', 'discount',
        'limited time', 'act now', 'free trial',
    ]
    
    def __init__(self, weights: Optional[Dict[str, int]] = None):
        """
        Initialize ranker with optional custom weights.
        
        Args:
            weights: Dict of factor names to weights (should sum to 100)
        """
        self.weights = weights or RANKING_WEIGHTS
        
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        self.normalized_weights = {k: v / total for k, v in self.weights.items()}
    
    def rank_results(self, results: List[Dict[str, Any]], 
                     query: str,
                     query_terms: List[str] = None) -> List[Dict[str, Any]]:
        """
        Rank a list of search results.
        
        Args:
            results: List of result dictionaries
            query: Original search query
            query_terms: Parsed query terms (extracted if not provided)
            
        Returns:
            Results sorted by relevance score (highest first)
        """
        if not query_terms:
            query_terms = self._extract_terms(query)
        
        ranked = []
        for result in results:
            scored_result = self.score_result(result, query, query_terms)
            ranked.append(scored_result)
        
        # Sort by relevance_score descending
        ranked.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return ranked
    
    def score_result(self, result: Dict[str, Any], 
                     query: str,
                     query_terms: List[str] = None) -> Dict[str, Any]:
        """
        Calculate relevance score for a single result.
        
        Args:
            result: Result dictionary with title, url, snippet, etc.
            query: Original search query
            query_terms: Parsed query terms
            
        Returns:
            Result dict with added relevance_score and ranking_factors
        """
        if not query_terms:
            query_terms = self._extract_terms(query)
        
        factors = RankingFactors()
        
        title = result.get('title', '')
        url = result.get('url', '')
        snippet = result.get('snippet', '')
        engine = result.get('engine', '')
        
        # Calculate each factor
        factors.source_authority = self._score_source_authority(url, engine)
        factors.keyword_density = self._score_keyword_density(title, snippet, query_terms)
        factors.keyword_proximity = self._score_keyword_proximity(title + ' ' + snippet, query_terms)
        factors.title_match = self._score_title_match(title, query_terms, query)
        factors.domain_relevance = self._score_domain_relevance(url, query_terms)
        factors.content_freshness = self._score_freshness(result)
        factors.content_quality = self._score_content_quality(title, snippet, url)
        
        # Calculate weighted composite score
        composite_score = (
            factors.source_authority * self.normalized_weights.get('source_authority', 0.25) +
            factors.keyword_density * self.normalized_weights.get('keyword_density', 0.15) +
            factors.keyword_proximity * self.normalized_weights.get('keyword_proximity', 0.10) +
            factors.title_match * self.normalized_weights.get('title_match', 0.20) +
            factors.domain_relevance * self.normalized_weights.get('domain_relevance', 0.10) +
            factors.content_freshness * self.normalized_weights.get('content_freshness', 0.10) +
            factors.content_quality * self.normalized_weights.get('content_quality', 0.10)
        )
        
        # Add scores to result
        result['relevance_score'] = round(composite_score, 2)
        result['ranking_factors'] = factors.to_dict()
        
        return result
    
    def _extract_terms(self, query: str) -> List[str]:
        """Extract search terms from query."""
        # Remove operators and special syntax
        cleaned = re.sub(r'[+\-"()]', ' ', query)
        cleaned = re.sub(r'\b(AND|OR|NOT|site:|filetype:|intitle:|inurl:|after:|before:)\S*', '', cleaned, flags=re.IGNORECASE)
        
        # Split into terms
        terms = [t.strip().lower() for t in cleaned.split() if t.strip() and len(t.strip()) > 1]
        
        return list(set(terms))
    
    def _score_source_authority(self, url: str, engine: str) -> float:
        """Score based on source authority."""
        if not url:
            return 50.0
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check exact domain match
            if domain in self.AUTHORITY_SCORES:
                return float(self.AUTHORITY_SCORES[domain])
            
            # Check TLD
            for tld, score in self.AUTHORITY_SCORES.items():
                if tld.startswith('.') and domain.endswith(tld):
                    return float(score)
            
            # Check if subdomain of known domain
            for known_domain, score in self.AUTHORITY_SCORES.items():
                if not known_domain.startswith('.') and domain.endswith('.' + known_domain):
                    return float(score) * 0.9  # Slightly lower for subdomains
            
            # Boost for HTTPS
            base_score = float(self.AUTHORITY_SCORES['_default'])
            if parsed.scheme == 'https':
                base_score += 5
            
            return min(base_score, 100.0)
            
        except Exception:
            return 50.0
    
    def _score_keyword_density(self, title: str, snippet: str, terms: List[str]) -> float:
        """Score based on keyword density."""
        if not terms:
            return 50.0
        
        text = (title + ' ' + snippet).lower()
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.0
        
        # Count term occurrences
        term_count = sum(text.count(term) for term in terms)
        
        # Calculate density (terms per 100 words)
        density = (term_count / total_words) * 100
        
        # Optimal density is around 2-5%, too high is suspicious
        if density < 1:
            return density * 30  # Low density
        elif density <= 5:
            return 50 + (density * 10)  # Optimal range
        elif density <= 10:
            return 100 - ((density - 5) * 5)  # Starting to get suspicious
        else:
            return max(50, 100 - (density * 3))  # Too dense, likely keyword stuffing
    
    def _score_keyword_proximity(self, text: str, terms: List[str]) -> float:
        """Score based on how close query terms are to each other."""
        if len(terms) < 2:
            return 100.0  # Single term, proximity doesn't apply
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Find positions of all terms
        positions = {}
        for term in terms:
            positions[term] = []
            for i, word in enumerate(words):
                if term in word:
                    positions[term].append(i)
        
        # If not all terms found, low proximity score
        if not all(positions.get(t) for t in terms):
            return 30.0
        
        # Calculate minimum distance between terms
        min_span = float('inf')
        for i, term1 in enumerate(terms):
            for term2 in terms[i+1:]:
                for pos1 in positions[term1]:
                    for pos2 in positions[term2]:
                        span = abs(pos2 - pos1)
                        min_span = min(min_span, span)
        
        if min_span == float('inf'):
            return 30.0
        
        # Score: closer terms = higher score
        # Adjacent (span=1) = 100, span of 10+ = 50
        if min_span <= 1:
            return 100.0
        elif min_span <= 3:
            return 90.0
        elif min_span <= 5:
            return 80.0
        elif min_span <= 10:
            return 70.0
        else:
            return max(50.0, 100.0 - (min_span * 2))
    
    def _score_title_match(self, title: str, terms: List[str], query: str) -> float:
        """Score based on title matching query."""
        if not title:
            return 0.0
        
        title_lower = title.lower()
        query_lower = query.lower()
        
        # Exact match (very high score)
        if query_lower in title_lower:
            return 100.0
        
        # Check how many terms appear in title
        terms_in_title = sum(1 for term in terms if term in title_lower)
        
        if not terms:
            return 50.0
        
        term_ratio = terms_in_title / len(terms)
        
        # All terms in title
        if term_ratio == 1.0:
            return 95.0
        elif term_ratio >= 0.75:
            return 85.0
        elif term_ratio >= 0.5:
            return 70.0
        elif term_ratio >= 0.25:
            return 55.0
        else:
            return 30.0
    
    def _score_domain_relevance(self, url: str, terms: List[str]) -> float:
        """Score based on domain containing query terms."""
        if not url or not terms:
            return 50.0
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Check terms in domain
            terms_in_domain = sum(1 for term in terms if term in domain)
            terms_in_path = sum(1 for term in terms if term in path)
            
            domain_score = (terms_in_domain / len(terms)) * 50 if terms else 0
            path_score = (terms_in_path / len(terms)) * 30 if terms else 0
            
            return min(100.0, 50.0 + domain_score + path_score)
            
        except Exception:
            return 50.0
    
    def _score_freshness(self, result: Dict[str, Any]) -> float:
        """Score based on content freshness."""
        # Check for date in result metadata
        date_str = result.get('published_date') or result.get('date')
        
        if not date_str:
            # Check snippet for date patterns
            snippet = result.get('snippet', '')
            # Look for recent years
            current_year = datetime.now().year
            for year in range(current_year, current_year - 5, -1):
                if str(year) in snippet:
                    age = current_year - year
                    return max(50.0, 100.0 - (age * 10))
            
            return 50.0  # Unknown date
        
        try:
            # Parse date and calculate age
            if isinstance(date_str, str):
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%B %d, %Y', '%d %B %Y']:
                    try:
                        pub_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return 50.0
            else:
                return 50.0
            
            days_old = (datetime.now() - pub_date).days
            
            if days_old < 7:
                return 100.0
            elif days_old < 30:
                return 90.0
            elif days_old < 90:
                return 80.0
            elif days_old < 365:
                return 70.0
            elif days_old < 730:
                return 60.0
            else:
                return 50.0
                
        except Exception:
            return 50.0
    
    def _score_content_quality(self, title: str, snippet: str, url: str) -> float:
        """Score based on estimated content quality."""
        text = (title + ' ' + snippet).lower()
        
        score = 50.0  # Base score
        
        # Positive indicators
        for indicator in self.QUALITY_POSITIVE:
            if indicator in text:
                score += 5
        
        # Negative indicators
        for indicator in self.QUALITY_NEGATIVE:
            if indicator in text:
                score -= 10
        
        # URL quality indicators
        if url:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Positive URL patterns
            if '/docs/' in path or '/documentation/' in path:
                score += 10
            if '/api/' in path or '/reference/' in path:
                score += 5
            if '/research/' in path or '/paper/' in path:
                score += 10
            
            # Negative URL patterns
            if '/ad/' in path or '/ads/' in path:
                score -= 15
            if 'tracking' in path:
                score -= 10
        
        # Title quality
        if title:
            # Very short titles are suspicious
            if len(title) < 10:
                score -= 10
            # Very long titles might be clickbait
            elif len(title) > 200:
                score -= 5
            # ALL CAPS is often spam
            if title.isupper():
                score -= 15
        
        return max(0.0, min(100.0, score))
    
    def get_quality_tier(self, score: float) -> str:
        """Get quality tier label for a score."""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "high"
        elif score >= 70:
            return "good"
        elif score >= 60:
            return "fair"
        elif score >= 50:
            return "average"
        else:
            return "low"
    
    def filter_by_quality(self, results: List[Dict[str, Any]], 
                          min_score: float = 50.0) -> List[Dict[str, Any]]:
        """Filter results by minimum quality score."""
        return [r for r in results if r.get('relevance_score', 0) >= min_score]
    
    def group_by_quality(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group results by quality tier."""
        groups = {
            'excellent': [],  # 90-100
            'high': [],       # 80-89
            'good': [],       # 70-79
            'fair': [],       # 60-69
            'average': [],    # 50-59
            'low': [],        # 0-49
        }
        
        for result in results:
            score = result.get('relevance_score', 0)
            tier = self.get_quality_tier(score)
            groups[tier].append(result)
        
        return groups
