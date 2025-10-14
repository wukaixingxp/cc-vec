# CC-Vec Examples

This directory contains example scripts demonstrating how to use cc-vec for building RAG (Retrieval Augmented Generation) applications with Common Crawl data.

## Available Examples

### 1. `cc_vec_complete_rag_workflow.py` - Complete RAG Workflow with Llama Stack

**What it demonstrates:**
- Searching Common Crawl data and getting statistics before indexing
- Indexing content into vector stores with custom chunking configuration
- Listing and managing vector stores
- Direct vector store queries using cc-vec
- Advanced RAG using OpenAI Responses API with file_search tool
- Resource cleanup

**Best for:** Learning the full end-to-end workflow with Llama Stack as the LLM backend

### 2. `cc_vec_rag_example.py` - RAG with OpenAI

**What it demonstrates:**
- Indexing GitHub Pages content from Common Crawl
- Querying vector stores using OpenAI's Assistant API with file_search
- Handling citations and source attribution

**Best for:** Quick start with OpenAI's API for production RAG applications

## Prerequisites

### Required Environment Variables

All examples require:
```bash
# AWS credentials for Common Crawl access via Athena
export ATHENA_OUTPUT_BUCKET="s3://your-bucket/athena/"
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export AWS_SESSION_TOKEN="your-session-token"  # Optional, for temporary credentials

# OpenAI API configuration for vector operations
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Custom OpenAI endpoint for llama-stack
export OPENAI_BASE_URL="http://localhost:8321/v1/openai/v1"  # For Llama Stack or other OpenAI-compatible endpoints
export OPENAI_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"  # Or nomic-embed-text, sentence-transformers/all-MiniLM-L6-v2
```

### Additional Setup for Llama Stack Example

The `cc_vec_complete_rag_workflow.py` example uses Llama Stack as the LLM backend:

1. **Install Llama Stack:**
   ```bash
   git clone https://github.com/llama-stack/llama-stack
   cd llama-stack
   pip install -e .
   ```

2. **Choose an API provider:**
   - [Fireworks.ai](https://fireworks.ai) or [Together.ai](https://together.ai)
   ```bash
   export FIREWORKS_API_KEY="your-fireworks-key"
   # OR
   export TOGETHER_API_KEY="your-together-key"
   ```

3. **Start Llama Stack:**
   ```bash
   llama stack build --template starter --image-type venv --run
   ```
   This will start Llama Stack on `http://localhost:8321`

4. **Set the model to use:**
   ```bash
   export MODEL_NAME="together/meta-llama/Llama-3.3-70B-Instruct-Turbo"
   # OR
   export MODEL_NAME="fireworks/accounts/fireworks/models/llama-v3p3-70b-instruct"
   ```

## Running the Examples

### Run the Complete RAG Workflow (with Llama Stack)

```bash
# Make sure Llama Stack is running first
uv run python examples/cc_vec_complete_rag_workflow.py
```

### Run the OpenAI RAG Example

```bash
uv run python examples/cc_vec_rag_example.py
```

## What the Examples Do

Both examples follow a similar RAG workflow:

1. **Search & Filter**: Query Common Crawl metadata to find relevant content
2. **Index**: Download and process content, then index into OpenAI vector stores
3. **Query**: Use the vector store with an LLM to answer questions about the indexed content
4. **Cleanup**: Optionally delete resources after the demo

### Key Features Demonstrated

- **Advanced Filtering**: Filter by URL patterns, hostnames, MIME types, status codes, languages
- **Chunking Configuration**: Control how content is split for embeddings (chunk size, overlap)
- **Custom Embedding Models**: Use different embedding models (OpenAI, Nomic, Sentence Transformers)
- **Vector Store Management**: Create, list, query, and delete vector stores
- **RAG Integration**: Combine vector search with LLMs for context-aware answers
- **Citation Support**: Track which URLs contributed to answers

## Customization

Both examples are designed to be easily customizable:

### Modify the Search Filter

```python
filter_config = FilterConfig(
    url_host_names=["commoncrawl.org"],  # Search specific domains
    crawl_ids=["CC-MAIN-2024-33"],       # Use specific crawl datasets
    status_codes=[200],                   # Only successful responses
    mime_types=["text/html"],            # Only HTML content
    languages=["en"],                     # Only English content
)
```

### Adjust Chunking Strategy

```python
vector_store_config = VectorStoreConfig(
    name="my-vector-store",
    chunk_size=1000,      # Larger chunks for more context
    overlap=200,          # Less overlap for distinct sections
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
)
```

### Change Query Questions

Edit the `questions` list in the examples to ask your own questions about the indexed content.

## Troubleshooting

**Error: "ATHENA_OUTPUT_BUCKET not set"**
- Make sure you have set up an S3 bucket for Athena query results
- Format: `s3://your-bucket-name/path/`

**Error: "OPENAI_API_KEY not set"**
- Set your OpenAI API key in the environment
- For Llama Stack, you can use a dummy key: `export OPENAI_API_KEY="dummy"`

**Error: Connection refused (Llama Stack)**
- Ensure Llama Stack is running on `http://localhost:8321`
- Check with: `curl http://localhost:8321/v1/models`

**Slow indexing**
- Fetching and processing content from Common Crawl takes time
- Start with small limits (5-10 records) for testing
- Increase limits once you've validated the workflow
