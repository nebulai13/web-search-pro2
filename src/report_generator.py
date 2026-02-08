"""
Report Generator for WebSearchPro
Generates comprehensive Markdown and HTML reports from search results.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter

from config import RESULTS_DIR, REPORT_FORMATS


class ReportGenerator:
    """
    Generates comprehensive search reports in multiple formats.
    
    Supports:
    - Markdown reports with tables and statistics
    - HTML reports with styling and interactivity
    - JSON exports with full metadata
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or RESULTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, 
                        query: str,
                        results: List[Dict[str, Any]],
                        session_info: Dict[str, Any] = None,
                        formats: List[str] = None) -> Dict[str, Path]:
        """
        Generate reports in specified formats.
        
        Args:
            query: Original search query
            results: List of search results
            session_info: Session metadata (timing, engines, etc.)
            formats: List of formats to generate ('markdown', 'html', 'json')
            
        Returns:
            Dict mapping format name to file path
        """
        formats = formats or REPORT_FORMATS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = self._sanitize_filename(query)
        
        generated = {}
        
        if 'markdown' in formats or 'md' in formats:
            path = self._generate_markdown(query, results, session_info, timestamp, safe_query)
            generated['markdown'] = path
        
        if 'html' in formats:
            path = self._generate_html(query, results, session_info, timestamp, safe_query)
            generated['html'] = path
        
        if 'json' in formats:
            path = self._generate_json(query, results, session_info, timestamp, safe_query)
            generated['json'] = path
        
        return generated
    
    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """Create safe filename from text."""
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in text)
        return safe[:max_length].strip()
    
    def _generate_markdown(self, query: str, results: List[Dict], 
                           session_info: Dict, timestamp: str, 
                           safe_query: str) -> Path:
        """Generate Markdown report."""
        filepath = self.output_dir / f"report_{safe_query}_{timestamp}.md"
        
        stats = self._calculate_statistics(results, session_info)
        
        report = []
        
        # Header
        report.append(f"# WebSearchPro Search Report")
        report.append(f"## {query}")
        report.append("")
        report.append(f"**Search Date:** {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}")
        if session_info:
            report.append(f"**Session ID:** {session_info.get('session_id', 'N/A')}")
            report.append(f"**Duration:** {session_info.get('duration', 'N/A')}")
        report.append(f"**Total Results:** {len(results)} results")
        report.append(f"**Unique Results:** {stats.get('unique_count', len(results))}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        report.append(self._generate_executive_summary(query, results, stats))
        report.append("")
        
        # Key Findings
        report.append("### Key Findings")
        report.append("")
        for finding in self._generate_key_findings(results, stats):
            report.append(f"- {finding}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Search Methodology
        if session_info:
            report.append("## Search Methodology")
            report.append("")
            report.append("### Query Processing")
            report.append(f"- **Original Query:** `{query}`")
            if session_info.get('normalized_query'):
                report.append(f"- **Normalized Query:** `{session_info['normalized_query']}`")
            if session_info.get('query_variants'):
                report.append(f"- **Query Variants Generated:** {len(session_info['query_variants'])}")
            report.append("")
            
            # Sources table
            report.append("### Sources Queried")
            report.append("")
            report.append("| Engine | Results | Status |")
            report.append("|--------|---------|--------|")
            for engine, count in stats.get('results_by_engine', {}).items():
                status = "✓ Complete" if count > 0 else "○ No results"
                report.append(f"| {engine} | {count} | {status} |")
            report.append("")
            report.append("---")
            report.append("")
        
        # Statistics
        report.append("## Statistics")
        report.append("")
        report.append("### Result Distribution")
        report.append("")
        report.append("| Metric | Value |")
        report.append("|--------|-------|")
        report.append(f"| Total Results | {stats.get('total_count', 0)} |")
        report.append(f"| Unique URLs | {stats.get('unique_count', 0)} |")
        report.append(f"| Duplicates Removed | {stats.get('duplicates_removed', 0)} |")
        report.append(f"| Average Quality Score | {stats.get('avg_quality', 0):.1f}/100 |")
        report.append(f"| High Quality (90+) | {stats.get('high_quality_count', 0)} |")
        report.append(f"| Medium Quality (70-89) | {stats.get('medium_quality_count', 0)} |")
        report.append(f"| Low Quality (<70) | {stats.get('low_quality_count', 0)} |")
        report.append("")
        
        # Quality distribution
        if stats.get('quality_tiers'):
            report.append("### Quality Distribution")
            report.append("")
            for tier, count in stats['quality_tiers'].items():
                bar_length = int(count / max(stats['quality_tiers'].values()) * 20) if stats['quality_tiers'] else 0
                bar = "█" * bar_length
                report.append(f"- **{tier.title()}:** {count} {bar}")
            report.append("")
        report.append("---")
        report.append("")
        
        # Top Results
        report.append("## Top Results")
        report.append("")
        top_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)[:25]
        
        for i, result in enumerate(top_results, 1):
            title = result.get('title', 'No Title')
            url = result.get('url', '')
            engine = result.get('engine', 'Unknown')
            score = result.get('relevance_score', 0)
            snippet = result.get('snippet', '')[:200] + '...' if len(result.get('snippet', '')) > 200 else result.get('snippet', '')
            
            report.append(f"### {i}. {title}")
            report.append("")
            report.append(f"- **URL:** [{url}]({url})")
            report.append(f"- **Source:** {engine}")
            report.append(f"- **Quality Score:** {score}/100")
            if snippet:
                report.append(f"- **Snippet:** {snippet}")
            report.append("")
        
        if len(results) > 25:
            report.append(f"*... and {len(results) - 25} more results*")
            report.append("")
        
        report.append("---")
        report.append("")
        
        # Analysis by Source
        report.append("## Analysis by Source")
        report.append("")
        for engine, count in sorted(stats.get('results_by_engine', {}).items(), 
                                    key=lambda x: x[1], reverse=True):
            report.append(f"- **{engine}:** {count} results")
        report.append("")
        report.append("---")
        report.append("")
        
        # Footer
        report.append("## Report Metadata")
        report.append("")
        report.append(f"- **Generated:** {datetime.now().isoformat()}")
        report.append(f"- **Tool Version:** WebSearchPro v2.0")
        report.append(f"- **Report Format:** Markdown")
        report.append("")
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        return filepath
    
    def _generate_html(self, query: str, results: List[Dict],
                       session_info: Dict, timestamp: str,
                       safe_query: str) -> Path:
        """Generate HTML report with styling."""
        filepath = self.output_dir / f"report_{safe_query}_{timestamp}.html"
        
        stats = self._calculate_statistics(results, session_info)
        top_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)[:50]
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSearchPro Report: {query}</title>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --warning: #ca8a04;
            --danger: #dc2626;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
        }}
        header h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        header .query {{ font-size: 2rem; font-weight: 600; }}
        .meta {{ display: flex; gap: 2rem; margin-top: 1rem; opacity: 0.9; }}
        .card {{
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: var(--primary);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .stat {{
            text-align: center;
            padding: 1rem;
            background: var(--bg);
            border-radius: 8px;
        }}
        .stat-value {{ font-size: 2rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ color: var(--text-muted); font-size: 0.875rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: var(--bg); font-weight: 600; }}
        tr:hover {{ background: var(--bg); }}
        .result {{
            padding: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .result:last-child {{ border-bottom: none; }}
        .result-title {{
            font-weight: 600;
            color: var(--primary);
            text-decoration: none;
        }}
        .result-title:hover {{ text-decoration: underline; }}
        .result-url {{ color: var(--success); font-size: 0.875rem; word-break: break-all; }}
        .result-meta {{
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}
        .result-snippet {{ margin-top: 0.5rem; color: var(--text-muted); }}
        .score {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
        }}
        .score-high {{ background: #dcfce7; color: #166534; }}
        .score-medium {{ background: #fef9c3; color: #854d0e; }}
        .score-low {{ background: #fee2e2; color: #991b1b; }}
        .filter-bar {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .filter-bar input, .filter-bar select {{
            padding: 0.5rem;
            border: 1px solid var(--border);
            border-radius: 4px;
        }}
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>WebSearchPro Search Report</h1>
            <div class="query">{query}</div>
            <div class="meta">
                <span>📅 {datetime.now().strftime('%B %d, %Y')}</span>
                <span>📊 {len(results)} results</span>
                <span>⏱️ {session_info.get('duration', 'N/A') if session_info else 'N/A'}</span>
            </div>
        </header>

        <div class="card">
            <h2>📈 Statistics</h2>
            <div class="stats-grid">
                <div class="stat">
                    <div class="stat-value">{stats.get('total_count', 0)}</div>
                    <div class="stat-label">Total Results</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{stats.get('unique_count', 0)}</div>
                    <div class="stat-label">Unique URLs</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{stats.get('avg_quality', 0):.0f}</div>
                    <div class="stat-label">Avg Quality Score</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(stats.get('results_by_engine', {}))}</div>
                    <div class="stat-label">Sources Used</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🔍 Results by Source</h2>
            <table>
                <thead>
                    <tr><th>Source</th><th>Results</th><th>Avg Score</th></tr>
                </thead>
                <tbody>
                    {''.join(f"<tr><td>{engine}</td><td>{count}</td><td>{self._avg_score_for_engine(results, engine):.0f}</td></tr>" 
                             for engine, count in sorted(stats.get('results_by_engine', {}).items(), key=lambda x: x[1], reverse=True))}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>🏆 Top Results</h2>
            <div class="filter-bar">
                <input type="text" id="search" placeholder="Filter results..." onkeyup="filterResults()">
                <select id="scoreFilter" onchange="filterResults()">
                    <option value="all">All Scores</option>
                    <option value="high">High (90+)</option>
                    <option value="medium">Medium (70-89)</option>
                    <option value="low">Low (&lt;70)</option>
                </select>
            </div>
            <div id="results">
                {''.join(self._render_html_result(r, i) for i, r in enumerate(top_results, 1))}
            </div>
            {f'<p style="text-align:center;color:var(--text-muted);margin-top:1rem;">Showing top 50 of {len(results)} results</p>' if len(results) > 50 else ''}
        </div>

        <footer>
            Generated by WebSearchPro v2.0 | {datetime.now().isoformat()}
        </footer>
    </div>

    <script>
        function filterResults() {{
            const search = document.getElementById('search').value.toLowerCase();
            const scoreFilter = document.getElementById('scoreFilter').value;
            const results = document.querySelectorAll('.result');
            
            results.forEach(r => {{
                const text = r.textContent.toLowerCase();
                const score = parseFloat(r.dataset.score);
                let show = text.includes(search);
                
                if (scoreFilter === 'high') show = show && score >= 90;
                else if (scoreFilter === 'medium') show = show && score >= 70 && score < 90;
                else if (scoreFilter === 'low') show = show && score < 70;
                
                r.style.display = show ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>'''
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return filepath
    
    def _render_html_result(self, result: Dict, index: int) -> str:
        """Render a single result as HTML."""
        title = result.get('title', 'No Title')
        url = result.get('url', '')
        engine = result.get('engine', 'Unknown')
        score = result.get('relevance_score', 0)
        snippet = result.get('snippet', '')[:250]
        
        score_class = 'high' if score >= 90 else 'medium' if score >= 70 else 'low'
        
        return f'''
        <div class="result" data-score="{score}">
            <a href="{url}" target="_blank" class="result-title">{index}. {title}</a>
            <div class="result-url">{url}</div>
            <div class="result-meta">
                <span>📍 {engine}</span>
                <span class="score score-{score_class}">{score:.0f}/100</span>
            </div>
            {f'<div class="result-snippet">{snippet}...</div>' if snippet else ''}
        </div>
        '''
    
    def _generate_json(self, query: str, results: List[Dict],
                       session_info: Dict, timestamp: str,
                       safe_query: str) -> Path:
        """Generate JSON export with full data."""
        filepath = self.output_dir / f"report_{safe_query}_{timestamp}.json"
        
        stats = self._calculate_statistics(results, session_info)
        
        data = {
            'report': {
                'generated_at': datetime.now().isoformat(),
                'version': '2.0',
                'format': 'json',
            },
            'search': {
                'query': query,
                'session_info': session_info or {},
            },
            'statistics': stats,
            'results': results,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def _calculate_statistics(self, results: List[Dict], session_info: Dict = None) -> Dict[str, Any]:
        """Calculate statistics from results."""
        if not results:
            return {'total_count': 0, 'unique_count': 0}
        
        scores = [r.get('relevance_score', 0) for r in results]
        engines = [r.get('engine', 'unknown') for r in results]
        
        # Count by engine
        engine_counts = Counter(engines)
        
        # Quality tiers
        high = sum(1 for s in scores if s >= 90)
        medium = sum(1 for s in scores if 70 <= s < 90)
        low = sum(1 for s in scores if s < 70)
        
        return {
            'total_count': len(results),
            'unique_count': len(set(r.get('url', '') for r in results)),
            'duplicates_removed': session_info.get('duplicates_removed', 0) if session_info else 0,
            'avg_quality': sum(scores) / len(scores) if scores else 0,
            'max_quality': max(scores) if scores else 0,
            'min_quality': min(scores) if scores else 0,
            'high_quality_count': high,
            'medium_quality_count': medium,
            'low_quality_count': low,
            'results_by_engine': dict(engine_counts),
            'quality_tiers': {
                'excellent': sum(1 for s in scores if s >= 90),
                'high': sum(1 for s in scores if 80 <= s < 90),
                'good': sum(1 for s in scores if 70 <= s < 80),
                'fair': sum(1 for s in scores if 60 <= s < 70),
                'average': sum(1 for s in scores if 50 <= s < 60),
                'low': sum(1 for s in scores if s < 50),
            }
        }
    
    def _avg_score_for_engine(self, results: List[Dict], engine: str) -> float:
        """Calculate average score for an engine."""
        engine_results = [r for r in results if r.get('engine') == engine]
        if not engine_results:
            return 0
        scores = [r.get('relevance_score', 0) for r in engine_results]
        return sum(scores) / len(scores)
    
    def _generate_executive_summary(self, query: str, results: List[Dict], stats: Dict) -> str:
        """Generate executive summary text."""
        total = stats.get('total_count', 0)
        unique = stats.get('unique_count', total)
        avg_quality = stats.get('avg_quality', 0)
        engines = len(stats.get('results_by_engine', {}))
        high_quality = stats.get('high_quality_count', 0)
        
        summary = f"This report documents a comprehensive search for \"{query}\" "
        summary += f"across {engines} search engines. "
        summary += f"The search identified {unique} unique results "
        summary += f"with an average quality score of {avg_quality:.0f}/100. "
        
        if high_quality > 0:
            summary += f"{high_quality} results were classified as high-quality (90+ score). "
        
        top_engine = max(stats.get('results_by_engine', {}).items(), 
                        key=lambda x: x[1], default=('N/A', 0))
        summary += f"The most productive source was {top_engine[0]} with {top_engine[1]} results."
        
        return summary
    
    def _generate_key_findings(self, results: List[Dict], stats: Dict) -> List[str]:
        """Generate key findings list."""
        findings = []
        
        # Top result
        if results:
            top = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)[0]
            findings.append(f"Highest quality result: \"{top.get('title', 'N/A')[:50]}...\" (Score: {top.get('relevance_score', 0):.0f})")
        
        # Quality distribution
        high = stats.get('high_quality_count', 0)
        total = stats.get('total_count', 1)
        findings.append(f"{high} results ({high/total*100:.1f}%) rated as high quality")
        
        # Source diversity
        engines = len(stats.get('results_by_engine', {}))
        findings.append(f"Results aggregated from {engines} different sources")
        
        return findings
