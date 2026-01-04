# Criadex API Specification

## Base URL
All endpoints are rooted at:
```
http://localhost:25574/
```

Authentication: API key via HTTP header `x-api-key`.

---

## 1. Group Management
Endpoints to manage group definitions and lifecycle.

### 1.1 Create a Group
POST /groups/{group_name}/create
- Description: Create a new group.
- Path Parameters:
  - `group_name` (string, required): The unique name for the group.
- Request Body (`PartialGroupConfig`):
  ```json
  {
    "type": "DOCUMENT",
    "llm_model_id": 1,
    "embedding_model_id": 2,
    "rerank_model_id": 4
  }
  ```
- Response 200 OK (`GroupCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully created the group.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "config": {
      "type": "DOCUMENT",
      "llm_model_id": 1,
      "embedding_model_id": 2,
      "rerank_model_id": 4,
      "name": "test-group-gemini"
    }
  }
  ```

### 1.2 Get Group Info
GET /groups/{group_name}/about
- Description: Retrieve information about a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Response 200 OK (`GroupAboutResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved the group info for 'test-group-gemini'.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "info": {
      "id": 801,
      "name": "test-group-gemini",
      "type": "DOCUMENT",
      "llm_model_id": 1,
      "embedding_model_id": 2,
      "rerank_model_id": 4,
      "created": "2025-11-19T14:05:28"
    }
  }
  ```

### 1.3 Delete a Group
DELETE /groups/{group_name}/delete
- Description: Delete a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Response 200 OK:
  ```json
  {
    "status": 200,
    "message": "Successfully deleted the index group.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 1.4 Query a Group
POST /groups/{group_name}/query
- Description: Query a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Request Body:
  ```json
  {
    "query": "test"
  }
  ```
- Response 200 OK:
  ```json
  {
    "nodes": [
      {
        "node": {
          "metadata": {
            "file_name": "my-test-document.json",
            "updated_at": 1763393591041
          },
          "excluded_embed_metadata_keys": [],
          "excluded_llm_metadata_keys": [],
          "class_name": "TextNode",
          "text": "updated",
          "text_template": "{}",
          "metadata_template": "{}"
        },
        "score": 0.0
      }
    ],
    "assets": [],
    "search_units": 1,
    "status": 200,
    "message": "Successfully queried group 'test-group-gemini'.",
    "timestamp": 1763561064,
    "code": "SUCCESS"
  }
  ```

---

## 2. Authorization
Endpoints to manage API keys.

### 2.1 Create API Key
POST /auth/{api_key}/create
- Description: Create an API key.
- Path Parameters:
  - `api_key` (string, required): The API key to create.
- Request Body (`AuthKeyConfig`):
  ```json
  {
    "master": false
  }
  ```
- Response 200 OK (`AuthCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "api_key": "non-master-key-name-gemini",
    "master": false
  }
  ```

### 2.2 Validate API Key
GET /auth/{api_key}/check
- Description: Check if an API key is valid.
- Path Parameters:
  - `api_key` (string, required): The API key to check.
- Response 200 OK (`AuthCheckResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "api_key": "non-master-key-name-gemini",
    "authorized": true,
    "master": false
  }
  ```

### 2.3 Delete API Key
DELETE /auth/{api_key}/delete
- Description: Delete an API key.
- Path Parameters:
  - `api_key` (string, required): The API key to delete.
- Response 200 OK (`AuthDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "api_key": "reset-82fface045"
  }
  ```

### 2.4 Validate API Key (Keys Endpoint)
GET /auth/keys/{api_key}
- Description: Check for an API key used to access this API. This endpoint is for compatibility with older clients.
- Path Parameters:
  - `api_key` (string, required): The API key to check.
- Response 200 OK (`AuthKeysResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "api_key": "non-master-key-name-gemini",
    "authorized": true,
    "master": false
  }
  ```

### 2.5 Reset API Key
PATCH /auth/{api_key}/reset
- Description: Reset an API key.
- Path Parameters:
  - `api_key` (string, required): The API key to reset.
- Query Parameters:
  - `new_key` (string, required): The new API key.
- Response 200 OK (`AuthResetResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "new_key": "reset-82fface045"
  }
  ```

---

## 3. Group Authorization
Endpoints to manage group authorizations.

### 3.1 Add Group Authorization
POST /group_auth/{group_name}/create
- Description: Add an authorization to a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Query Parameters:
  - `api_key` (string, required): The API key to authorize.
- Response 200 OK (`GroupAuthCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 3.2 Check Group Authorization
GET /group_auth/{group_name}/check
- Description: Check if an API key is authorized for a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Query Parameters:
  - `api_key` (string, required): The API key to check.
