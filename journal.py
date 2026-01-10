"""
Journaling and Logging System for Web Search Pro
Tracks all search activities, results, and provides audit trail.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib

from config import JOURNAL_DIR, LOGS_DIR, RESULTS_DIR


class SearchJournal:
    """
    Maintains a journal of all search activities with timestamps,
    queries, results, and metadata.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.session_start = datetime.now()
        self.journal_file = JOURNAL_DIR / f"journal_{self.session_id}.json"
        self.log_file = LOGS_DIR / f"search_{self.session_id}.log"
        self.entries: List[Dict[str, Any]] = []
        self._init_journal()

    def _generate_session_id(self) -> str:
        """Generate unique session ID based on timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"{timestamp}_{hash_suffix}"

    def _init_journal(self):
        """Initialize journal file with session metadata."""
        metadata = {
            "session_id": self.session_id,
            "started_at": self.session_start.isoformat(),
            "entries": []
        }
        self._save_journal(metadata)
        self.log("INFO", f"Session started: {self.session_id}")

    def _save_journal(self, data: Dict[str, Any]):
        """Save journal data to file."""
        with open(self.journal_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_journal(self) -> Dict[str, Any]:
        """Load journal data from file."""
        if self.journal_file.exists():
            with open(self.journal_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"session_id": self.session_id, "entries": []}

    def log(self, level: str, message: str):
        """Write log entry to log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def add_entry(self, entry_type: str, data: Dict[str, Any]) -> str:
        """
        Add a new entry to the journal.

        Args:
            entry_type: Type of entry (search_start, search_result, error, etc.)
            data: Entry data

        Returns:
            Entry ID
        """
        entry_id = hashlib.md5(
            f"{datetime.now().timestamp()}{entry_type}".encode()
        ).hexdigest()[:12]

        entry = {
            "id": entry_id,
            "type": entry_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        journal = self._load_journal()
        journal["entries"].append(entry)
        self._save_journal(journal)

        self.log("INFO", f"Journal entry added: {entry_type} - {entry_id}")
        return entry_id

    def record_search_start(self, query: str, engines: List[str], search_type: str) -> str:
        """Record the start of a search operation."""
        return self.add_entry("search_start", {
            "query": query,
            "engines": engines,
            "search_type": search_type
        })

    def record_search_progress(self, search_id: str, engine: str, status: str,
                                results_count: int = 0, message: str = ""):
        """Record progress of ongoing search."""
        self.add_entry("search_progress", {
            "search_id": search_id,
            "engine": engine,
            "status": status,
            "results_count": results_count,
            "message": message
        })

    def record_search_result(self, search_id: str, engine: str,
                             results: List[Dict[str, Any]]):
        """Record search results."""
        return self.add_entry("search_result", {
            "search_id": search_id,
            "engine": engine,
            "results_count": len(results),
            "results": results
        })

    def record_error(self, context: str, error: str, details: Optional[Dict] = None):
        """Record an error."""
        self.log("ERROR", f"{context}: {error}")
        return self.add_entry("error", {
            "context": context,
            "error": error,
            "details": details or {}
        })

    def save_results_to_file(self, query: str, results: List[Dict[str, Any]],
                              format: str = "json") -> Path:
        """
        Save search results to a file.

        Args:
            query: Original search query
            results: List of search results
            format: Output format (json, txt, md)

        Returns:
            Path to saved file
        """
        safe_query = "".join(c if c.isalnum() or c in " -_" else "_" for c in query)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{safe_query}_{timestamp}.{format}"
        filepath = RESULTS_DIR / filename

        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "results_count": len(results),
                    "results": results
                }, f, indent=2, ensure_ascii=False)

        elif format == "txt":
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Search Results for: {query}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Total Results: {len(results)}\n")
                f.write("=" * 60 + "\n\n")
                for i, result in enumerate(results, 1):
                    f.write(f"[{i}] {result.get('title', 'No Title')}\n")
                    f.write(f"    URL: {result.get('url', 'N/A')}\n")
                    f.write(f"    Source: {result.get('engine', 'Unknown')}\n")
                    if result.get('snippet'):
                        f.write(f"    Snippet: {result.get('snippet')[:200]}...\n")
                    f.write("\n")

        elif format == "md":
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Search Results: {query}\n\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n")
                f.write(f"**Total Results:** {len(results)}\n\n")
                f.write("---\n\n")
                for i, result in enumerate(results, 1):
                    f.write(f"## {i}. {result.get('title', 'No Title')}\n\n")
                    f.write(f"- **URL:** [{result.get('url', 'N/A')}]({result.get('url', '')})\n")
                    f.write(f"- **Source:** {result.get('engine', 'Unknown')}\n")
                    if result.get('snippet'):
                        f.write(f"- **Snippet:** {result.get('snippet')}\n")
                    f.write("\n")

        self.log("INFO", f"Results saved to: {filepath}")
        return filepath

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        journal = self._load_journal()
        entries = journal.get("entries", [])

        searches = [e for e in entries if e["type"] == "search_start"]
        results = [e for e in entries if e["type"] == "search_result"]
        errors = [e for e in entries if e["type"] == "error"]

        total_results = sum(e["data"].get("results_count", 0) for e in results)

        return {
            "session_id": self.session_id,
            "duration": str(datetime.now() - self.session_start),
            "total_searches": len(searches),
            "total_results": total_results,
            "total_errors": len(errors),
            "journal_file": str(self.journal_file),
            "log_file": str(self.log_file)
        }

    def close_session(self):
        """Close the session and finalize journal."""
        summary = self.get_session_summary()
        self.add_entry("session_end", summary)
        self.log("INFO", f"Session ended: {self.session_id}")
        return summary
