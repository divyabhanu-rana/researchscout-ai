from __future__ import annotations
from typing import List
from tavily import TavilyClient
from models import SearchResult

class TavilySearchTool:
     def __init__(self, api_key: str | None):
          self.api_key = api_key
          self._client = TavilyClient(api_key = api_key) if api_key else None

     def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
          if not self._client or not query.strip():
               return []
          
          try:
               data = self._client.search(
                    query = query,
                    max_results = max_results,
                    include_answer = False,
                    include_images = False,
               )
               results = data.get("results", []) or []

               normalised: List[SearchResult] = []
               for r in results:
                    title = (r.get("title") or "").strip()
                    url = (r.get("url") or "").strip()
                    snippet = (r.get("content") or r.get("snippet") or "").strip()

                    if not title or not url or not snippet:
                         continue

                    normalised.append(SearchResult(title = title, url = url, snippet = snippet))

               return normalised
          except Exception:
               return[]