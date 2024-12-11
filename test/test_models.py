import json

import pytest
from httpx import Response

from app.controllers.models.azure_models.about import AzureModelAboutResponse
from app.controllers.models.azure_models.create import AzureModelCreateResponse
from app.controllers.models.azure_models.delete import AzureModelDeleteResponse
from app.controllers.models.azure_models.update import AzureModelUpdateResponse
from app.controllers.models.cohere_models.about import CohereModelAboutResponse
from app.controllers.models.cohere_models.create import CohereModelCreateResponse
from app.controllers.models.cohere_models.delete import CohereModelDeleteResponse
from app.controllers.models.cohere_models.update import CohereModelUpdateResponse
from criadex.database.tables.models.azure import AzureModelsModel, AzureModelsPartialBaseModel
from criadex.database.tables.models.cohere import CohereModelsModel, CohereModelsPartialBaseModel
from utils.models_utils import create_test_azure_model, update_test_azure_model, create_test_cohere_model, update_test_cohere_model
from utils.test_client import CriaTestClient, assert_response_shape, client, sample_master_headers


@pytest.mark.asyncio
async def test_models_azure_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
) -> None:
    test_model: AzureModelsModel = create_test_azure_model()

    # (1) Create a test model
    response: Response = client.post(
        f"/models/azure/create",
        headers=sample_master_headers,
        json=json.loads(test_model.json())
    )

    response_data: AzureModelCreateResponse = assert_response_shape(response.json(), custom_shape=AzureModelCreateResponse)
    model_id: int = response_data.model.id

    # Run checks on the response to see if the model was created
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to create the test model!"
    assert response_data.model.api_resource == test_model.api_resource, "The API resource does not match the test model"
    assert response_data.model.api_version == test_model.api_version, "The API version does not match the test model"
    assert response_data.model.api_key == test_model.api_key, "The API key does not match the test model"
    assert response_data.model.api_deployment == test_model.api_deployment, "The API deployment does not match the test model"
    assert response_data.model.api_model == test_model.api_model, "The API model does not match the test model"

    # (2) Check if the test model exists
    response: Response = client.get(f"/models/azure/{model_id}/about", headers=sample_master_headers)
    response_data: AzureModelAboutResponse = assert_response_shape(response.json(), custom_shape=AzureModelAboutResponse)

    # Run checks on the response to see if the model exists
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to check the test model"
    assert response_data.model.api_resource == test_model.api_resource, "The API resource does not match the test model"
    assert response_data.model.api_version == test_model.api_version, "The API version does not match the test model"
    assert response_data.model.api_key == test_model.api_key, "The API key does not match the test model"
    assert response_data.model.api_deployment == test_model.api_deployment, "The API deployment does not match the test model"
    assert response_data.model.api_model == test_model.api_model, "The API model does not match the test model"

    # (3) Update the model
    updated_model: AzureModelsPartialBaseModel = update_test_azure_model()

    response: Response = client.patch(
        f"/models/azure/{model_id}/update",
        headers=sample_master_headers,
        json=json.loads(updated_model.json())
    )

    response_data: AzureModelUpdateResponse = assert_response_shape(response.json(), custom_shape=AzureModelUpdateResponse)

    assert response_data.status == 200, "Failed to update the test model"
    assert response_data.model.api_resource == updated_model.api_resource, "The API resource does not match the updated model"
    assert response_data.model.api_version == updated_model.api_version, "The API version does not match the updated model"
    assert response_data.model.api_key == updated_model.api_key, "The API key does not match the updated model"
    assert response_data.model.api_deployment == updated_model.api_deployment, "The API deployment does not match the updated model"

    # (4) Check if the updated model exists
    response: Response = client.delete(f"/models/azure/{model_id}/delete", headers=sample_master_headers)
    response_data: AzureModelDeleteResponse = assert_response_shape(response.json(), custom_shape=AzureModelDeleteResponse)

    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the test model"


@pytest.mark.asyncio
async def test_models_cohere_positive(
        client: CriaTestClient,
        sample_master_headers: dict,
) -> None:
    test_model: CohereModelsModel = create_test_cohere_model()

    # (1) Create a test model
    response: Response = client.post(
        f"/models/cohere/create",
        headers=sample_master_headers,
        json=json.loads(test_model.json())
    )

    response_data: CohereModelCreateResponse = assert_response_shape(response.json(), custom_shape=CohereModelCreateResponse)
    model_id: int = response_data.model.id

    # Run checks on the response to see if the model was created
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to create the test model!"
    assert response_data.model.api_key == test_model.api_key, "The API key does not match the test model"
    assert response_data.model.api_model == test_model.api_model, "The API model does not match the test model"

    # (2) Check if the test model exists
    response: Response = client.get(f"/models/cohere/{model_id}/about", headers=sample_master_headers)
    response_data: CohereModelAboutResponse = assert_response_shape(response.json(), custom_shape=CohereModelAboutResponse)

    # Run checks on the response to see if the model exists
    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to check the test model"
    assert response_data.model.api_key == test_model.api_key, "The API key does not match the test model"
    assert response_data.model.api_model == test_model.api_model, "The API model does not match the test model"

    # (3) Update the model
    updated_model: CohereModelsPartialBaseModel = update_test_cohere_model()

    response: Response = client.patch(
        f"/models/cohere/{model_id}/update",
        headers=sample_master_headers,
        json=json.loads(updated_model.json())
    )

    response_data: CohereModelUpdateResponse = assert_response_shape(response.json(), custom_shape=CohereModelUpdateResponse)

    assert response_data.status == 200, "Failed to update the test model"
    assert response_data.model.api_key == updated_model.api_key, "The API key does not match the updated model"

    # (4) Check if the updated model exists
    response: Response = client.delete(f"/models/cohere/{model_id}/delete", headers=sample_master_headers)
    response_data: CohereModelDeleteResponse = assert_response_shape(response.json(), custom_shape=CohereModelDeleteResponse)

    assert response_data.status == 200 and response_data.code == "SUCCESS", "Failed to delete the test model"
