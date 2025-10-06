# CC-Vec RAG Agent Usage Guide

The CC-Vec RAG Agent combines the power of cc-vec's Common Crawl indexing with Llama Stack's RAG capabilities to create intelligent question-answering systems from web content.

## Overview

The RAG agent provides:
- **Knowledge Base Creation**: Index Common Crawl data into Llama Stack vector stores
- **Intelligent Querying**: Ask questions and get AI-generated answers based on indexed content
- **Python API**: Programmatic interface for knowledge base operations
- **CLI Interface**: Command-line tools for knowledge base management

## Quick Start

### 1. Prerequisites

**Environment Variables:**
- `LLAMA_STACK_PORT` - Llama Stack server port (default: 8321)
- `ATHENA_OUTPUT_BUCKET` - S3 bucket for Athena results (required)
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS credentials (required)

**Start Llama Stack Server:**
```bash
# Install and start Llama Stack (see https://llama-stack.readthedocs.io/)
llama stack build --distro starter --image-type venv --run
```

### 2. Create Knowledge Base from Common Crawl

```bash
# Create a knowledge base from GitHub Pages sites
uv run cc-vec rag-create "%.github.io" github-pages --limit 50

# Create from academic sites
uv run cc-vec rag-create "%.edu" academic-sites --limit 100

# Auto-generate name if not provided
uv run cc-vec rag-create "%.arxiv.org" --limit 75
```

### 3. Query Knowledge Base

```bash
# Query by vector store ID
uv run cc-vec rag-query vs_abc123 "What is machine learning?"

# Save response to file
uv run cc-vec rag-query vs_abc123 "Explain deep learning" --save response.txt
```


## Python API

### Basic Usage

```python
from cc_vec import create_rag_agent

# Create RAG agent
rag_agent = create_rag_agent()

# Create knowledge base from Common Crawl
result = rag_agent.create_knowledge_base_from_common_crawl(
    url_pattern="%.github.io",
    vector_store_name="github-pages-kb",
    limit=100
)

print(f"Created: {result['vector_store_name']} ({result['vector_store_id']})")

# Query the knowledge base
response = rag_agent.query_knowledge_base(
    result['vector_store_id'],
    "What are the advantages of using GitHub Pages?"
)

print(f"AI Response: {response['response']}")
```

### Advanced Configuration

```python
from cc_vec.rag_agent import CCVecRAGAgent

# Custom Llama Stack configuration
rag_agent = CCVecRAGAgent(
    llama_stack_url="http://localhost:8321",
    model="meta-llama/Llama-3.3-70B-Instruct"
)

# Advanced knowledge base creation
result = rag_agent.create_knowledge_base_from_common_crawl(
    url_pattern="%.arxiv.org",
    vector_store_name="arxiv-papers",
    limit=200,
    crawl="CC-MAIN-2024-33",
    status_codes=[200],
    mime_types=["text/html", "application/pdf"],
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    embedding_dimension=384,
    provider_id="faiss"
)
```


## Management Operations

### List Knowledge Bases

```bash
# CLI
uv run cc-vec rag-list

# Python
knowledge_bases = rag_agent.list_knowledge_bases()
for kb in knowledge_bases:
    print(f"{kb['name']} ({kb['id']}): {kb['file_count']} files")
```

### Delete Knowledge Base

```bash
# CLI
uv run cc-vec rag-delete vs_abc123

# Python
rag_agent.delete_knowledge_base("vs_abc123")
```

### Query Multiple Knowledge Bases

```python
# Query across multiple knowledge bases
response = rag_agent.query_multiple_knowledge_bases(
    vector_store_ids=["vs_abc123", "vs_def456", "vs_ghi789"],
    query="Compare machine learning approaches"
)
```

## Configuration Options

### Knowledge Base Creation

- `url_pattern`: Common Crawl URL pattern (e.g., `"%.github.io"`)
- `vector_store_name`: Name for the knowledge base
- `limit`: Maximum pages to index (default: 50)
- `crawl`: Common Crawl dataset (default: "CC-MAIN-2024-33")
- `status_codes`: HTTP codes to filter (default: [200])
- `mime_types`: MIME types to filter (default: ["text/html"])
- `embedding_model`: Embedding model (default: "sentence-transformers/all-MiniLM-L6-v2")
- `embedding_dimension`: Embedding dimensions (default: 384)
- `provider_id`: Vector DB backend (default: "faiss")

### Query Configuration

- `model`: LLM model for generation (default: "meta-llama/Llama-3.3-70B-Instruct")
- `llama_stack_url`: Llama Stack server URL (default: from LLAMA_STACK_PORT)

## Architecture

The RAG agent follows this workflow:

