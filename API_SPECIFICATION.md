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
- Description: Create an API key. Requires master key authorization.
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
- Description: Check for an API key. Equivalent to §2.2, kept for compatibility with older clients. Does not error when the key doesn't exist — returns `authorized: false` instead.
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
- Description: Rotate the token for an existing API key without recreating its authorizations. Requires a master key.
- Path Parameters:
  - `api_key` (string, required): The existing API key.
- Query Parameters:
  - `new_key` (string, required): The new API key value.
- Response 200 OK (`AuthResetResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully completed the request!",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "new_key": "new-api-key-2"
  }
  ```
- Response 404 (`NOT_FOUND`) if `api_key` doesn't exist; 409 (`ERROR`) if `new_key` already exists.

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
- Description: Self-service — list the index groups an API key is authorized on. Not gated behind the master-key dependency (any caller can list groups for a key they provide).
- Query Parameters or `x-api-key` header:
  - `api_key` (string, required): The API key to look up (query param or header).
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
- Response 401 if no `api_key` provided; 404 (`NOT_FOUND`) if the key doesn't exist.

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
- Description: Query a group's index directly (lower-level than §1.4 Query a Group).
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
    "status": 200,
    "message": "Successfully retrieved searched the index for the requested content.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "response": {
      "nodes": [
        {
          "node": {
            "metadata": {"file_name": "my-test-document.json", "updated_at": 1763561128810},
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

### 4.6 Upload Raw File (Native Ragflow Parse)
POST /groups/{group_name}/content/upload/file
- Description: Upload a raw file (PDF, DOCX, HTML, TXT, …) directly to Ragflow for native parsing/chunking/indexing — replaces CriaParse. Different from §4.1, which takes already-parsed nodes; this takes raw bytes.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Request Body (`multipart/form-data`):
  - `file` (file, required): The raw file content.
  - `filename_override` (string, optional): Overrides the stored document name (defaults to the uploaded filename).
  - `strategy` (string, optional): One of `GENERIC` (default — raw Ragflow native parse), `ALSYLLABUS`, `ALSYLLABUSFR`, `PARAGRAPH` (pre-processes to plain text before handing to Ragflow, e.g. for HTML input).
- Response 200 OK (`NativeFileUploadResponse`):
  ```json
  {
    "status": 200,
    "message": "File queued for native Ragflow parsing.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "document_name": "syllabus.pdf"
  }
  ```
- Response 409 (`DUPLICATE`) if a document with that name already exists; 404 (`GROUP_NOT_FOUND`) if the group doesn't exist.

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
    "api_resource": "your-resource-name",
    "api_version": "2023-05-15",
    "api_key": "your-key",
    "api_deployment": "your-deployment-name"
  }
  ```
  Note: `api_resource` can be the resource name or the full Azure endpoint URL.
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
    "api_resource": "https://new-resource.openai.azure.com/",
    "api_version": "2023-05-15",
    "api_key": "your-key",
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
      "api_resource": "new-resource",
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
    "api_key": "your-key"
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
    "api_key": "your-key"
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

### 5.3 Generic Models
Endpoints for OpenAI-compatible generic LLM providers.

#### 5.3.1 Create Generic Model
POST /models/generic/create
- Description: Add a generic OpenAI-compatible model config to the database.
- Request Body (`GenericModelsBaseModel`):
  ```json
  {
    "api_model": "gpt-4",
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "your-api-key"
  }
  ```
- Response 200 OK (`GenericModelCreateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully created the model. Model ID returned in payload.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_base_url": "https://api.openai.com/v1",
      "api_key": "fake",
      "api_model": "gpt-4",
      "id": 20
    }
  }
  ```

#### 5.3.2 Get Generic Model Info
GET /models/generic/{model_id}/about
- Description: Retrieve information about a Generic Model.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`GenericModelAboutResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully retrieved the model config",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_base_url": "https://api.openai.com/v1",
      "api_key": "fake",
      "api_model": "gpt-4",
      "id": 20
    }
  }
  ```

#### 5.3.3 Update Generic Model
PATCH /models/generic/{model_id}/update
- Description: Update a Generic model config in the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Request Body (`GenericModelsPartialBaseModel`):
  ```json
  {
    "api_base_url": "https://api.proxy.com/v1",
    "api_key": "new-api-key"
  }
  ```
- Response 200 OK (`GenericModelUpdateResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully updated the model.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "model": {
      "api_base_url": "https://api.proxy.com/v1",
      "api_key": "fake",
      "api_model": "gpt-4",
      "id": 20
    }
  }
  ```

#### 5.3.4 Delete Generic Model
DELETE /models/generic/{model_id}/delete
- Description: Delete a Generic model config from the database.
- Path Parameters:
  - `model_id` (int, required): The ID of the model.
- Response 200 OK (`GenericModelDeleteResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully deleted the model",
    "timestamp": "<timestamp>",
    "code": "SUCCESS"
  }
  ```

### 5.4 Ragflow Model Sync
Ragflow-configured models don't have their own dedicated `/models/ragflow/*` CRUD routes — they're synced into the same generic model registry as §5.3, tagged `provider_type=ragflow`, then read back via the generic routes (`GET /models/ragflow/list`, `GET /models/ragflow/{model_id}/about`, etc.).

#### 5.4.1 Sync Ragflow Models
POST /models/ragflow/sync
- Description: Reads active models from Ragflow's `tenant_llm` table (scoped to `RAGFLOW_TENANT_ID`) and mirrors them into the generic model registry with `provider_type=ragflow`. Models removed from Ragflow's tenant config are removed here too.
- Response 200 OK (`RagflowSyncResponse`):
  ```json
  {
    "status": 200,
    "message": "Successfully synced Ragflow models.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "stats": {"created": 2, "updated": 1, "removed": 0, "skipped": 0}
  }
  ```

#### 5.4.2 Deduplicate Generic Models
POST /models/dedupe
- Description: Merges duplicate generic models that share the same `provider_type` + `api_model`, keeping the lowest model ID, remapping any `Groups` references to it, and deleting the rest. Requires master key in production.
- Request Body (`ModelDedupeRequest`, all fields optional — omit to dedupe everything):
  ```json
  {
    "provider_type": "ragflow",
    "api_model": "gpt-4o"
  }
  ```
- Response 200 OK (`ModelDedupeResponse`):
  ```json
  {
    "status": 200,
    "message": "Duplicate generic models merged.",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "merged_groups": 1,
    "deleted_models": 2
  }
  ```

---

## 6. Agents

### 6.1 Ragflow Agents
Note: `app/controllers/agents/azure_agents/` contains an older, near-identical set of these same routes but is never imported/registered by `app/controllers/agents/__init__.py` — it's dead code, not a live parallel API. The `ragflow_agents/` versions below are what's actually reachable.

#### 6.1.0 Ensure Dialog
POST /ragflow/chats/{chat_id}/ensure
- Description: Ensure a Ragflow dialog exists for the given chat ID, creating it if needed. Used to initialize the backing dialog before starting a chat.
- Path Parameters:
  - `chat_id` (string, required): The chat ID to ensure a dialog for.
- Request Body (`EnsureDialogRequest`):
  ```json
  {
    "tenant_id": null,
    "llm_id": null
  }
  ```
- Response 200 OK (`EnsureDialogResponse`):
  ```json
  {
    "status": 200,
    "message": "Dialog ensured successfully",
    "timestamp": "<timestamp>",
    "code": "SUCCESS",
    "chat_id": "your-chat-id",
    "created": true
  }
  ```

#### 6.1.1 Chat
POST /models/ragflow/{model_id}/agents/chat
- Description: Chat with a Ragflow model. Uses the server-side `RAGFLOW_API_KEY` and requires a `chat_id`.
- Path Parameters:
  - `model_id` (int or string, required): The ID of the model.
- Request Body (`ChatAgentRequest`):
  ```json
  {
    "chat_id": "your-chat-id",
    "prompt": "hi",
    "history": []
  }
  ```
- Response 200 OK:
  ```json
  {
    "code": "SUCCESS",
    "status": 200,
    "message": "Chat completed successfully",
    "agent_response": {
      "chat_response": {
        "message": {
          "role": "assistant",
          "blocks": [
            {
              "block_type": "text",
              "text": "Hello!"
            }
          ],
          "additional_kwargs": {},
          "metadata": {}
        },
        "raw": {}
      },
      "usage": {
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2
      }
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
- Description: Ask the bot's own Ragflow dialog to suggest up to 3 short follow-up questions, based on the prior question/answer pair. Reuses the same chat-completion path as a real reply (`RagflowChatAgent.chat`) — there is no separate "related prompts" model/API in Ragflow. Requires `chat_id`; returns an empty list (not an error) if `chat_id` is omitted or generation fails.
- Path Parameters:
  - `model_id` (int, required): The ID of the model. Not currently used to select the dialog — `chat_id` is.
- Request Body (`RelatedPromptsRequest`):
  ```json
  {
    "llm_prompt": "What is AI?",
    "llm_reply": "AI is artificial intelligence.",
    "chat_id": "your-chat-id",
    "max_reply_tokens": 500,
    "temperature": 0.1
  }
  ```
- Response 200 OK (`AgentRelatedPromptsResponse`):
  ```json
  {
    "agent_response": {
      "related_prompts": [
        {"label": "How is AI used today?", "prompt": "How is AI used today?", "llm_generated": true}
      ],
      "usage": [
        {
          "completion_tokens": 12,
          "prompt_tokens": 40,
          "total_tokens": 52,
          "usage_label": "RelatedPromptsAgent"
        }
      ]
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

## 7. GraphRAG
Lightweight relationship-graph layer built on top of a group's documents, for graph-expanded search.

### 7.1 Build Group Graph
POST /groups/{group_name}/build_graph
- Description: Queues a graph build for the group.
- Response 200 OK (`GraphBuildResponse`):
  ```json
  {"status": 200, "code": "SUCCESS", "group_name": "...", "job_id": "...", "state": "QUEUED", "source": "none", "progress": 0}
  ```

### 7.2 Get Group Graph Status
GET /groups/{group_name}/graph_status
- Description: Returns current graph build job status plus summary graph metrics.
- Response 200 OK (`GraphStatusResponse`):
  ```json
  {
    "status": 200, "code": "SUCCESS", "group_name": "...",
    "graph": {"status": "NOT_BUILT", "source": "none", "node_count": 0, "edge_count": 0, "top_entities": [], "fallback_reason": null, "error": null, "built_at": null, "updated_at": null},
    "job": null
  }
  ```

### 7.3 Graph Search Group
POST /groups/{group_name}/graph_search
- Description: Runs a group query with graph-based query expansion when a graph is available (extends §1.4 Query a Group with graph traversal params).
- Request Body (`GraphSearchConfig` — extends the base `SearchConfig`):
  ```json
  {
    "query": "test",
    "max_hops": 1,
    "max_expansion_terms": 8,
    "auto_build": false
  }
  ```
- Response 200 OK (`GraphSearchResponse`):
  ```json
  {"status": 200, "code": "SUCCESS", "nodes": [], "assets": [], "search_units": 0, "graph_metadata": {}}
  ```
- Response 404 (`GROUP_NOT_FOUND` / `INDEX_NOT_FOUND`) if the group or its index doesn't exist.

---

## 8. Ragflow Integration
Operational endpoints for keeping Criadex's `GroupRagflowLinks` table (dataset/chat ID mappings) in sync with Ragflow.

### 8.1 Ragflow Webhook Receiver
POST /ragflow/webhook
- Description: Receives Ragflow event webhooks and schedules a background reconcile of KB links. Requires a `Bearer` token matching the server's `RAGFLOW_API_KEY`.
- Headers: `Authorization: Bearer <RAGFLOW_API_KEY>`
- Request Body (`WebhookRequest`):
  ```json
  {"event": "...", "resource": {}}
  ```
- Response 202 (`SUCCESS`) if reconcile was scheduled; 401 if the bearer token doesn't match.

### 8.2 Ragflow Reconcile
POST /ragflow/reconcile
- Description: Synchronously runs a full reconcile between Ragflow and Criadex's group links — upserts missing links, removes stale ones.
- Response 200 OK (`RagflowWebhookResponse`):
  ```json
  {"status": 200, "code": "SUCCESS", "message": "Reconcile completed", "stats": {}}
  ```

### 8.3 Get Group Ragflow Link
GET /ragflow/link/{group_name}
- Description: Returns the stored `GroupRagflowLinks` row for a group. Test/debugging use — requires master API key.
- Path Parameters:
  - `group_name` (string, required): The name of the group.
- Response 200 OK:
  ```json
  {
    "status": 200, "code": "SUCCESS", "message": "Link found",
    "stats": {"ragflow_dataset_id": "...", "ragflow_dataset_name": "...", "ragflow_chat_id": "..."}
  }
  ```
