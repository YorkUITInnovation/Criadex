from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from criadex.criadex import Criadex


@pytest.mark.asyncio
async def test_insert_file_document_nodes_with_raw_payload() -> None:
    criadex = Criadex(
        mysql_credentials=SimpleNamespace(),
        elasticsearch_credentials=SimpleNamespace(),
    )

    criadex.get_id = AsyncMock(return_value=123)
    criadex.mark_graph_stale = AsyncMock()

    criadex.mysql_api = SimpleNamespace(
        documents=SimpleNamespace(
            exists=AsyncMock(return_value=False),
            insert=AsyncMock(),
        )
    )

    criadex.vector_store = SimpleNamespace(ainsert=AsyncMock())
    criadex.embedder = SimpleNamespace(embed=lambda _text: [0.1, 0.2, 0.3])

    # Mix dict and object node payloads to cover both input branches.
    file_contents = {
        "nodes": [
            {"text": "first node text", "metadata": {"topic": "a"}},
            SimpleNamespace(text="second node", metadata={"topic": "b"}),
        ],
        "assets": [],
    }

    token_usage = await criadex.insert_file(
        group_name="group-a",
        file_name="doc-a",
        file_contents=file_contents,
        file_metadata={"course_id": "42"},
    )

    assert token_usage == 5
    assert criadex.vector_store.ainsert.await_count == 2

    first_call = criadex.vector_store.ainsert.await_args_list[0].kwargs
    second_call = criadex.vector_store.ainsert.await_args_list[1].kwargs

    assert first_call["collection_name"] == "group-a"
    assert first_call["doc_id"] == "doc-a-0"
    assert first_call["metadata"]["topic"] == "a"
    assert first_call["metadata"]["course_id"] == "42"
    assert first_call["metadata"]["file_name"] == "doc-a"

    assert second_call["doc_id"] == "doc-a-1"
    assert second_call["metadata"]["topic"] == "b"
    assert second_call["metadata"]["course_id"] == "42"

    criadex.mysql_api.documents.insert.assert_awaited_once_with(document_name="doc-a", group_id=123)
    criadex.mark_graph_stale.assert_awaited_once_with(group_name="group-a", reason="content_uploaded")


@pytest.mark.asyncio
async def test_insert_file_questions_includes_answer_node() -> None:
    criadex = Criadex(
        mysql_credentials=SimpleNamespace(),
        elasticsearch_credentials=SimpleNamespace(),
    )

    criadex.get_id = AsyncMock(return_value=456)
    criadex.mark_graph_stale = AsyncMock()

    criadex.mysql_api = SimpleNamespace(
        documents=SimpleNamespace(
            exists=AsyncMock(return_value=False),
            insert=AsyncMock(),
        )
    )

    criadex.vector_store = SimpleNamespace(ainsert=AsyncMock())
    criadex.embedder = SimpleNamespace(embed=lambda _text: [0.9])

    token_usage = await criadex.insert_file(
        group_name="group-q",
        file_name="doc-q",
        file_contents={
            "questions": ["what is ai"],
            "answer": "ai is artificial intelligence",
        },
        file_metadata={"source": "unit-test"},
    )

    assert token_usage == 7
    assert criadex.vector_store.ainsert.await_count == 2

    first_call = criadex.vector_store.ainsert.await_args_list[0].kwargs
    second_call = criadex.vector_store.ainsert.await_args_list[1].kwargs

    assert first_call["text"] == "what is ai"
    assert second_call["text"] == "ai is artificial intelligence"
    assert first_call["metadata"]["source"] == "unit-test"
    assert second_call["metadata"]["source"] == "unit-test"

    criadex.mysql_api.documents.insert.assert_awaited_once_with(document_name="doc-q", group_id=456)
    criadex.mark_graph_stale.assert_awaited_once_with(group_name="group-q", reason="content_uploaded")
