# Using Custom Embedding Models

cc-vec now supports using custom embedding models hosted as OpenAI-compatible APIs, allowing you to use models like sentence-transformers instead of OpenAI's default embedding models.

## Configuration

### Environment Variables

Set the following environment variables to use your custom embedding model:

```bash
# Required: Your API key
export OPENAI_API_KEY="your-api-key"

# Required: Point to your OpenAI-compatible embedding service
export OPENAI_BASE_URL="http://localhost:8000/v1"

# Optional: Specify the model name (e.g., 'sentence-transformers')
export OPENAI_EMBEDDING_MODEL="sentence-transformers"
```

### Configuration File

Alternatively, create a `.env` file in your project root:

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_EMBEDDING_MODEL=sentence-transformers
```

## Hosting Options

### Option 1: Local Embedding Service

You can host your own embedding service using frameworks like:

- **LiteLLM**: Provides OpenAI-compatible API for various embedding models
- **vLLM**: High-throughput inference for embedding models
- **FastAPI**: Custom service wrapping sentence-transformers

Example with sentence-transformers using FastAPI:

```python
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import numpy as np

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.post("/v1/embeddings")
async def create_embedding(request: dict):
    texts = request.get("input", [])
    if isinstance(texts, str):
        texts = [texts]

    embeddings = model.encode(texts)

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": i
            }
            for i, embedding in enumerate(embeddings)
        ],
        "model": request.get("model", "sentence-transformers"),
        "usage": {
            "prompt_tokens": sum(len(t.split()) for t in texts),
            "total_tokens": sum(len(t.split()) for t in texts)
        }
    }

# Run with: uvicorn server:app --host 0.0.0.0 --port 8000
```

### Option 2: Hosted Services

Some services provide OpenAI-compatible APIs with custom models:
- **Anyscale Endpoints**
- **Together AI**
- **Replicate**

## Usage

Once configured, use cc-vec normally. The custom embedding model will be used automatically:

### CLI Usage

```bash
# Index content - will use your custom embedding model
cc-vec index \
  --url-pattern "example.com/*" \
  --vector-store-name "my-custom-embeddings" \
  --limit 100

# Query the vector store
cc-vec query \
  --vector-store-id "vs_xxx" \
  --query "your search query"
```

### Python API Usage

```python
from cc_vec.lib.index import VectorStoreLoader
from cc_vec.types.config import load_config

# Configuration is loaded from environment variables
config = load_config()

# Create loader - will automatically use custom base_url and embedding_model
loader = VectorStoreLoader()

# Or explicitly specify:
loader = VectorStoreLoader(
    api_key="your-key",
    base_url="http://localhost:8000/v1",
    embedding_model="sentence-transformers"
)

# Create vector store
vector_store_id = loader.create_vector_store("my-store")
```

## Verification

To verify your custom embedding model is being used, check the logs:

```
INFO - Using custom OpenAI base URL: http://localhost:8000/v1
INFO - Using custom embedding model: sentence-transformers
INFO - Creating vector store: my-store with max_chunk_size_tokens=800, chunk_overlap_tokens=400
```

## Troubleshooting

### Connection Issues

If you can't connect to your embedding service:

1. Verify the service is running: `curl http://localhost:8000/v1/models`
2. Check the base URL includes `/v1`: `http://localhost:8000/v1`
3. Ensure your API key is valid

### Model Not Found

If you get "model not found" errors:

1. Verify your service supports the model name
2. Check the model name matches exactly
3. Some services require the model parameter in requests

### Performance Issues

If embeddings are slow:

1. Consider batching (OpenAI API supports batching)
2. Use a smaller embedding model
3. Deploy your service on GPU-enabled hardware
4. Implement caching for frequently embedded texts

## Example: Complete Setup with sentence-transformers

```bash
# 1. Install dependencies
pip install fastapi uvicorn sentence-transformers

# 2. Create embedding service (save as embedding_service.py)
cat > embedding_service.py << 'EOF'
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from typing import List, Union

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "sentence-transformers"

@app.post("/v1/embeddings")
async def create_embedding(request: EmbeddingRequest):
    texts = request.input
    if isinstance(texts, str):
        texts = [texts]

    embeddings = model.encode(texts)

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "embedding": embedding.tolist(),
                "index": i
            }
            for i, embedding in enumerate(embeddings)
        ],
        "model": request.model,
        "usage": {
            "prompt_tokens": sum(len(t.split()) for t in texts),
            "total_tokens": sum(len(t.split()) for t in texts)
        }
    }

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "sentence-transformers",
                "object": "model",
                "owned_by": "local"
            }
        ]
    }
EOF

# 3. Start the service
uvicorn embedding_service:app --host 0.0.0.0 --port 8000 &

# 4. Configure cc-vec
export OPENAI_API_KEY="dummy-key"
export OPENAI_BASE_URL="http://localhost:8000/v1"
export OPENAI_EMBEDDING_MODEL="sentence-transformers"

# 5. Use cc-vec normally
cc-vec index --url-pattern "example.com/*" --vector-store-name "test" --limit 10
```

## Notes

- The custom base URL and embedding model are stored in the configuration and used throughout cc-vec
- All vector store operations will use your custom embedding service
- The vector store still uses OpenAI's storage infrastructure, only embeddings are custom
- Ensure your embedding dimensions match (most sentence-transformers models use 384 or 768 dimensions)
