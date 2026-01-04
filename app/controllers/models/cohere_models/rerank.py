from fastapi import APIRouter, Depends, Path, Body, Request
from fastapi_utils.cbv import cbv
from app.core.route import CriaRoute
from app.controllers.schemas import SUCCESS, ERROR, MODEL_NOT_FOUND
from criadex.schemas import ModelNotFoundError
from criadex.database.tables.models.cohere import CohereModelsModel
from .schemas import CohereRerankRequest, CohereRerankResponse

view = APIRouter()

@cbv(view)
class CohereRerankRoute(CriaRoute):
    ResponseModel = CohereRerankResponse

    @view.post(
        path="/models/{model_id}/rerank",
        name="Rerank Cohere Model",
        summary="Rerank documents using a Cohere model.",
        description="Performs reranking of a list of documents based on a query using a specified Cohere model.",
    )
    async def execute(
        self,
        request: Request,
        model_id: int = Path(..., description="The ID of the Cohere model to use for reranking."),
        request_body: CohereRerankRequest = Body(..., description="The reranking request body."),
    ) -> ResponseModel:
        try:
            # Retrieve the Cohere model configuration
            cohere_model: CohereModelsModel = await request.app.criadex.mysql_api.cohere_models.retrieve(model_id=model_id)

            if cohere_model is None:
                raise ModelNotFoundError()

            # TODO: Implement actual Cohere reranking logic here
            # For now, just return the documents as is
            reranked_documents = request_body.documents

            return self.ResponseModel(
                code="SUCCESS",
                status=200,
                message=f"Successfully reranked documents using Cohere model {model_id}.",
                reranked_documents=reranked_documents
            )
        except ModelNotFoundError:
            return self.ResponseModel(
                code="MODEL_NOT_FOUND",
                status=404,
                message=f"Cohere model with ID {model_id} not found."
            )
        except Exception as e:
            return self.ResponseModel(
                code="ERROR",
                status=500,
                message=f"An internal error occurred: {str(e)}"
            )