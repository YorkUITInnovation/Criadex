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

try:
    from ragflow import RagflowEmbedding, RagflowRetriever, RagflowReranker, RagflowLLM
except ImportError:
    # If not installed, these will be resolved after pip install -r requirements.txt in .venv
    RagflowEmbedding = object
    RagflowRetriever = object
    RagflowReranker = object
    RagflowLLM = object


import os
from typing import List
import asyncio

class CriaEmbedding(RagflowEmbedding):
    """
    Ragflow-based embedding model for Cria
    """
    def embed(self, text: str) -> List[float]:
        if os.environ.get('APP_API_MODE', 'PRODUCTION') == 'TESTING':
            return [0.0] * 1536
        return super().embed(text)

    async def aembed(self, text: str) -> List[float]:
        if os.environ.get('APP_API_MODE', 'PRODUCTION') == 'TESTING':
            return [0.0] * 1536
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, text)

class CriaRetriever(RagflowRetriever):
    """
    Ragflow-based retriever for multi-collection search
    """
    def retrieve(self, query: str):
        return super().retrieve(query)

    async def aretrieve(self, query: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.retrieve, query)

class CriaReranker(RagflowReranker):
    """
    Ragflow-based reranker for search results
    """
    def rerank(self, results, query):
        return super().rerank(results, query)

    async def arerank(self, results, query):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.rerank, results, query)

class CriaLLM(RagflowLLM):
    """
    Ragflow-based LLM for response generation
    """
    def generate(self, prompt: str):
        return super().generate(prompt)

    async def agenerate(self, prompt: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate, prompt)
