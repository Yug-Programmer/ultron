"""
Real-Time Web Search Tool
Powered by DuckDuckGo Search (100% free, zero API key required).
Provides fresh real-time grounding to answer queries beyond LLM cutoff dates.
"""

import logging
from ddgs import DDGS

logger = logging.getLogger("Ultron.WebSearch")

class WebSearchTool:
    @staticmethod
    def search(query: str, max_results: int = 4) -> str:
        """
        Executes a real-time DuckDuckGo web search and returns formatted snippets.
        """
        if not query or not query.strip():
            return "No search query provided."

        try:
            logger.info(f"[WebSearch] Searching DuckDuckGo for: '{query}'")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No relevant web results found for '{query}'."

            formatted = []
            for i, res in enumerate(results, 1):
                title = res.get("title", "")
                snippet = res.get("body", "")
                formatted.append(f"[{i}] {title}\nSummary: {snippet}")

            return "\n\n".join(formatted)
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return f"Failed to retrieve web search results: {str(e)}"
