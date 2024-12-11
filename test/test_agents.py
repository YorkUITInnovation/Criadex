import json
import uuid

import pytest
from httpx import Response

from app.controllers.content.delete import ContentDeleteResponse
from app.controllers.content.list import ContentListResponse
from app.controllers.content.search import ContentSearchResponse
from app.controllers.content.update import ContentUpdateResponse
from app.controllers.content.upload import ContentUploadResponse
from criadex.index.base_api import ContentUploadConfig
from criadex.index.index_api.document.index_objects import DocumentConfig
from criadex.index.index_api.question.index_objects import QuestionConfig
from criadex.index.schemas import SearchConfig, TextNodeWithScore, IndexResponse
from utils.content_utils import sample_document, sample_document_updated, sample_question, sample_question_updated
from utils.misc_utils import assert_exists_index
from utils.test_client import CriaTestClient, sample_question_index, client, sample_non_master_key, sample_master_headers, assert_response_shape, sample_document_index


@pytest.mark.asyncio
async def test_group_content_document_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_document_index: str,
        sample_non_master_key: str
) -> None:

    # Confirm the index exists before performing test operations
    await assert_exists_index(client, sample_master_headers, sample_document_index)

    sample_doc: DocumentConfig = sample_document()
    sample_doc_name: str = "pytest-doc-" + str(uuid.uuid4())

    # A test upload config for the test document index
    content_upload_config: ContentUploadConfig = ContentUploadConfig(
        file_name=sample_doc_name,
        file_contents=sample_doc.dict(),
        file_metadata={"pytest-sample-file-metadata": "pytest-sample-file-metadata-value"}
    )

    # (1) Upload the sample document
    response = client.post(
        f"/groups/{sample_document_index}/content/upload",
        headers=sample_master_headers,
        json=json.loads(content_upload_config.model_dump_json())
    )

    print(json.loads(content_upload_config.model_dump_json()))
    response_data: ContentUploadResponse = assert_response_shape(response.json(), custom_shape=ContentUploadResponse)

    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to upload the sample document"

    # (2) Check if the document was uploaded successfully by querying the group content list
    response_data: ContentListResponse = client.get_json(
        f"/groups/{sample_document_index}/content/list",
        headers=sample_master_headers,
        apply_shape=ContentListResponse,
        apply_shape_require_code="SUCCESS",
        apply_shape_require_status=200
    )

    # Confirm the doc was inserted into the content list
    assert sample_doc_name in response_data.files, "The sample document was not found in the group content list"

    # (3) Apply an update to the document contents
    updated_doc = sample_document_updated()
    updated_node = updated_doc.nodes[-1]
    update_id: str = updated_node.metadata['update_id']

    content_upload_config.file_contents = updated_doc.dict()
    response: Response = client.patch(
        f"/groups/{sample_document_index}/content/update",
        headers=sample_master_headers,
        json=json.loads(content_upload_config.model_dump_json())
    )

    response_data: ContentUpdateResponse = assert_response_shape(response.json(), custom_shape=ContentUpdateResponse)

    # Confirm the update was successful
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to update the sample document"

    json_payload: SearchConfig = SearchConfig(
        prompt=updated_node.text,
        top_k=1,
        rerank_enabled=True
    )

    # (4) Search the index with a query that should return the updated document node
    response: Response = client.post(
        f"/groups/{sample_document_index}/content/search",
        headers=sample_master_headers,
        json=json.loads(json_payload.model_dump_json())
    )

    response_data: ContentSearchResponse = assert_response_shape(response.json(), custom_shape=ContentSearchResponse)

    # Confirm the updated node is returned in the search results & also run checks for re-ranking by looking at the metadata
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to search the index for the updated document"

    index_response: IndexResponse = response_data.response

    try:
        assert len(index_response.nodes) == 1
    except AssertionError:
        assert len(index_response.nodes) < 1, "The search results returned more than one node! Top_K and/or Top_N was ignored."
        assert len(index_response.nodes) > 1, "The search results returned less than one node! Top_K and/or Top_N was ignored."

    top_node: TextNodeWithScore = index_response.nodes[0]

    # Confirm the updated node is returned in the search results
    # This:
    # 1) Confirms the update from before worked
    # 2) Confirms the search functionality is working
    # 3) Confirms that metadata is in fact being stored properly
    assert top_node.metadata['update_id'] == update_id, "The search results did not return the updated document node. Either search is broken, or the document was not updated correctly."

    # (5) Delete the document
    response: Response = client.delete(
        f"/groups/{sample_document_index}/content/delete?document_name={sample_doc_name}",
        headers=sample_master_headers
    )

    response_data: ContentDeleteResponse = assert_response_shape(response.json(), custom_shape=ContentDeleteResponse)

    # Confirm the document was deleted
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the sample document"

    # (6) Re-check the content list to confirm the document was deleted
    response_data: ContentListResponse = client.get_json(
        f"/groups/{sample_document_index}/content/list",
        headers=sample_master_headers,
        apply_shape=ContentListResponse,
        apply_shape_require_code="SUCCESS",
        apply_shape_require_status=200
    )

    # Confirm the doc was removed from the content list
    assert sample_doc_name not in response_data.files, "The sample document was not deleted from the group content list"


