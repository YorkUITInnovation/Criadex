import uuid

from criadex.database.tables.models.azure import AzureModelsModel, AzureModelsPartialBaseModel
from criadex.database.tables.models.cohere import CohereModelsModel, CohereModelsPartialBaseModel


def create_test_azure_model() -> AzureModelsModel:
    return AzureModelsModel(
        api_resource='pytest-api-resource',
        api_version='pytest-api-version',
        api_key='pytest-api-key',
        api_deployment='pytest-api-deployment',
        api_model='gpt-4o',
    )


def update_test_azure_model() -> AzureModelsPartialBaseModel:
    model = create_test_azure_model()
    model.api_deployment = 'pytest-api-model-updated-' + str(uuid.uuid4())

    return AzureModelsPartialBaseModel(
        **model.model_dump()
    )


def create_test_cohere_model() -> CohereModelsModel:
    return CohereModelsModel(
        api_key='pytest-api-key',
        api_model='rerank-multilingual-v2.0',
    )


def update_test_cohere_model() -> CohereModelsPartialBaseModel:
    model = create_test_cohere_model()
    model.api_deployment = 'pytest-api-model-updated-' + str(uuid.uuid4())

    return CohereModelsPartialBaseModel(
        **model.model_dump()
    )
