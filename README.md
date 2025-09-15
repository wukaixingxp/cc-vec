# CCVec - Common Crawl Vectorizer

Search, analyze, and vectorize Common Crawl data for RAG applications with 3 interfaces: Python library, CLI, and MCP server.

## Quick Start

**Environment variables:**

- **`ATHENA_OUTPUT_BUCKET`** - Required S3 bucket for Athena query results (needed for reliable queries to Common Crawl metadata)
- **`AWS_SECRET_KEY`** - Required for Athena/S3 access (needed to run Athena queries)
- **`AWS_ACCESS_KEY`** - Required for Athena/S3 access (needed to run Athena queries)
- **`OPENAI_API_KEY`** - Required for vector operations (index, query, list)
- `OPENAI_BASE_URL` - Optional custom OpenAI endpoint
- `AWS_DEFAULT_REGION` - AWS region (defaults to us-west-2)
- `LOG_LEVEL` - Logging level (defaults to INFO)

**Note:** Uses SQL wildcards (`%`) not glob patterns (`*`) for URL matching.

## 1. 📦 Python Library

```python
from cc_vec import search, stats, fetch, index, list_vector_stores, query_vector_store

# Search and stats (no OpenAI key needed)
results = search("%.github.io%", limit=10)
print(f"Found {len(results)} URLs")
for result in results[:3]:
    print(f"  {result.url} (Status: {result.status})")

stats_response = stats("%.github.io%")
print(f"Estimated records: {stats_response.estimated_records:,}")
print(f"Estimated size: {stats_response.estimated_size_mb:.2f} MB")

# Fetch and process content (returns clean text)
content_results = fetch("%.example.com%", limit=2)
print(f"Processed {len(content_results)} content records")
for record, processed in content_results:
    if processed:
        print(f"  {record.url}: {processed['word_count']} words")
        print(f"    Title: {processed.get('title', 'N/A')}")

# Index data in a vector store
result = index("%.github.io%", "ml-research", limit=50, chunk_size=800, overlap=400)
print(f"Created vector store: {result['vector_store_name']}")
print(f"Vector Store ID: {result['vector_store_id']}")
print(f"Processed {result['total_pages']} pages")

# List all vector stores
stores = list_vector_stores()
print(f"Available stores: {len(stores)}")
for store in stores[:3]:
    print(f"  {store['name']} (ID: {store['id']}, Status: {store['status']})")

# Query vector store for RAG
query_results = query_vector_store("ml-research", "What is machine learning?", limit=5)
print(f"Query found {len(query_results.get('results', []))} relevant results")
for i, result in enumerate(query_results.get("results", []), 1):
    print(f"  {i}. Score: {result.get('score', 0):.3f}")
    print(f"     Content: {result.get('content', '')[:100]}...")
    print(f"     File: {result.get('file_id', 'N/A')}")

# Complete RAG workflow in 2 lines:
# 1. Index content: OpenAI handles chunking with specified token limits
index_result = index(
    "%.stanford.edu%", "research-papers", limit=100, chunk_size=800, overlap=400
)
# 2. Query for relevant content: ready for LLM context
answers = query_vector_store(index_result["vector_store_id"], "explain neural networks")
```

## 2. ⌨️ Command Line

```bash
# Search Common Crawl index
uv run cc-vec search "%.github.io%" --limit 10

# Get statistics
uv run cc-vec stats "%.edu%"

# Fetch and process content (returns clean text)
uv run cc-vec fetch "%.example.com%" --limit 5

# Advanced filtering
uv run cc-vec fetch "%.github.io%" --status-codes "200,201" --mime-types "text/html" --limit 10

# Vector operations (require OPENAI_API_KEY)
# Create vector store with processed content (OpenAI handles chunking with token limits)
uv run cc-vec index "%.github.io%" "ml-research" --limit 50 --chunk-size 800 --overlap 400

# Vector store name is optional - will auto-generate if not provided
uv run cc-vec index "%.github.io%" --limit 50

# List all vector stores
uv run cc-vec list --output json

# Query vector store by ID for RAG
uv run cc-vec query "What is machine learning?" --vector-store-id "vs-123abc" --limit 5

# Query vector store by name
uv run cc-vec query "Explain deep learning" --vector-store-name "ml-research" --limit 3

# Complete RAG pipeline in 2 commands:
uv run cc-vec index "%.stanford.edu%" "research-db" --limit 100 --chunk-size 800 --overlap 400  # Index with token chunking
# Or auto-generate name: uv run cc-vec index "%.stanford.edu%" --limit 100
uv run cc-vec query "neural networks" --vector-store-name "research-db"  # Query for RAG
```

## 3. 🔌 MCP Server (Claude Desktop)

**Setup:**
1. Copy and edit the config: `cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Update the directory path and API key in the config file
3. Restart Claude Desktop

The config uses stdio mode (required by Claude Desktop):
```json
{
  "mcpServers": {
    "cc-vec": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/rsm/dev/ccf", "cc-vec", "mcp-serve", "--mode", "stdio"],
      "env": {
        "ATHENA_OUTPUT_BUCKET": "s3://llama-stack-dev-test0/athena-results/",
        "OPENAI_API_KEY": "your-openai-api-key-here"
      }
    }
  }
}
```

**Available MCP tools:**

```
# Search and analysis (no OpenAI key needed)
cc_search - Search Common Crawl for URLs matching patterns
cc_stats - Get statistics and cost estimates for patterns
cc_fetch - Download actual content from matched URLs

# Vector operations (require OPENAI_API_KEY)
cc_index - Create and populate vector stores from Common Crawl content
cc_list_vector_stores - List all available OpenAI vector stores
cc_query - Query vector stores for relevant content
```

**Example usage in Claude Desktop:**
- "Use cc_search to find GitHub Pages sites: pattern=%.github.io%, limit=10"
- "Use cc_stats to analyze education sites: pattern=%.edu%"
- "Use cc_index to create vector store: name=research, pattern=%.arxiv.org%, limit=100"
- "Use cc_list_vector_stores to show available stores"
- "Use cc_query to search: vector_store_id=vs-123, query=machine learning"

## Library API

```python
from cc_vec import (
    search,
    stats,
    fetch,
    index,
    list_vector_stores,
    query_vector_store,
    FilterConfig,
    StatsResponse,
    SearchResponse,
)

# Simplified API - functions handle client initialization automatically
results = search("%.github.io%", limit=10)  # Returns List[CrawlRecord]
stats_response = stats("%.github.io%")  # Returns StatsResponse
content = fetch(
    "%.example.com%", limit=5
)  # Returns List[Tuple[CrawlRecord, processed_content]]

# Vector operations (requires OPENAI_API_KEY)
stores = list_vector_stores()  # Returns List[Dict]
result = index(
    "%.github.io%", "my-store", limit=50, chunk_size=800, overlap=400
)  # Returns Dict
query_results = query_vector_store("vs-123", "query text", limit=5)  # Returns Dict
```

## License

MIT
