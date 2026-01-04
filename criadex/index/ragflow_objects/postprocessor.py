class RagflowNodePostprocessor:
    def __init__(self, **kwargs):
        pass
"""
This file is part of Criadex.

Criadex is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
Criadex is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Criadex. If not, see <https://www.gnu.org/licenses/>.

@package    Criadex
@author     kiarash b
@copyright  2025 onwards York University (https://yorku.ca/)
@repository https://github.com/YorkUITInnovation/Criadex
@license    https://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
"""


import asyncio

class RagflowPostprocessor:
    def __init__(self, reranker):
        self.reranker = reranker

    def rerank(self, results, query):
        # Use external reranker if available, else sort by score
        if hasattr(self.reranker, "rerank"):
            return self.reranker.rerank(results, query)
        return sorted(results, key=lambda x: x.get("_score", 0), reverse=True)

    async def arerank(self, results, query):
        # Async rerank support
        if hasattr(self.reranker, "arerank"):
            return await self.reranker.arerank(results, query)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.rerank, results, query)
