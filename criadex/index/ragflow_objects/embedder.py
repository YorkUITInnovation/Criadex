import asyncio
import math
import os
import re
from typing import List, Optional, Protocol, runtime_checkable


@runtime_checkable
class _Embedder(Protocol):
    def embed(self, text: str) -> List[float]: ...
    async def aembed(self, text: str) -> List[float]: ...


class _LocalHashingEmbedder:
    """
    Deterministic local embedder for dev/testing.

    This is the fallback when a real embedding backend isn't configured.
    """

    DIMS: int = 768
    _TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

    def embed(self, text: str) -> List[float]:
        tokens = self._TOKEN_RE.findall(text or "")
        vec = [0.0] * self.DIMS

        for tok in tokens:
            idx = hash(tok.lower()) % self.DIMS
            vec[idx] += 1.0

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            inv = 1.0 / norm
            vec = [v * inv for v in vec]
        return vec

    async def aembed(self, text: str) -> List[float]:
        await asyncio.sleep(0)
        return self.embed(text)


class RagflowEmbedder:
    """
    Production-first embedder.

    - If Ragflow's embedding backend is available and configured, use it.
    - Otherwise fall back to a deterministic local embedder (so dev stacks still work).
    """

    def __init__(self) -> None:
        mode = (os.getenv("CRIADEX_EMBEDDER_MODE") or "auto").strip().lower()
        self._impl: _Embedder = self._build_impl(mode=mode) or _LocalHashingEmbedder()

    def _build_impl(self, *, mode: str) -> Optional[_Embedder]:
        if mode in ("local", "hash", "fallback"):
            return _LocalHashingEmbedder()

        # "ragflow" forces Ragflow backend; "auto" tries ragflow then falls back.
        if mode not in ("auto", "ragflow"):
            return None

        try:
            from ragflow import RagflowEmbedding  # type: ignore
        except Exception:
            if mode == "ragflow":
                raise
            return None

        # Many ragflow integrations rely on env vars (api key/secret/tenant).
        # If they're not set, RagflowEmbedding is likely to fail anyway.
        if mode == "auto" and not (
            os.getenv("RAGFLOW_API_KEY") or os.getenv("RAGFLOW_SECRET_KEY")
        ):
            return None

        class _RagflowEmbeddingWrapper:
            def __init__(self) -> None:
                self._rag = RagflowEmbedding()  # type: ignore[call-arg]

            def embed(self, text: str) -> List[float]:
                vec = self._rag.embed(text)
                return [float(x) for x in vec]

            async def aembed(self, text: str) -> List[float]:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.embed, text)

        return _RagflowEmbeddingWrapper()

    def embed(self, text: str) -> List[float]:
        return self._impl.embed(text)

    async def aembed(self, text: str) -> List[float]:
        return await self._impl.aembed(text)
