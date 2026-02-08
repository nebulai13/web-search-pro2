"""
State Manager for WebSearchPro
Handles search state checkpointing, pause/resume functionality.
"""
import json
import pickle
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from config import SESSIONS_DIR, AUTO_CHECKPOINT, CHECKPOINT_INTERVAL


class SearchStatus(Enum):
    """Status of a search operation."""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SearchState:
    """Represents the complete state of a search operation."""
    session_id: str
    query: str
    normalized_query: str
    query_variants: List[str] = field(default_factory=list)
    
    # Progress tracking
    status: SearchStatus = SearchStatus.INITIALIZED
    current_tier: int = 1
    current_engine: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    
    # Results
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    results_by_engine: Dict[str, List[Dict]] = field(default_factory=dict)
    deduplicated_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Search configuration
    include_darknet: bool = False
    include_i2p: bool = False
    engines_to_search: List[str] = field(default_factory=list)
    completed_engines: List[str] = field(default_factory=list)
    failed_engines: List[str] = field(default_factory=list)
    pending_engines: List[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    resumed_at: Optional[str] = None
    completed_at: Optional[str] = None
    elapsed_seconds: float = 0.0
    
    # Metadata
    checkpoints: List[str] = field(default_factory=list)
    error_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchState':
        """Create state from dictionary."""
        data['status'] = SearchStatus(data.get('status', 'initialized'))
        return cls(**data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current state."""
        return {
            'session_id': self.session_id,
            'query': self.query,
            'status': self.status.value,
            'progress': f"{self.progress * 100:.1f}%",
            'current_tier': self.current_tier,
            'results_count': len(self.all_results),
            'unique_results': len(self.deduplicated_results),
            'engines_completed': len(self.completed_engines),
            'engines_remaining': len(self.pending_engines),
            'elapsed_time': f"{self.elapsed_seconds:.1f}s",
        }


class StateManager:
    """
    Manages search state for pause/resume functionality.
    Supports checkpointing, recovery, and state persistence.
    """
    
    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_state: Optional[SearchState] = None
        self._checkpoint_counter = 0
    
    def create_session(self, session_id: str, query: str, 
                       normalized_query: str = "",
                       engines: List[str] = None,
                       include_darknet: bool = False,
                       include_i2p: bool = False) -> SearchState:
        """
        Create a new search session.
        
        Args:
            session_id: Unique session identifier
            query: Original search query
            normalized_query: Normalized/parsed query
            engines: List of engines to search
            include_darknet: Whether to include Tor searches
            include_i2p: Whether to include I2P searches
            
        Returns:
            New SearchState object
        """
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "checkpoints").mkdir(exist_ok=True)
        (session_dir / "results").mkdir(exist_ok=True)
        
        state = SearchState(
            session_id=session_id,
            query=query,
            normalized_query=normalized_query or query,
            engines_to_search=engines or [],
            pending_engines=engines.copy() if engines else [],
            include_darknet=include_darknet,
            include_i2p=include_i2p,
            started_at=datetime.now().isoformat(),
        )
        
        self._current_state = state
        self._save_metadata(state)
        
        return state
    
    def get_session_dir(self, session_id: str) -> Path:
        """Get the directory for a session."""
        return self.sessions_dir / session_id
    
    def _save_metadata(self, state: SearchState):
        """Save session metadata as JSON."""
        session_dir = self.get_session_dir(state.session_id)
        metadata_file = session_dir / "state.json"
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False, default=str)
    
    def create_checkpoint(self, state: Optional[SearchState] = None, 
                          label: str = "") -> str:
        """
        Create a checkpoint of current search state.
        
        Args:
            state: SearchState to checkpoint (uses current if None)
            label: Optional label for the checkpoint
            
        Returns:
            Checkpoint ID
        """
        state = state or self._current_state
        if not state:
            raise ValueError("No state to checkpoint")
        
        self._checkpoint_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"checkpoint_{timestamp}_{self._checkpoint_counter}"
        if label:
            checkpoint_id = f"checkpoint_{label}_{timestamp}"
        
        session_dir = self.get_session_dir(state.session_id)
        checkpoint_dir = session_dir / "checkpoints"
        
        # Save full state as compressed pickle
        checkpoint_file = checkpoint_dir / f"{checkpoint_id}.pkl.gz"
        with gzip.open(checkpoint_file, 'wb') as f:
            pickle.dump(state, f)
        
        # Update state with checkpoint info
        state.checkpoints.append(checkpoint_id)
        
        # Save updated metadata
        self._save_metadata(state)
        
        return checkpoint_id
    
    def load_checkpoint(self, session_id: str, checkpoint_id: str) -> SearchState:
        """
        Load state from a checkpoint.
        
        Args:
            session_id: Session identifier
            checkpoint_id: Checkpoint to load
            
        Returns:
            Restored SearchState
        """
        session_dir = self.get_session_dir(session_id)
        checkpoint_file = session_dir / "checkpoints" / f"{checkpoint_id}.pkl.gz"
        
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")
        
        with gzip.open(checkpoint_file, 'rb') as f:
            state = pickle.load(f)
        
        self._current_state = state
        return state
    
    def load_session(self, session_id: str) -> SearchState:
        """
        Load the latest state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SearchState for the session
        """
        session_dir = self.get_session_dir(session_id)
        metadata_file = session_dir / "state.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = SearchState.from_dict(data)
        self._current_state = state
        return state
    
    def list_sessions(self, include_completed: bool = True) -> List[Dict[str, Any]]:
        """
        List all available sessions.
        
        Args:
            include_completed: Whether to include completed sessions
            
        Returns:
            List of session summaries
        """
        sessions = []
        
        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            metadata_file = session_dir / "state.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                status = data.get('status', 'unknown')
                if not include_completed and status == 'completed':
                    continue
                
                sessions.append({
                    'session_id': data.get('session_id'),
                    'query': data.get('query'),
                    'status': status,
                    'started_at': data.get('started_at'),
                    'results_count': len(data.get('all_results', [])),
                    'progress': data.get('progress', 0),
                })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x.get('started_at', ''), reverse=True)
    
    def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of checkpoint info
        """
        session_dir = self.get_session_dir(session_id)
        checkpoint_dir = session_dir / "checkpoints"
        
        if not checkpoint_dir.exists():
            return []
        
        checkpoints = []
        for checkpoint_file in checkpoint_dir.glob("*.pkl.gz"):
            checkpoint_id = checkpoint_file.stem.replace('.pkl', '')
            stat = checkpoint_file.stat()
            checkpoints.append({
                'checkpoint_id': checkpoint_id,
                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'size_bytes': stat.st_size,
            })
        
        return sorted(checkpoints, key=lambda x: x['created_at'], reverse=True)
    
    def pause_search(self, state: Optional[SearchState] = None) -> str:
        """
        Pause current search and create checkpoint.
        
        Args:
            state: State to pause (uses current if None)
            
        Returns:
            Checkpoint ID
        """
        state = state or self._current_state
        if not state:
            raise ValueError("No active search to pause")
        
        state.status = SearchStatus.PAUSED
        state.paused_at = datetime.now().isoformat()
        
        # Create checkpoint with pause label
        checkpoint_id = self.create_checkpoint(state, label=f"paused_tier{state.current_tier}")
        
        return checkpoint_id
    
    def resume_search(self, session_id: str, 
                      checkpoint_id: Optional[str] = None) -> SearchState:
        """
        Resume a paused search.
        
        Args:
            session_id: Session to resume
            checkpoint_id: Specific checkpoint to resume from (latest if None)
            
        Returns:
            Restored SearchState ready to continue
        """
        if checkpoint_id:
            state = self.load_checkpoint(session_id, checkpoint_id)
        else:
            # Load latest state
            state = self.load_session(session_id)
            
            # If there are checkpoints, load the latest one for full results
            checkpoints = self.list_checkpoints(session_id)
            if checkpoints:
                latest_checkpoint = checkpoints[0]['checkpoint_id']
                state = self.load_checkpoint(session_id, latest_checkpoint)
        
        state.status = SearchStatus.RUNNING
        state.resumed_at = datetime.now().isoformat()
        
        self._current_state = state
        self._save_metadata(state)
        
        return state
    
    def update_progress(self, 
                        engine: str = None,
                        tier: int = None,
                        progress: float = None,
                        results: List[Dict] = None,
                        error: str = None):
        """
        Update search progress.
        
        Args:
            engine: Current engine being searched
            tier: Current tier number
            progress: Overall progress (0.0 to 1.0)
            results: New results to add
            error: Error message if engine failed
        """
        if not self._current_state:
            return
        
        state = self._current_state
        
        if engine:
            state.current_engine = engine
        
        if tier is not None:
            state.current_tier = tier
        
        if progress is not None:
            state.progress = progress
        
        if results:
            state.all_results.extend(results)
            if engine:
                if engine not in state.results_by_engine:
                    state.results_by_engine[engine] = []
                state.results_by_engine[engine].extend(results)
        
        if error:
            state.error_log.append({
                'engine': engine,
                'error': error,
                'timestamp': datetime.now().isoformat()
            })
            if engine and engine in state.pending_engines:
                state.pending_engines.remove(engine)
                state.failed_engines.append(engine)
        elif engine and results is not None:
            # Engine completed successfully
            if engine in state.pending_engines:
                state.pending_engines.remove(engine)
                state.completed_engines.append(engine)
        
        # Auto-checkpoint if enabled
        if AUTO_CHECKPOINT and len(state.completed_engines) % 3 == 0:
            self.create_checkpoint(state, label=f"auto_tier{state.current_tier}")
    
    def complete_search(self, deduplicated_results: List[Dict] = None):
        """Mark search as completed."""
        if not self._current_state:
            return
        
        state = self._current_state
        state.status = SearchStatus.COMPLETED
        state.completed_at = datetime.now().isoformat()
        state.progress = 1.0
        
        if deduplicated_results:
            state.deduplicated_results = deduplicated_results
        
        # Create final checkpoint
        self.create_checkpoint(state, label="final")
        self._save_metadata(state)
    
    def fail_search(self, error: str):
        """Mark search as failed."""
        if not self._current_state:
            return
        
        state = self._current_state
        state.status = SearchStatus.FAILED
        state.error_log.append({
            'engine': 'system',
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        self.create_checkpoint(state, label="failed")
        self._save_metadata(state)
    
    def cancel_search(self) -> Optional[str]:
        """Cancel current search and save state."""
        if not self._current_state:
            return None
        
        state = self._current_state
        state.status = SearchStatus.CANCELLED
        
        checkpoint_id = self.create_checkpoint(state, label="cancelled")
        self._save_metadata(state)
        
        return checkpoint_id
    
    def delete_session(self, session_id: str):
        """Delete a session and all its data."""
        import shutil
        session_dir = self.get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
    
    @property
    def current_state(self) -> Optional[SearchState]:
        """Get current state."""
        return self._current_state
    
    def get_resumable_sessions(self) -> List[Dict[str, Any]]:
        """Get sessions that can be resumed (paused or running)."""
        sessions = self.list_sessions(include_completed=False)
        return [s for s in sessions if s['status'] in ('paused', 'running', 'initialized')]