@pytest.mark.asyncio
async def test_group_content_question_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
        sample_question_index: str,
        sample_non_master_key: str
) -> None:
    """
    Test the group auth-related routes:
    - /group_auth/{group}/create
    - /group_auth/{group}/check
    - /group_auth/{group}/delete
    - /group_auth/list

    """

    # Confirm the index exists before performing test operations
    await assert_exists_index(client, sample_master_headers, sample_question_index)

    sample_doc: QuestionConfig = sample_question()
    sample_doc_name: str = "pytest-doc-" + str(uuid.uuid4())

    # A test upload config for the test document index
    content_upload_config: ContentUploadConfig = ContentUploadConfig(
        file_name=sample_doc_name,
        file_contents=sample_doc.dict(),
        file_metadata={"pytest-sample-file-metadata": "pytest-sample-file-metadata-value"}
    )

    # (1) Upload the sample document
    response = client.post(
        f"/groups/{sample_question_index}/content/upload",
        headers=sample_master_headers,
        json=json.loads(content_upload_config.model_dump_json())
    )

    response_data: ContentUploadResponse = assert_response_shape(response.json(), custom_shape=ContentUploadResponse)
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to upload the sample question"

    # (2) Check if the document was uploaded successfully by querying the group content list
    response_data: ContentListResponse = client.get_json(
        f"/groups/{sample_question_index}/content/list",
        headers=sample_master_headers,
        apply_shape=ContentListResponse,
        apply_shape_require_code="SUCCESS",
        apply_shape_require_status=200
    )

    # Confirm the doc was inserted into the content list
    assert sample_doc_name in response_data.files, "The sample question was not found in the group content list"

    # (3) Apply an update to the document contents
    updated_doc, update_id = sample_question_updated()

    content_upload_config.file_contents = updated_doc.dict()
    response: Response = client.patch(
        f"/groups/{sample_question_index}/content/update",
        headers=sample_master_headers,
        json=json.loads(content_upload_config.model_dump_json())
    )

    response_data: ContentUpdateResponse = assert_response_shape(response.json(), custom_shape=ContentUpdateResponse)

    # Confirm the update was successful
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to update the sample question"

    json_payload: SearchConfig = SearchConfig(
        prompt=updated_doc.questions[0],
        top_k=1,
        rerank_enabled=True
    )

    # (4) Search the index with a query that should return the updated document node
    response: Response = client.post(
        f"/groups/{sample_question_index}/content/search",
        headers=sample_master_headers,
        json=json.loads(json_payload.model_dump_json())
    )

    response_data: ContentSearchResponse = assert_response_shape(response.json(), custom_shape=ContentSearchResponse)

    # Confirm the updated node is returned in the search results & also run checks for re-ranking by looking at the metadata
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to search the index for the question document"

    index_response: IndexResponse = response_data.response

    try:
        assert len(index_response.nodes) == 1
    except AssertionError:
        assert len(index_response.nodes) < 1, "The question search results returned more than one node! Top_K and/or Top_N was ignored."
        assert len(index_response.nodes) > 1, "The question search results returned less than one node! Top_K and/or Top_N was ignored."

    top_node: TextNodeWithScore = index_response.nodes[0]

    # Confirm the updated node is returned in the search results
    # This:
    # 1) Confirms the update from before worked
    # 2) Confirms the search functionality is working
    # 3) Confirms that metadata is in fact being stored properly
    assert update_id in top_node.text, "The search results did not return the updated question node. Either search is broken, or the question was not updated correctly."

    # (5) Delete the document
    response: Response = client.delete(
        f"/groups/{sample_question_index}/content/delete?document_name={sample_doc_name}",
        headers=sample_master_headers
    )

    response_data: ContentDeleteResponse = assert_response_shape(response.json(), custom_shape=ContentDeleteResponse)

    # Confirm the document was deleted
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the sample question"

    # (6) Re-check the content list to confirm the document was deleted
    response_data: ContentListResponse = client.get_json(
        f"/groups/{sample_question_index}/content/list",
        headers=sample_master_headers,
        apply_shape=ContentListResponse,
        apply_shape_require_code="SUCCESS",
        apply_shape_require_status=200
    )

    # Confirm the doc was removed from the content list
    assert sample_doc_name not in response_data.files, "The sample question was not deleted from the group content list"