- Response 200 OK (`GroupAuthCheckResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "authorized": true,
    "master": false
  }
  ```

### 3.3 Delete Group Authorization
DELETE /group_auth/{group_name}/delete
- Description: Delete a group authorization.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Query Parameters:
  - `api_key` (string, required): The API key to deauthorize.
- Response 200 OK (`GroupAuthDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 3.4 List Authorized Groups
GET /group_auth/list
- Description: List the groups an API key is authorized for.
- Query Parameters:
  - `api_key` (string, optional): The API key to check. Can also be passed in the `x-api-key` header.
- Response 200 OK (`GroupAuthListResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "groups": [
      {
        "id": 801,
        "name": "test-group-gemini",
        "type": 1,
        "llm_model_id": 1,
        "embedding_model_id": 2,
        "rerank_model_id": 4,
        "created": "2025-11-19T14:05:28"
      }
    ]
  }
  ```

---

## 4. Content Management
Endpoints to manage content within a group.

### 4.1 Upload Content
POST /groups/{group_name}/content/upload
- Description: Upload content to a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Request Body (`ContentUploadConfig`):
  ```json
  {
    "file_name": "my-test-document.json",
    "file_contents": {
      "nodes": [
        {
          "text": "test",
          "metadata": {},
          "type": "NarrativeText"
        }
      ],
      "assets": []
    },
    "file_metadata": {}
  }
  ```
- Response 200 OK (`ContentUploadResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully uploaded & indexed the content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "token_usage": 1,
    "document_name": "my-test-document.json"
  }
  ```

### 4.2 List Content
GET /groups/{group_name}/content/list
- Description: List content in a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Response 200 OK (`ContentListResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved index content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "files": [
      "my-test-document.json"
    ]
  }
  ```

### 4.3 Update Content
PATCH /groups/{group_name}/content/update
- Description: Update content in a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Request Body (`ContentUploadConfig`):
  ```json
  {
    "file_name": "my-test-document.json",
    "file_contents": {
      "nodes": [
        {
          "text": "updated",
          "metadata": {},
          "type": "NarrativeText"
        }
      ],
      "assets": []
    },
    "file_metadata": {}
  }
  ```
- Response 200 OK (`ContentUpdateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully updated & re-indexed the content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "token_usage": 1,
    "document_name": "my-test-document.json"
  }
  ```

### 4.4 Delete Content
DELETE /groups/{group_name}/content/delete
- Description: Delete content from a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Query Parameters:
  - `document_name` (string, required): The name of the document to delete.
- Response 200 OK (`ContentDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully deleted & de-indexed the content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 4.5 Search Content
POST /groups/{group_name}/content/search
- Description: Search content in a group.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Request Body (`SearchConfig`):
  ```json
  {
    "query": "test"
  }
  ```
