# Criadex API User Guide

This guide shows how to interact with the Criadex HTTP API using `curl`. For each endpoint, you’ll see required headers, request examples, and sample responses.

## Prerequisites
- You must have a valid API key. Set it in `x-api-key` header.
- `HOST` and `PORT` point to your running service (default `http://localhost:25574`).

Example environment variables:
```bash
export HOST=http://localhost
export PORT=25574
export API_KEY=your_api_key_here
```

## Common Headers
```
Content-Type: application/json
x-api-key: ${API_KEY}
```

---

## 1. Group Management

### 1.1 Create a Group
POST /groups/{group_name}/create

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/create" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "type": "DOCUMENT",
    "llm_model_id": 1,
    "embedding_model_id": 2,
    "rerank_model_id": 4
  }'
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/groups/test-group-gemini/about" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/groups/test-group-gemini/delete" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "query": "test"
  }'
```

Response (200 OK):
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

### 2.1 Create API Key
POST /auth/{api_key}/create

Request:
```bash
curl -X POST "${HOST}:${PORT}/auth/new-api-key/create" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "master": false
  }'
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully completed the request!",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "api_key": "new-api-key",
  "master": false
}
```

### 2.2 Validate API Key
GET /auth/{api_key}/check

Request:
```bash
curl "${HOST}:${PORT}/auth/new-api-key/check" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully completed the request!",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "api_key": "new-api-key",
  "authorized": true,
  "master": false
}
```

### 2.3 Delete API Key
DELETE /auth/{api_key}/delete

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/auth/new-api-key/delete" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully completed the request!",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "api_key": "new-api-key"
}
```

### 2.4 Validate API Key (Keys Endpoint)
GET /auth/keys/{api_key}

Request:
```bash
curl "${HOST}:${PORT}/auth/keys/new-api-key" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully completed the request!",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "api_key": "new-api-key",
  "authorized": true,
  "master": false
}
```

### 2.5 Reset API Key
PATCH /auth/{api_key}/reset

Request:
```bash
curl -X PATCH "${HOST}:${PORT}/auth/new-api-key/reset?new_key=new-api-key-2" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully completed the request!",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "new_key": "new-api-key-2"
}
```

---

## 3. Group Authorization

### 3.1 Add Group Authorization
POST /group_auth/{group_name}/create

Request:
```bash
curl -X POST "${HOST}:${PORT}/group_auth/test-group-gemini/create?api_key=new-api-key" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/group_auth/test-group-gemini/check?api_key=new-api-key" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/group_auth/test-group-gemini/delete?api_key=new-api-key" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/group_auth/list?api_key=new-api-key" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

### 4.1 Upload Content
POST /groups/{group_name}/content/upload

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/content/upload" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
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
  }'
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/groups/test-group-gemini/content/list" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X PATCH "${HOST}:${PORT}/groups/test-group-gemini/content/update" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
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
  }'
```

Response (200 OK):
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

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/groups/test-group-gemini/content/delete?document_name=my-test-document.json" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/content/search" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "query": "test"
  }'
```

Response (200 OK):
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

### 4.6 Upload Raw File (Native Ragflow Parse)
POST /groups/{group_name}/content/upload/file

Upload a raw file (PDF, DOCX, HTML, TXT, …) straight to Ragflow for native parsing — replaces CriaParse. Unlike §4.1, which takes already-parsed nodes, this takes raw bytes as multipart form data.

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/content/upload/file" \
  -H "x-api-key: ${API_KEY}" \
  -F "file=@syllabus.pdf" \
  -F "strategy=GENERIC"
```

`strategy` is optional (default `GENERIC`) — one of `GENERIC`, `ALSYLLABUS`, `ALSYLLABUSFR`, `PARAGRAPH` (the latter three pre-process the file to plain text before handing it to Ragflow). `filename_override` is also optional.

Response (200 OK):
```json
{
  "status": 200,
  "message": "File queued for native Ragflow parsing.",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "document_name": "syllabus.pdf"
}
```

---

## 5. Model Management

### 5.1 Azure Models

