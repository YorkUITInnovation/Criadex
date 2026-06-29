from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from pydantic import BaseModel
from starlette.requests import Request

from app.controllers.schemas import catch_exceptions, APIResponse, SUCCESS, ERROR
from app.core.route import CriaRoute
from criadex.database.tables.models.generic import GenericModelsModel, GenericModelsBaseModel

view = APIRouter()


class GenericModelConfig(BaseModel):
    """Flexible config for any provider - common fields + extra as dict."""
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_model: Optional[str] = None

    class Config:
        extra = "allow"


class GenericModelCreateResponse(APIResponse):
    code: Union[SUCCESS, ERROR]
    model: Optional[GenericModelsModel] = None


@cbv(view)
class CreateGenericModelRoute(CriaRoute):
    ResponseModel = GenericModelCreateResponse

    @view.post(
        path="/models/{provider_type}/create",
        name="Add a Generic Model",
        summary="Add a model for providers (ollama, openai, anthropic, etc.)",
        description="Add a model config for extensible LLM providers. Use /models/azure/* or /models/cohere/* for those.",
    )
    @catch_exceptions(ResponseModel)
    async def execute(
        self,
        request: Request,
        provider_type: str,
        model_config: GenericModelConfig
    ) -> ResponseModel:
        if provider_type.lower() in ("azure", "cohere"):
            raise HTTPException(
                status_code=404,
                detail="Use /models/azure/* or /models/cohere/* for this provider."
            )
        db = request.app.criadex.mysql_api
        config_dict = model_config.model_dump(exclude_none=True)
        provider = provider_type.lower()
        api_model = (config_dict.get("api_model") or "").strip()
        if api_model:
            existing = await db.generic_models.find_by_provider_and_api_model(provider, api_model)
            if existing:
                return self.ResponseModel(
                    code="SUCCESS",
                    status=200,
                    message="Model already exists.",
                    model=existing,
                )

        base = GenericModelsBaseModel(provider_type=provider, config=config_dict)
        model = await db.generic_models.insert(config=base)
        return self.ResponseModel(
            code="SUCCESS",
            status=200,
            message="Successfully created the model.",
            model=model
        )


__all__ = ["view", "GenericModelCreateResponse"]
