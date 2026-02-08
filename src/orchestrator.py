"""
Tiered Search Orchestrator for WebSearchPro
Executes searches in priority tiers with progress tracking.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import get_config


class TierStatus(Enum):
    """Status of a search tier."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class TierConfig:
    """Configuration for a search tier."""
    name: str
    tier_number: int
    engines: List[str]
    timeout: int
    enabled: bool = True
    requires_tor: bool = False
    requires_i2p: bool = False


@dataclass
class TierResult:
    """Result from a completed tier."""
    tier_number: int
    tier_name: str
    status: TierStatus
    results: List[Dict[str, Any]]
    results_count: int
    engines_succeeded: List[str]
    engines_failed: List[str]
    elapsed_seconds: float
    errors: List[str]


class SearchOrchestrator:
    """
    Orchestrates multi-tier search execution.
    
    Tiers:
    1. Official/Authoritative sources
    2. Major search engines (DuckDuckGo, Bing, Brave)
    3. Extended engines (Yahoo, Yandex, Qwant, etc.)
    4. Specialized/Archives (Wikipedia, Reddit, GitHub, Archive.org)
    5. Tor Hidden Services (Ahmia, Torch, Haystack)
    6. I2P Network
    """
    
    DEFAULT_TIERS = [
        TierConfig(
            name="Major Search Engines",
            tier_number=2,
            engines=["duckduckgo", "bing", "brave"],
            timeout=60,
            enabled=True,
        ),
        TierConfig(
            name="Extended Engines",
            tier_number=3,
            engines=["yahoo", "yandex", "qwant", "mojeek", "ecosia"],
            timeout=90,
            enabled=True,
        ),
        TierConfig(
            name="Specialized & Archives",
            tier_number=4,
            engines=["wikipedia", "reddit", "github", "stackoverflow", 
                     "hackernews", "scholar", "semantic_scholar", "pubmed", "archive_org"],
            timeout=120,
            enabled=True,
        ),
        TierConfig(
            name="Tor Hidden Services",
            tier_number=5,
            engines=["ahmia", "torch", "haystack"],
            timeout=300,
            enabled=False,  # Enabled via --darknet flag
            requires_tor=True,
        ),
        TierConfig(
            name="I2P Network",
            tier_number=6,
            engines=["i2p_search"],
            timeout=300,
            enabled=False,
            requires_i2p=True,
        ),
    ]
    
    def __init__(self, 
                 search_engine_manager,
                 include_darknet: bool = False,
                 include_i2p: bool = False,
                 tiers: List[TierConfig] = None):
        """
        Initialize orchestrator.
        
        Args:
            search_engine_manager: SearchEngineManager instance
            include_darknet: Enable Tor-based search tiers
            include_i2p: Enable I2P-based search tiers
            tiers: Custom tier configuration
        """
        self.engine_manager = search_engine_manager
        self.include_darknet = include_darknet
        self.include_i2p = include_i2p
        
        # Configure tiers
        self.tiers = tiers or self._load_tier_config()
        
        # Enable/disable tiers based on flags
        for tier in self.tiers:
            if tier.requires_tor:
                tier.enabled = include_darknet
            if tier.requires_i2p:
                tier.enabled = include_i2p
        
        # Progress tracking
        self.current_tier: Optional[int] = None
        self.tier_results: Dict[int, TierResult] = {}
        self.all_results: List[Dict[str, Any]] = []
        
        # Callbacks
        self._progress_callback: Optional[Callable] = None
        self._tier_callback: Optional[Callable] = None
    
    def _load_tier_config(self) -> List[TierConfig]:
        """Load tier configuration from config file or use defaults."""
        tiers = []
        
        # Try to load from YAML config
        tier_configs = {
            2: ('tier2_major', 'Major Search Engines', ['duckduckgo', 'bing', 'brave']),
            3: ('tier3_extended', 'Extended Engines', ['yahoo', 'yandex', 'qwant', 'mojeek', 'ecosia']),
            4: ('tier4_specialized', 'Specialized & Archives', 
                ['wikipedia', 'reddit', 'github', 'stackoverflow', 'hackernews', 
                 'scholar', 'semantic_scholar', 'pubmed', 'archive_org']),
            5: ('tier5_tor', 'Tor Hidden Services', ['ahmia', 'torch', 'haystack']),
            6: ('tier6_i2p', 'I2P Network', ['i2p_search']),
        }
        
        for tier_num, (config_key, name, default_engines) in tier_configs.items():
            enabled = get_config(f'tiers.{config_key}.enabled', tier_num <= 4)
            timeout = get_config(f'tiers.{config_key}.timeout', 60 * tier_num)
            engines = get_config(f'tiers.{config_key}.engines', default_engines)
            
            tiers.append(TierConfig(
                name=name,
                tier_number=tier_num,
                engines=engines,
                timeout=timeout,
                enabled=enabled,
                requires_tor=(tier_num == 5),
                requires_i2p=(tier_num == 6),
            ))
        
        return sorted(tiers, key=lambda t: t.tier_number)
    
    def set_progress_callback(self, callback: Callable[[str, str, str], None]):
        """
        Set callback for progress updates.
        
        Callback signature: (engine: str, status: str, message: str)
        """
        self._progress_callback = callback
    
    def set_tier_callback(self, callback: Callable[[int, str, TierStatus], None]):
        """
        Set callback for tier status changes.
        
        Callback signature: (tier_number: int, tier_name: str, status: TierStatus)
        """
        self._tier_callback = callback
    
    def _notify_progress(self, engine: str, status: str, message: str):
        """Send progress notification."""
        if self._progress_callback:
            self._progress_callback(engine, status, message)
    
    def _notify_tier_status(self, tier: TierConfig, status: TierStatus):
        """Send tier status notification."""
        if self._tier_callback:
            self._tier_callback(tier.tier_number, tier.name, status)
    
    def execute_search(self, 
                       query: str,
                       max_results_per_engine: int = 30,
                       stop_on_results: int = 0,
                       parallel_engines: int = 3) -> Tuple[List[Dict], Dict[int, TierResult]]:
        """
        Execute tiered search.
        
        Args:
            query: Search query
            max_results_per_engine: Max results per engine
            stop_on_results: Stop after reaching this many results (0 = no limit)
            parallel_engines: Number of engines to search in parallel
            
        Returns:
            Tuple of (all_results, tier_results)
        """
        self.all_results = []
        self.tier_results = {}
        start_time = time.time()
        
        for tier in self.tiers:
            if not tier.enabled:
                self.tier_results[tier.tier_number] = TierResult(
                    tier_number=tier.tier_number,
                    tier_name=tier.name,
                    status=TierStatus.SKIPPED,
                    results=[],
                    results_count=0,
                    engines_succeeded=[],
                    engines_failed=[],
                    elapsed_seconds=0,
                    errors=[],
                )
                continue
            
            # Check early stop
            if stop_on_results > 0 and len(self.all_results) >= stop_on_results:
                self._notify_tier_status(tier, TierStatus.SKIPPED)
                self.tier_results[tier.tier_number] = TierResult(
                    tier_number=tier.tier_number,
                    tier_name=tier.name,
                    status=TierStatus.SKIPPED,
                    results=[],
                    results_count=0,
                    engines_succeeded=[],
                    engines_failed=[],
                    elapsed_seconds=0,
                    errors=["Skipped: sufficient results collected"],
                )
                continue
            
            # Execute tier
            self.current_tier = tier.tier_number
            tier_result = self._execute_tier(tier, query, max_results_per_engine, parallel_engines)
            self.tier_results[tier.tier_number] = tier_result
            self.all_results.extend(tier_result.results)
        
        total_elapsed = time.time() - start_time
        
        return self.all_results, self.tier_results
    
    def _execute_tier(self, 
                      tier: TierConfig,
                      query: str,
                      max_results: int,
                      parallel: int) -> TierResult:
        """Execute a single tier's search."""
        self._notify_tier_status(tier, TierStatus.RUNNING)
        tier_start = time.time()
        
        results = []
        succeeded = []
        failed = []
        errors = []
        
        # Filter to available engines
        available_engines = self._get_available_engines(tier)
        
        if not available_engines:
            return TierResult(
                tier_number=tier.tier_number,
                tier_name=tier.name,
                status=TierStatus.SKIPPED,
                results=[],
                results_count=0,
                engines_succeeded=[],
                engines_failed=tier.engines,
                elapsed_seconds=0,
                errors=["No available engines for this tier"],
            )
        
        # Execute engines in parallel
        with ThreadPoolExecutor(max_workers=min(parallel, len(available_engines))) as executor:
            futures = {}
            
            for engine in available_engines:
                self._notify_progress(engine, "starting", f"Starting {engine} search...")
                future = executor.submit(
                    self._search_single_engine,
                    engine, query, max_results, tier
                )
                futures[future] = engine
            
            for future in as_completed(futures, timeout=tier.timeout):
                engine = futures[future]
                try:
                    engine_results, error = future.result()
                    
                    if error:
                        failed.append(engine)
                        errors.append(f"{engine}: {error}")
                        self._notify_progress(engine, "error", f"Failed: {error}")
                    else:
                        results.extend(engine_results)
                        succeeded.append(engine)
                        self._notify_progress(engine, "complete", 
                                            f"Found {len(engine_results)} results")
                except Exception as e:
                    failed.append(engine)
                    errors.append(f"{engine}: {str(e)}")
                    self._notify_progress(engine, "error", f"Error: {str(e)}")
        
        elapsed = time.time() - tier_start
        status = TierStatus.COMPLETE if succeeded else TierStatus.FAILED
        
        self._notify_tier_status(tier, status)
        
        return TierResult(
            tier_number=tier.tier_number,
            tier_name=tier.name,
            status=status,
            results=results,
            results_count=len(results),
            engines_succeeded=succeeded,
            engines_failed=failed,
            elapsed_seconds=elapsed,
            errors=errors,
        )
    
    def _search_single_engine(self, 
                              engine: str, 
                              query: str, 
                              max_results: int,
                              tier: TierConfig) -> Tuple[List[Dict], Optional[str]]:
        """
        Search a single engine.
        
        Returns:
            Tuple of (results, error_message)
        """
        try:
            results = self.engine_manager.search_single(
                engine=engine,
                query=query,
                max_results=max_results,
                progress_callback=lambda s, m: self._notify_progress(engine, s, m)
            )
            
            # Add tier info to results
            for r in results:
                r['source_tier'] = tier.tier_number
                r['source_tier_name'] = tier.name
            
            return results, None
            
        except Exception as e:
            return [], str(e)
    
    def _get_available_engines(self, tier: TierConfig) -> List[str]:
        """Get list of available engines for a tier."""
        available = []
        
        for engine in tier.engines:
            # Check if engine exists in manager
            if tier.requires_tor:
                if engine in getattr(self.engine_manager, 'darknet_engines', {}):
                    available.append(engine)
            elif tier.requires_i2p:
                # I2P engines - check if I2P client is available
                if hasattr(self.engine_manager, 'i2p_engines'):
                    available.append(engine)
            else:
                # Check clearnet engines
                if (engine in getattr(self.engine_manager, 'clearnet_engines', {}) or
                    engine in getattr(self.engine_manager, 'extended_engines', {}) or
                    engine in getattr(self.engine_manager, 'deep_engines', {})):
                    available.append(engine)
        
        return available
    
    def get_tier_summary(self) -> Dict[str, Any]:
        """Get summary of tier execution."""
        total_results = sum(tr.results_count for tr in self.tier_results.values())
        total_time = sum(tr.elapsed_seconds for tr in self.tier_results.values())
        
        tiers_completed = sum(1 for tr in self.tier_results.values() 
                             if tr.status == TierStatus.COMPLETE)
        tiers_failed = sum(1 for tr in self.tier_results.values() 
                          if tr.status == TierStatus.FAILED)
        
        return {
            'total_results': total_results,
            'total_time_seconds': total_time,
            'tiers_completed': tiers_completed,
            'tiers_failed': tiers_failed,
            'tiers_skipped': len(self.tiers) - tiers_completed - tiers_failed,
            'tier_details': {
                tr.tier_number: {
                    'name': tr.tier_name,
                    'status': tr.status.value,
                    'results': tr.results_count,
                    'time': tr.elapsed_seconds,
                    'engines_ok': tr.engines_succeeded,
                    'engines_failed': tr.engines_failed,
                }
                for tr in self.tier_results.values()
            }
        }
    
    def get_enabled_tiers(self) -> List[TierConfig]:
        """Get list of enabled tiers."""
        return [t for t in self.tiers if t.enabled]
    
    def get_all_engines(self) -> List[str]:
        """Get all engines from enabled tiers."""
        engines = []
        for tier in self.get_enabled_tiers():
            engines.extend(tier.engines)
        return engines