#### 5.1.1 Create Azure Model
POST /models/azure/create

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/azure/create" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_model": "text-embedding-ada-002",
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "your-controllers-key",
    "api_deployment": "your-deployment-name"
  }'
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/models/azure/13/about" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X PATCH "${HOST}:${PORT}/models/azure/13/update" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_key": "new-key"
  }'
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully updated the model.",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "model": {
    "api_resource": "your-resource",
    "api_version": "2023-05-15",
    "api_key": "new-key",
    "api_deployment": "your-deployment-name",
    "api_model": "text-embedding-ada-002",
    "id": 13
  }
}
```

#### 5.1.4 Delete Azure Model
DELETE /models/azure/{model_id}/delete

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/models/azure/13/delete" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/cohere/create" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_model": "rerank-multilingual-v2.0",
    "api_key": "your-cohere-key"
  }'
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully created the model. Model ID returned in payload.",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "model": {
    "api_key": "your-cohere-key",
    "api_model": "rerank-multilingual-v2.0",
    "id": 5
  }
}
```

#### 5.2.2 Get Cohere Model Info
GET /models/cohere/{model_id}/about

Request:
```bash
curl "${HOST}:${PORT}/models/cohere/5/about" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully retrieved the model config",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "model": {
    "api_key": "your-cohere-key",
    "api_model": "rerank-multilingual-v2.0",
    "id": 5
  }
}
```

#### 5.2.3 Update Cohere Model
PATCH /models/cohere/{model_id}/update

Request:
```bash
curl -X PATCH "${HOST}:${PORT}/models/cohere/5/update" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_key": "new-cohere-key"
  }'
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully updated the model.",
  "timestamp": "<timestamp>",
  "code": "SUCCESS",
  "model": {
    "api_key": "new-cohere-key",
    "api_model": "rerank-multilingual-v2.0",
    "id": 5
  }
}
```

#### 5.2.4 Delete Cohere Model
DELETE /models/cohere/{model_id}/delete

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/models/cohere/5/delete" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/5/rerank" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
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
  }'
```

Response (200 OK):
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

### 5.3 Generic Models (OpenAI-Compatible)

#### 5.3.1 Create Generic Model
POST /models/generic/create

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/generic/create" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_model": "gpt-4",
    "api_base_url": "https://api.openai.com/v1",
    "api_key": "your-api-key"
  }'
```

Response (200 OK):
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

Request:
```bash
curl "${HOST}:${PORT}/models/generic/20/about" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Request:
```bash
curl -X PATCH "${HOST}:${PORT}/models/generic/20/update" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "api_base_url": "https://api.proxy.com/v1"
  }'
