import uuid

from criadex.database.tables.models.azure import AzureModelsModel, AzureModelsPartialBaseModel
from criadex.database.tables.models.cohere import CohereModelsModel, CohereModelsPartialBaseModel, CohereModelsBaseModel


def create_test_azure_model() -> AzureModelsModel:
    return AzureModelsModel(
        api_resource='pytest-api-resource-' + str(uuid.uuid4()),
        api_version='pytest-api-version',
        api_key='pytest-api-key',
        api_deployment='pytest-api-deployment-' + str(uuid.uuid4()),
        api_model='gpt-4o',
    )


def update_test_azure_model() -> AzureModelsPartialBaseModel:
    return AzureModelsPartialBaseModel(
        api_deployment='pytest-api-model-updated-' + str(uuid.uuid4())
    )


def create_test_cohere_model() -> CohereModelsBaseModel:
    return CohereModelsBaseModel(
        api_key='pytest-api-key-' + str(uuid.uuid4()),
        api_model='rerank-multilingual-v2.0',
    )


def update_test_cohere_model() -> CohereModelsPartialBaseModel:
    return CohereModelsPartialBaseModel(
        api_key='pytest-api-key-updated',
    )