1. **Index Phase**:
   ```
   Common Crawl → cc-vec fetch → Content Processing → Llama Stack Files API → Vector Store
   ```

2. **Query Phase**:
   ```
   User Query → Llama Stack Responses API → file_search tool → Vector Store → AI Response
   ```

### Components

- **CCVecRAGAgent**: Main RAG agent class
- **cc-vec integration**: Common Crawl data fetching and processing
- **Llama Stack integration**: Vector storage and AI generation

## Examples

### rag_demo
use the included demo to see all features:
`python examples/rag_demo.py`

### Research Knowledge Base

```python
# Create research knowledge base from arXiv
rag_agent = create_rag_agent()

kb = rag_agent.create_knowledge_base_from_common_crawl(
    url_pattern="%.arxiv.org",
    vector_store_name="ml-research",
    limit=500,
    mime_types=["text/html", "application/pdf"]
)

# Query research topics
response = rag_agent.query_knowledge_base(
    kb['vector_store_id'],
    "What are the latest developments in transformer architectures?"
)
```

### Documentation Knowledge Base

```python
# Index documentation sites
kb = rag_agent.create_knowledge_base_from_common_crawl(
    url_pattern="%.readthedocs.io",
    vector_store_name="docs-kb",
    limit=1000
)

# Query documentation
response = rag_agent.query_knowledge_base(
    kb['vector_store_id'],
    "How do I set up authentication in Django?"
)
```

### Multi-Domain Knowledge Base

```python
# Create separate knowledge bases for different domains
domains = [
    ("%.github.io", "github-pages"),
    ("%.medium.com", "medium-articles"),
    ("%.stackoverflow.com", "stackoverflow")
]

kb_ids = []
for pattern, name in domains:
    kb = rag_agent.create_knowledge_base_from_common_crawl(
        url_pattern=pattern,
        vector_store_name=name,
        limit=200
    )
    kb_ids.append(kb['vector_store_id'])

# Query across all domains
response = rag_agent.query_multiple_knowledge_bases(
    kb_ids,
    "What are best practices for web development?"
)
```

## Error Handling

```python
try:
    kb = rag_agent.create_knowledge_base_from_common_crawl(
        url_pattern="%.example.com",
        vector_store_name="test-kb",
        limit=10
    )
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Creation failed: {e}")

try:
    response = rag_agent.query_knowledge_base(kb_id, "test query")
except Exception as e:
    print(f"Query failed: {e}")
```

## Performance Tips

1. **Start Small**: Use `limit=10-50` for testing, scale up as needed
2. **Filter Content**: Use `status_codes=[200]` and specific `mime_types`
3. **Choose Crawl**: Recent crawls have more current content
4. **Embedding Model**: Balance quality vs speed based on your needs
5. **Multiple KBs**: Create domain-specific knowledge bases for better relevance

## Troubleshooting

### Common Issues

**Llama Stack Connection Error:**
```
Error: Failed to connect to Llama Stack server
```
- Ensure Llama Stack server is running
- Check `LLAMA_STACK_PORT` environment variable
- Verify server URL and port

**No Content Found:**
```
Error: No content found for pattern: %.example.com
```
- Check URL pattern syntax (use `%` not `*`)
- Try broader patterns or different crawl datasets
- Verify Common Crawl contains the target sites

**AWS/Athena Errors:**
```
Error: Missing required environment variable: ATHENA_OUTPUT_BUCKET
```
- Set all required AWS environment variables
- Ensure S3 bucket exists and is accessible
- Check AWS credentials and permissions

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enables detailed logging for troubleshooting
rag_agent = create_rag_agent()
```

## Demo Script

Run the included demo to see all features:

```bash
cd examples
python rag_demo.py
```

The demo provides:
- Programmatic API examples
- Interactive mode demonstration
- Full workflow (create → query → cleanup)
- Error handling examples

## Integration Examples

### Jupyter Notebook

```python
# Install in Jupyter
# !pip install cc-vec

from cc_vec import create_rag_agent
import os

# Set required environment variables
os.environ['ATHENA_OUTPUT_BUCKET'] = 's3://your-bucket/athena-results/'

# Create and use RAG agent
rag_agent = create_rag_agent()
# ... rest of code
```

### Web Application

```python
from flask import Flask, request, jsonify
from cc_vec import create_rag_agent

app = Flask(__name__)
rag_agent = create_rag_agent()

@app.route('/query', methods=['POST'])
def query_knowledge_base():
    data = request.json
    response = rag_agent.query_knowledge_base(
        data['vector_store_id'],
        data['query']
    )
    return jsonify({'response': str(response['response'])})
```

This guide provides comprehensive coverage of the CC-Vec RAG Agent capabilities. For more details, see the source code and examples in the repository.
