from criadex.database.tables.models.azure import AzureModelsModel
from criadex.database.tables.models.cohere import CohereModelsModel
from criadex.database.tables.models.generic import GenericModelsModel
from criadex.models.usability import (
    infer_model_type,
    is_azure_model_usable,
    is_cohere_model_usable,
    is_generic_model_usable,
)


def test_placeholder_azure_models_are_not_usable() -> None:
    model = AzureModelsModel(
        id=1,
        api_model="gpt-4",
        api_resource="your-resource-gpt-4",
        api_deployment="your-deployment-gpt-4",
        api_key="",
    )
    assert is_azure_model_usable(model) is False


def test_configured_azure_model_is_usable() -> None:
    model = AzureModelsModel(
        id=2,
        api_model="gpt-4",
        api_resource="criadex-llm-prod",
        api_deployment="criadex-llm-deploy",
        api_key="real-key",
    )
    assert is_azure_model_usable(model) is True


def test_cohere_without_api_key_is_not_usable() -> None:
    model = CohereModelsModel(id=1, api_model="rerank-english-v3.0", api_key="")
    assert is_cohere_model_usable(model) is False


def test_ragflow_generic_model_is_usable() -> None:
    model = GenericModelsModel(
        id=3,
        provider_type="ragflow",
        config={
            "api_model": "gpt-5.4",
            "llm_name": "gpt-5.4",
            "llm_factory": "OpenAI",
            "model_type": "chat",
            "tenant_id": "cf25af063cc611f1ab456202e7812f6d",
            "status": "1",
        },
    )
    assert is_generic_model_usable(model) is True
    assert infer_model_type("ragflow", "gpt-5.4", model.config) == "chat"


def test_ragflow_embedding_model_type() -> None:
    model = GenericModelsModel(
        id=4,
        provider_type="ragflow",
        config={
            "api_model": "text-embedding-3-large",
            "model_type": "embedding",
            "status": "1",
        },
    )
    assert infer_model_type("ragflow", model.config["api_model"], model.config) == "embedding"