- Response 200 OK (`ContentSearchResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved searched the index for the requested content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "response": {
      "nodes": [
        {
          "node": {
            "metadata": {
              "file_name": "my-test-document.json",
              "updated_at": 1763561128810
            },
            "excluded_embed_metadata_keys": [],
            "excluded_llm_metadata_keys": [],
            "class_name": "TextNode",
            "text": "updated",
            "text_template": "{}",
            "metadata_template": "{}"
          },
          "score": 0.0
        }
      ],
      "assets": [],
      "search_units": 1
    }
  }
  ```

---

## 5. Model Management

### 5.1 Azure Models

#### 5.1.1 Create Azure Model
POST /models/azure/create
- Description: Add an Azure OpenAI model config to the database.
- Request Body (`AzureModelsBaseModel`):
  ```json
  {
    "api_model": "text-embedding-ada-002",
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "your-controllers-key",
    "api_deployment": "your-deployment-name"
  }
  ```
- Response 200 OK (`AzureModelCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully created the model. Model ID returned in payload.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.2 Get Azure Model Info
GET /models/azure/{model_id}/about
- Description: Retrieve information about an Azure Model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`AzureModelAboutResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved the model config",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.3 Update Azure Model
PATCH /models/azure/{model_id}/update
- Description: Update an Azure OpenAI model config in the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`AzureModelsPartialBaseModel`):
  ```json
  {
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "your-controllers-key",
    "api_deployment": "your-deployment-name"
  }
  ```
- Response 200 OK (`AzureModelUpdateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully updated the model.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.4 Delete Azure Model
DELETE /models/azure/{model_id}/delete
- Description: Delete an Azure OpenAI model config from the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`AzureModelDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully deleted the model",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 5.2 Cohere Models

#### 5.2.1 Create Cohere Model
POST /models/cohere/create
- Description: Add a Cohere model config to the database.
- Request Body (`CohereModelsBaseModel`):
  ```json
  {
    "api_model": "rerank-multilingual-v2.0",
    "api_key": "your-controllers-key"
  }
  ```
- Response 200 OK (`CohereModelCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully created the model. Model ID returned in payload.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_key": "fake",
      "api_model": "rerank-multilingual-v2.0",
      "id": 5
    }
  }
  ```

#### 5.2.2 Get Cohere Model Info
GET /models/cohere/{model_id}/about
- Description: Retrieve information about a Cohere Model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`CohereModelAboutResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved the model config",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_key": "fake",
      "api_model": "rerank-multilingual-v2.0",
      "id": 5
    }
  }
  ```

#### 5.2.3 Update Cohere Model
PATCH /models/cohere/{model_id}/update
- Description: Update a Cohere model config in the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`CohereModelsPartialBaseModel`):
  ```json
  {
    "api_key": "your-controllers-key"
  }
  ```
- Response 200 OK (`CohereModelUpdateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully updated the model.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_key": "fake",
      "api_model": "rerank-multilingual-v2.0",
      "id": 5
    }
  }
  ```

#### 5.2.4 Delete Cohere Model
DELETE /models/cohere/{model_id}/delete
- Description: Delete a Cohere model config from the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`CohereModelDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully deleted the model",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

#### 5.2.5 Rerank with Cohere
POST /models/{model_id}/rerank
- Description: Rerank documents using a Cohere model.
- Path Parameters:
  - `model_id` (int, required): The ID of the Cohere model.
- Request Body (`CohereRerankRequest`):
  ```json
  {
    "query": "best?",
    "documents": [
      {
        "text": "A"
      },
      {
        "text": "B"
      },
      {
        "text": "C"
      }
    ]
  }
  ```
- Response 200 OK (`CohereRerankResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully reranked documents using Cohere model 5.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "reranked_documents": [
      {
        "text": "A"
      },
      {
        "text": "B"
      },
      {
        "text": "C"
      }
    ]
  }
  ```

---

## 6. Agents

### 6.1 Ragflow Agents

#### 6.1.1 Chat
POST /models/ragflow/{model_id}/agents/chat
- Description: Chat with a Ragflow model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body:
  ```json
  {
    "prompt": "hi"
  }
  ```
- Response 200 OK:
  ```json
  {
    "agent_response": {
      "chat_response": {
        "message": {
          "role": "assistant",
          "blocks": [
            {
              "block_type": "text",
              "text": "Error: Invalid response from Ragflow API."
            }
          ],
          "additional_kwargs": {},
          "metadata": {}
        },
        "raw": {
          "code": 100,
          "data": null,
          "message": "<NotFound '404: Not Found'>"
        }
      },
      "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 9,
        "total_tokens": 10,
        "label": "ChatAgent"
      },
      "message": "Successfully queried the model!",
      "model_id": 1
    }
  }
  ```

#### 6.1.2 Intents
POST /models/ragflow/{model_id}/agents/intents
- Description: Get intents from a Ragflow model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`IntentsRequest`):
  ```json
  {
    "text": "weather"
  }
  ```
- Response 200 OK:
  ```json
  {
    "agent_response": {
      "ranked_intents": [],
      "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 0,
        "total_tokens": 10,
        "label": "IntentsAgent"
      },
      "message": "Successfully ranked intents",
      "model_id": 1
    }
  }
  ```

#### 6.1.3 Language
POST /models/ragflow/{model_id}/agents/language
- Description: Detect language with a Ragflow model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`LanguageRequest`):
  ```json
  {
    "text": "hello"
  }
  ```
- Response 200 OK (`LanguageAgentResponse`):
  ```json
  {
    "language": "ST",
    "confidence": 0.17332524358443202
  }
  ```

#### 6.1.4 Related Prompts
POST /models/{model_id}/related_prompts
- Description: Get related prompts from a Ragflow model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`AgentRelatedPromptsResponse`):
  ```json
  {
    "agent_response": {
      "message": null,
      "usage": [
        {
          "completion_tokens": 0,
          "prompt_tokens": 0,
          "total_tokens": 0,
          "usage_label": "RelatedPromptsAgent"
        }
      ],
      "related_prompts": []
    }
  }
  ```

#### 6.1.5 Transform
POST /models/ragflow/{model_id}/agents/transform
- Description: Transform text with a Ragflow model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`TransformRequest`):
  ```json
  {
    "text": "change"
  }
  ```
- Response 200 OK (`TransformAgentResponse`):
  ```json
  {
    "transformed_text": "CHANGE"
  }
  ```

---

## 5. Model Management

### 5.1 Azure Models

#### 5.1.1 Create Azure Model
POST /models/azure/create
- Description: Add an Azure OpenAI model config to the database.
- Request Body (`AzureModelsBaseModel`):
  ```json
  {
    "api_model": "text-embedding-ada-002",
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "your-controllers-key",
    "api_deployment": "your-deployment-name"
  }
  ```
- Response 200 OK (`AzureModelCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully created the model. Model ID returned in payload.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.2 Get Azure Model Info
GET /models/azure/{model_id}/about
- Description: Retrieve information about an Azure Model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`AzureModelAboutResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved the model config",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.3 Update Azure Model
PATCH /models/azure/{model_id}/update
- Description: Update an Azure OpenAI model config in the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`AzureModelsPartialBaseModel`):
  ```json
  {
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "your-controllers-key",
    "api_deployment": "your-deployment-name"
  }
  ```
- Response 200 OK (`AzureModelUpdateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully updated the model.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_resource": "your-resource",
      "api_version": "2023-05-15",
      "api_key": "fake",
      "api_deployment": "your-deployment-name",
      "api_model": "text-embedding-ada-002",
      "id": 13
    }
  }
  ```

#### 5.1.4 Delete Azure Model
DELETE /models/azure/{model_id}/delete
- Description: Delete an Azure OpenAI model config from the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`AzureModelDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully deleted the model",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```
