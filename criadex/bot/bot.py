"""
Bot module for Criadex (Elasticsearch version)
Implements bot logic for semantic search, chat, and orchestration.
"""

from typing import Optional
from criadex.agent.azure.chat import ChatAgent
from criadex.core.event import Event
from criadex.index.schemas import IndexResponse, TextNodeWithScore, TextNode, BaseNode


class Bot:
    """
    Bot orchestration for Criadex (Elasticsearch version)
    Handles semantic search, chat, and event-driven flows.
    """
    def __init__(self, vector_store, embedder, event: Event = None):
        self.vector_store = vector_store
        self.embedder = embedder
        self.event = event or Event()

    async def search(self, group_name: str, query: str, top_k=10, query_filter: Optional[dict] = None):
        # Emit event for search
        self.event.emit(Event.SEARCH, query=query)

        # Embed the query
        embedding = self.embedder.embed(query)

        # Implement semantic search using Elasticsearch vector store
        if hasattr(self.vector_store, 'asearch'):
            hits = await self.vector_store.asearch(
                collection_name=group_name, 
                query_embedding=embedding, 
                top_k=top_k,
                sort={"metadata.updated_at": {"order": "desc"}},
                query_filter=query_filter # Pass the query_filter here
            )

            nodes = []
            for hit in hits:
                src = hit.get('_source', {})
                text = src.get('text')
                metadata = src.get('metadata', {})
                score = hit.get('_score', 0.0)

                base_node = BaseNode(
                    metadata=metadata,
                    class_name='TextNode'
                )

                text_node = TextNode(
                    text=text,
                    metadata=metadata,
                    class_name='TextNode',
                    text_template='{}',
                    metadata_template='{}'
                )

                node_with_score = TextNodeWithScore(
                    node=text_node,
                    score=score
                )
                nodes.append(node_with_score)

            return IndexResponse(nodes=nodes, assets=[])

        # Fallback: return empty result
        return IndexResponse(nodes=[])

    async def chat(self, message: str, llm_model_id: int, context: Optional[str] = None):
        # Emit event for chat
        self.event.emit('chat', message=message, context=context)

        history = [{"role": "user", "content": message}]
        if context:
            history.insert(0, {"role": "system", "content": context})

        agent = ChatAgent(llm_model_id=llm_model_id)
        response = await agent.execute(history=history)
        return response