```

Response (200 OK):
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

Request:
```bash
curl -X DELETE "${HOST}:${PORT}/models/generic/20/delete" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200,
  "message": "Successfully deleted the model",
  "timestamp": "<timestamp>",
  "code": "SUCCESS"
}
```

### 5.4 Ragflow Model Sync

Ragflow-configured models don't have their own `/models/ragflow/*` CRUD routes — they're synced into the same generic model registry as §5.3 above, tagged `provider_type=ragflow`, then read back with the generic routes (e.g. `GET /models/ragflow/list`).

#### 5.4.1 Sync Ragflow Models
POST /models/ragflow/sync

Reads active models from Ragflow's tenant config (scoped to `RAGFLOW_TENANT_ID`) and mirrors them into the generic model registry.

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/ragflow/sync" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
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

Merges duplicate generic models sharing the same `provider_type` + `api_model`, keeping the lowest ID and remapping any group references. Requires master key in production.

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/dedupe" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "provider_type": "ragflow"
  }'
```

Response (200 OK):
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

`app/controllers/agents/azure_agents/` has an older, near-identical copy of these routes, but it's never imported into the app — it's dead code, not a reachable parallel API. Use the routes below.

#### 6.1.0 Ensure Dialog
POST /ragflow/chats/{chat_id}/ensure

Initialize the backing Ragflow dialog for a chat ID before starting a chat, creating it if it doesn't exist yet.

Request:
```bash
curl -X POST "${HOST}:${PORT}/ragflow/chats/your-chat-id/ensure" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{}'
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/ragflow/1/agents/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "chat_id": "your-chat-id",
    "prompt": "hi",
    "history": []
  }'
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/ragflow/1/agents/intents" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "text": "weather"
  }'
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/ragflow/1/agents/language" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "text": "hello"
  }'
```

Response (200 OK):
```json
{
  "language": "ST",
  "confidence": 0.17332524358443202
}
```

#### 6.1.4 Related Prompts
POST /models/{model_id}/related_prompts

Asks the bot's own Ragflow dialog to suggest up to 3 short follow-up questions, given the prior question/answer pair. Reuses the same chat-completion path as a real reply — there's no separate "related prompts" model in Ragflow. Needs a `chat_id`; returns an empty list (not an error) if `chat_id` is missing or generation fails.

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/1/related_prompts" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "llm_prompt": "What is AI?",
    "llm_reply": "AI is artificial intelligence.",
    "chat_id": "your-chat-id"
  }'
```

Response (200 OK):
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

Request:
```bash
curl -X POST "${HOST}:${PORT}/models/ragflow/1/agents/transform" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "text": "change"
  }'
```

Response (200 OK):
```json
{
  "transformed_text": "CHANGE"
}
```

---

## 7. GraphRAG

A lightweight relationship graph built on top of a group's documents, used for graph-expanded search.

### 7.1 Build Group Graph
POST /groups/{group_name}/build_graph

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/build_graph" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{"status": 200, "code": "SUCCESS", "group_name": "test-group-gemini", "job_id": "...", "state": "QUEUED", "source": "none", "progress": 0}
```

### 7.2 Get Group Graph Status
GET /groups/{group_name}/graph_status

Request:
```bash
curl "${HOST}:${PORT}/groups/test-group-gemini/graph_status" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200, "code": "SUCCESS", "group_name": "test-group-gemini",
  "graph": {"status": "NOT_BUILT", "source": "none", "node_count": 0, "edge_count": 0, "top_entities": []},
  "job": null
}
```

### 7.3 Graph Search Group
POST /groups/{group_name}/graph_search

Same as §1.4 Query a Group, but with graph-based query expansion when a graph is available.

Request:
```bash
curl -X POST "${HOST}:${PORT}/groups/test-group-gemini/graph_search" \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{
    "query": "test",
    "max_hops": 1,
    "max_expansion_terms": 8,
    "auto_build": false
  }'
```

Response (200 OK):
```json
{"status": 200, "code": "SUCCESS", "nodes": [], "assets": [], "search_units": 0, "graph_metadata": {}}
```

---

## 8. Ragflow Integration

Operational endpoints that keep Criadex's stored dataset/chat ID links in sync with Ragflow.

### 8.1 Ragflow Webhook Receiver
POST /ragflow/webhook

Receives Ragflow event webhooks and schedules a background reconcile. Requires a `Bearer` token matching the server's `RAGFLOW_API_KEY` — this is meant to be called by Ragflow, not end users.

Request:
```bash
curl -X POST "${HOST}:${PORT}/ragflow/webhook" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
  -d '{"event": "document.parsed", "resource": {}}'
```

Response (202 Accepted): reconcile scheduled in the background.

### 8.2 Ragflow Reconcile
POST /ragflow/reconcile

Synchronously runs a full reconcile between Ragflow and Criadex's group links.

Request:
```bash
curl -X POST "${HOST}:${PORT}/ragflow/reconcile" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{"status": 200, "code": "SUCCESS", "message": "Reconcile completed", "stats": {}}
```

### 8.3 Get Group Ragflow Link
GET /ragflow/link/{group_name}

Returns the stored dataset/chat link for a group. Debugging use — requires master API key.

Request:
```bash
curl "${HOST}:${PORT}/ragflow/link/test-group-gemini" \
  -H "x-api-key: ${API_KEY}"
```

Response (200 OK):
```json
{
  "status": 200, "code": "SUCCESS", "message": "Link found",
  "stats": {"ragflow_dataset_id": "...", "ragflow_dataset_name": "...", "ragflow_chat_id": "..."}
}
```
