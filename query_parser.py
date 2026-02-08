"""
Query Parser for Web Search Pro
Handles advanced search syntax like:
- Boolean operators: AND, OR, NOT, +, -
- Exact phrases: "quoted text"
- Site filters: site:example.com
- File types: filetype:pdf
- Date ranges: after:2023-01-01
- Wildcards: * (multiple chars), ? (single char)
- Proximity search: "term1 term2"~N
- Boost operator: term^N
- Query expansion (synonyms, related terms)
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class TokenType(Enum):
    TERM = "term"
    PHRASE = "phrase"
    AND = "and"
    OR = "or"
    NOT = "not"
    PLUS = "plus"
    MINUS = "minus"
    SITE = "site"
    FILETYPE = "filetype"
    INTITLE = "intitle"
    INURL = "inurl"
    AFTER = "after"
    BEFORE = "before"
    WILDCARD = "wildcard"
    PROXIMITY = "proximity"
    BOOST = "boost"


@dataclass
class QueryToken:
    """Represents a parsed query token."""
    type: TokenType
    value: str
    modifier: Optional[str] = None
    boost: float = 1.0
    proximity: int = 0


@dataclass
class ParsedQuery:
    """Represents a fully parsed search query."""
    original: str
    tokens: List[QueryToken] = field(default_factory=list)
    required_terms: List[str] = field(default_factory=list)
    optional_terms: List[str] = field(default_factory=list)  # OR terms
    excluded_terms: List[str] = field(default_factory=list)
    phrases: List[str] = field(default_factory=list)
    or_groups: List[List[str]] = field(default_factory=list)  # Groups of OR terms
    proximity_searches: List[Tuple[str, int]] = field(default_factory=list)  # (phrase, distance)
    boosted_terms: List[Tuple[str, float]] = field(default_factory=list)  # (term, boost)
    wildcard_terms: List[str] = field(default_factory=list)
    site_filter: Optional[str] = None
    filetype_filter: Optional[str] = None
    date_after: Optional[str] = None
    date_before: Optional[str] = None
    expanded_terms: List[str] = field(default_factory=list)  # Synonyms/related terms

    def to_search_string(self, engine: str = "default") -> str:
        """
        Convert parsed query to search string for specific engine.

        Args:
            engine: Target search engine (duckduckgo, bing, google, etc.)

        Returns:
            Formatted search string
        """
        parts = []

        # Add required terms
        for term in self.required_terms:
            if engine == "duckduckgo":
                parts.append(f"+{term}")
            else:
                parts.append(term)

        # Add phrases
        for phrase in self.phrases:
            parts.append(f'"{phrase}"')

        # Add OR groups (term1 OR term2 OR term3)
        for or_group in self.or_groups:
            if len(or_group) > 1:
                or_part = " OR ".join(or_group)
                parts.append(f"({or_part})")
            elif or_group:
                parts.append(or_group[0])

        # Add optional/OR terms
        if self.optional_terms:
            or_part = " OR ".join(self.optional_terms)
            if len(self.optional_terms) > 1:
                parts.append(f"({or_part})")
            else:
                parts.append(or_part)

        # Add excluded terms
        for term in self.excluded_terms:
            parts.append(f"-{term}")

        # Add filters
        if self.site_filter:
            parts.append(f"site:{self.site_filter}")

        if self.filetype_filter:
            parts.append(f"filetype:{self.filetype_filter}")

        if self.date_after:
            if engine in ["google", "duckduckgo"]:
                parts.append(f"after:{self.date_after}")

        if self.date_before:
            if engine in ["google", "duckduckgo"]:
                parts.append(f"before:{self.date_before}")

        return " ".join(parts)

    def get_display_info(self) -> Dict[str, Any]:
        """Get query information for display."""
        return {
            "original": self.original,
            "terms": self.required_terms,
            "or_groups": self.or_groups,
            "excluded": self.excluded_terms,
            "phrases": self.phrases,
            "proximity": self.proximity_searches,
            "boosted": self.boosted_terms,
            "wildcards": self.wildcard_terms,
            "expanded": self.expanded_terms,
            "filters": {
                "site": self.site_filter,
                "filetype": self.filetype_filter,
                "date_after": self.date_after,
                "date_before": self.date_before,
            }
        }


class QueryExpander:
    """
    Expands search queries with synonyms and related terms.
    """
    
    # Common synonyms for search expansion
    SYNONYMS = {
        # Technology
        'ai': ['artificial intelligence', 'machine learning', 'ml'],
        'ml': ['machine learning', 'ai', 'artificial intelligence'],
        'js': ['javascript'],
        'javascript': ['js'],
        'py': ['python'],
        'python': ['py'],
        'db': ['database'],
        'database': ['db'],
        'api': ['application programming interface', 'web service'],
        'ui': ['user interface', 'gui'],
        'ux': ['user experience'],
        'os': ['operating system'],
        'cpu': ['processor', 'central processing unit'],
        'gpu': ['graphics card', 'graphics processing unit'],
        'ram': ['memory', 'random access memory'],
        'ssd': ['solid state drive'],
        'hdd': ['hard drive', 'hard disk'],
        
        # Research
        'research': ['study', 'investigation', 'analysis'],
        'study': ['research', 'investigation', 'paper'],
        'paper': ['article', 'publication', 'study'],
        'tutorial': ['guide', 'howto', 'how-to'],
        'guide': ['tutorial', 'manual', 'handbook'],
        'documentation': ['docs', 'manual', 'reference'],
        'docs': ['documentation', 'manual'],
        
        # Actions
        'install': ['setup', 'configure'],
        'setup': ['install', 'configure', 'installation'],
        'fix': ['solve', 'resolve', 'repair'],
        'error': ['bug', 'issue', 'problem'],
        'bug': ['error', 'issue', 'defect'],
        
        # Business
        'company': ['corporation', 'firm', 'business'],
        'product': ['service', 'offering'],
        'price': ['cost', 'pricing'],
        'free': ['gratis', 'no cost', 'complimentary'],
    }
    
    # Related terms (broader associations)
    RELATED_TERMS = {
        'python': ['django', 'flask', 'pandas', 'numpy'],
        'javascript': ['nodejs', 'react', 'vue', 'angular'],
        'database': ['sql', 'mysql', 'postgresql', 'mongodb'],
        'machine learning': ['neural network', 'deep learning', 'tensorflow', 'pytorch'],
        'security': ['cybersecurity', 'encryption', 'authentication'],
        'cloud': ['aws', 'azure', 'gcp', 'kubernetes'],
    }
    
    def __init__(self, enable_synonyms: bool = True, enable_related: bool = False):
        self.enable_synonyms = enable_synonyms
        self.enable_related = enable_related
    
    def expand_term(self, term: str, max_expansions: int = 3) -> List[str]:
        """Expand a single term with synonyms."""
        expansions = []
        term_lower = term.lower()
        
        if self.enable_synonyms and term_lower in self.SYNONYMS:
            expansions.extend(self.SYNONYMS[term_lower][:max_expansions])
        
        if self.enable_related and term_lower in self.RELATED_TERMS:
            expansions.extend(self.RELATED_TERMS[term_lower][:max_expansions])
        
        return list(set(expansions))
    
    def expand_query(self, terms: List[str], max_total: int = 10) -> List[str]:
        """Expand multiple terms."""
        all_expansions = []
        
        for term in terms:
            expansions = self.expand_term(term)
            all_expansions.extend(expansions)
            
            if len(all_expansions) >= max_total:
                break
        
        return list(set(all_expansions))[:max_total]


class QueryParser:
    """
    Parses advanced search queries into structured format.
    Supports grep-like boolean syntax.

    Supported syntax:
        term1 term2         -> Both terms (implicit AND)
        term1 + term2       -> Both terms required (explicit AND)
        term1 AND term2     -> Both terms required
        term1 && term2      -> Both terms required (grep style)
        "exact phrase"      -> Exact phrase match
        term1 OR term2      -> Either term
        term1 || term2      -> Either term (grep style)
        term1 | term2       -> Either term
        -excluded           -> Exclude term
        NOT term            -> Exclude term
        !term               -> Exclude term (grep style)
        site:example.com    -> Limit to site
        filetype:pdf        -> Limit to file type
        intitle:keyword     -> Keyword in title
        inurl:keyword       -> Keyword in URL
        after:2023-01-01    -> After date
        before:2023-12-31   -> Before date
        
    Advanced syntax:
        term*               -> Wildcard (any characters)
        term?               -> Single character wildcard
        "phrase"~5          -> Proximity search (within 5 words)
        term^2              -> Boost term importance

    Examples:
        python && java              -> Both terms required
        python || java || rust      -> Any of these terms
        "machine learning" && -tutorial -> Exact phrase, exclude tutorial
        AI OR "artificial intelligence" -> Either term
        zeiss* microscope           -> Wildcard search
        "optical quality"~5         -> Proximity search
    """

    # Regex patterns
    PHRASE_PATTERN = r'"([^"]+)"'
    PHRASE_PROXIMITY_PATTERN = r'"([^"]+)"~(\d+)'
    SITE_PATTERN = r'site:(\S+)'
    FILETYPE_PATTERN = r'filetype:(\S+)'
    INTITLE_PATTERN = r'intitle:(\S+)'
    INURL_PATTERN = r'inurl:(\S+)'
    DATE_AFTER_PATTERN = r'after:(\d{4}-\d{2}-\d{2})'
    DATE_BEFORE_PATTERN = r'before:(\d{4}-\d{2}-\d{2})'
    BOOST_PATTERN = r'(\w+)\^(\d+(?:\.\d+)?)'
    WILDCARD_PATTERN = r'(\w+[*?]\w*|\w*[*?]\w+)'

    def __init__(self, enable_expansion: bool = False):
        self.operators = {
            'AND': TokenType.AND,
            '&&': TokenType.AND,
            '&': TokenType.AND,
            '+': TokenType.PLUS,
            'OR': TokenType.OR,
            '||': TokenType.OR,
            '|': TokenType.OR,
            'NOT': TokenType.NOT,
            '!': TokenType.NOT,
            '-': TokenType.MINUS,
        }
        self.enable_expansion = enable_expansion
        self.expander = QueryExpander() if enable_expansion else None

    def parse(self, query: str, expand: bool = None) -> ParsedQuery:
        """
        Parse a search query string into structured format.

        Args:
            query: Raw search query string
            expand: Override expansion setting for this parse

        Returns:
            ParsedQuery object with structured data
        """
        result = ParsedQuery(original=query)
        working_query = query.strip()

        # Extract proximity searches first "phrase"~N
        proximity_matches = re.findall(self.PHRASE_PROXIMITY_PATTERN, working_query)
        for phrase, distance in proximity_matches:
            result.proximity_searches.append((phrase, int(distance)))
        working_query = re.sub(self.PHRASE_PROXIMITY_PATTERN, '', working_query)

        # Extract regular phrases (quoted strings)
        phrases = re.findall(self.PHRASE_PATTERN, working_query)
        result.phrases = phrases
        working_query = re.sub(self.PHRASE_PATTERN, '', working_query)

        # Extract boost operators term^N
        boost_matches = re.findall(self.BOOST_PATTERN, working_query)
        for term, boost in boost_matches:
            result.boosted_terms.append((term, float(boost)))
        working_query = re.sub(self.BOOST_PATTERN, '', working_query)

        # Extract wildcards
        wildcards = re.findall(self.WILDCARD_PATTERN, working_query)
        result.wildcard_terms = wildcards
        # Don't remove wildcards, let them pass through as terms

        # Extract site filter
        site_match = re.search(self.SITE_PATTERN, working_query)
        if site_match:
            result.site_filter = site_match.group(1)
            working_query = re.sub(self.SITE_PATTERN, '', working_query)

        # Extract filetype filter
        filetype_match = re.search(self.FILETYPE_PATTERN, working_query)
        if filetype_match:
            result.filetype_filter = filetype_match.group(1)
            working_query = re.sub(self.FILETYPE_PATTERN, '', working_query)

        # Extract date filters
        after_match = re.search(self.DATE_AFTER_PATTERN, working_query)
        if after_match:
            result.date_after = after_match.group(1)
            working_query = re.sub(self.DATE_AFTER_PATTERN, '', working_query)

        before_match = re.search(self.DATE_BEFORE_PATTERN, working_query)
        if before_match:
            result.date_before = before_match.group(1)
            working_query = re.sub(self.DATE_BEFORE_PATTERN, '', working_query)

        # Extract intitle
        intitle_match = re.search(self.INTITLE_PATTERN, working_query)
        if intitle_match:
            result.required_terms.append(f"intitle:{intitle_match.group(1)}")
            working_query = re.sub(self.INTITLE_PATTERN, '', working_query)

        # Extract inurl
        inurl_match = re.search(self.INURL_PATTERN, working_query)
        if inurl_match:
            result.required_terms.append(f"inurl:{inurl_match.group(1)}")
            working_query = re.sub(self.INURL_PATTERN, '', working_query)

        # Process remaining terms
        self._process_terms(working_query, result)

        # Apply query expansion if enabled
        should_expand = expand if expand is not None else self.enable_expansion
        if should_expand and self.expander:
            expansions = self.expander.expand_query(result.required_terms)
            result.expanded_terms = expansions

        return result

    def _process_terms(self, query: str, result: ParsedQuery):
        """Process individual terms and operators."""
        # Normalize operators in query
        query = query.replace('&&', ' AND ')
        query = query.replace('||', ' OR ')
        query = query.replace('!', ' NOT ')

        # Tokenize
        tokens = self._tokenize(query)

        exclude_next = False
        or_mode = False
        current_or_group = []

        for i, token in enumerate(tokens):
            token_upper = token.upper()

            # Check for operators
            if token_upper in ('NOT',):
                exclude_next = True
                continue

            if token_upper in ('AND', '&', '+'):
                # AND is implicit - if we were in OR mode, close the group
                if current_or_group:
                    if len(current_or_group) > 1:
                        result.or_groups.append(current_or_group)
                    else:
                        result.required_terms.extend(current_or_group)
                    current_or_group = []
                or_mode = False
                continue

            if token_upper in ('OR', '|'):
                # OR handling - start/continue OR group
                or_mode = True
                continue

            # Regular term
            if token.startswith('-'):
                result.excluded_terms.append(token[1:])
            elif token.startswith('+'):
                result.required_terms.append(token[1:])
            elif exclude_next:
                result.excluded_terms.append(token)
                exclude_next = False
            elif or_mode or current_or_group:
                # Add to current OR group
                current_or_group.append(token)
            else:
                # Check if next token is OR
                if i + 1 < len(tokens) and tokens[i + 1].upper() in ('OR', '|'):
                    current_or_group.append(token)
                else:
                    result.required_terms.append(token)

        # Close any remaining OR group
        if current_or_group:
            if len(current_or_group) > 1:
                result.or_groups.append(current_or_group)
            else:
                result.required_terms.extend(current_or_group)

    def _tokenize(self, query: str) -> List[str]:
        """Split query into tokens."""
        # Replace multiple spaces with single space
        query = re.sub(r'\s+', ' ', query).strip()

        tokens = []
        current_token = ""

        i = 0
        while i < len(query):
            char = query[i]

            if char == ' ':
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
            elif char in ('+', '-') and (not current_token or current_token.isspace()):
                # Operator at start of token
                current_token = char
            else:
                current_token += char

            i += 1

        if current_token and current_token.strip():
            tokens.append(current_token.strip())

        return [t for t in tokens if t and t.strip()]

    def suggest_refinements(self, query: str, results_count: int) -> List[str]:
        """
        Suggest query refinements based on results.

        Args:
            query: Original query
            results_count: Number of results found

        Returns:
            List of suggested refined queries
        """
        suggestions = []
        parsed = self.parse(query)

        if results_count == 0:
            # Too restrictive - suggest removing filters
            if parsed.site_filter:
                suggestions.append(f"Remove site filter: {query.replace(f'site:{parsed.site_filter}', '').strip()}")
            if parsed.filetype_filter:
                suggestions.append(f"Remove filetype filter: {query.replace(f'filetype:{parsed.filetype_filter}', '').strip()}")
            if parsed.excluded_terms:
                for term in parsed.excluded_terms:
                    suggestions.append(f"Remove exclusion of '{term}'")
            if len(parsed.required_terms) > 1:
                suggestions.append(f"Try fewer terms: {parsed.required_terms[0]}")

        elif results_count > 100:
            # Too many results - suggest adding specificity
            if not parsed.site_filter:
                suggestions.append("Add site filter: site:example.com")
            if not parsed.filetype_filter:
                suggestions.append("Add filetype filter: filetype:pdf")
            suggestions.append("Add more specific terms")
            suggestions.append("Use exact phrases with quotes")

        return suggestions


def format_query_for_display(parsed: ParsedQuery) -> str:
    """Format parsed query for display."""
    lines = [f"Original: {parsed.original}"]

    if parsed.required_terms:
        lines.append(f"Required terms: {', '.join(parsed.required_terms)}")

    if parsed.phrases:
        quoted_phrases = ['"{}"'.format(p) for p in parsed.phrases]
        lines.append(f"Exact phrases: {', '.join(quoted_phrases)}")

    if parsed.excluded_terms:
        lines.append(f"Excluded: {', '.join(parsed.excluded_terms)}")

    filters = []
    if parsed.site_filter:
        filters.append(f"site:{parsed.site_filter}")
    if parsed.filetype_filter:
        filters.append(f"filetype:{parsed.filetype_filter}")
    if parsed.date_after:
        filters.append(f"after:{parsed.date_after}")
    if parsed.date_before:
        filters.append(f"before:{parsed.date_before}")

    if filters:
        lines.append(f"Filters: {', '.join(filters)}")

    return "\n".join(lines)
