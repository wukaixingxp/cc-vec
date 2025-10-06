# Retrieval Augmented Generation (RAG)

RAG enables your applications to reference and recall information from previous interactions or external documents.

Llama Stack now uses a modern, OpenAI-compatible API pattern for RAG:
1. **Files API**: Upload documents using `client.files.create()`
2. **Vector Stores API**: Create and manage vector stores with `client.vector_stores.create()`
3. **Responses API**: Query documents using `client.responses.create()` with the `file_search` tool

This new approach provides better compatibility with OpenAI's ecosystem and is the recommended way to implement RAG in Llama Stack.

<img src="docs/static/img/rag_llama_stack.png" alt="RAG System" width="50%" />

## Prerequisites

For this guide, we will use [Ollama](https://ollama.com/) as the inference provider.
Ollama is an LLM runtime that allows you to run Llama models locally. It's a great choice for development and testing, but you can also use any other inference provider that supports the OpenAI API.

Before you begin, make sure you have the following:
1. **Ollama**: Follow the [installation guide](https://ollama.com/docs/ollama/getting-started/install
) to set up Ollama on your machine.
2. **Llama Stack**: Follow the [installation guide](/docs/installation) to set up Llama Stack on your
machine.
3. **Documents**: Prepare a set of documents that you want to search. These can be plain text, PDFs, or other file types.
4. **environment variable**: Set the `LLAMA_STACK_PORT` environment variable to the port where Llama Stack is running. For example, if you are using the default port of 8321, set `export LLAMA_STACK_PORT=8321`. Also set 'OLLAMA_URL' environment variable to be 'http://localhost:11434'

## Step 0: Initialize Client

After lauched Llama Stack server by `llama stack build --distro starter --image-type venv --run`, initialize the client with the base URL of your Llama Stack instance.

```python
import os
from llama_stack_client import LlamaStackClient
from io import BytesIO

client = LlamaStackClient(base_url=f"http://localhost:{os.environ['LLAMA_STACK_PORT']}")
```

## Step 1: Upload Documents Using Files API

The first step is to upload your documents using the Files API. Documents can be plain text, PDFs, or other file types.

<Tabs>
<TabItem value="text" label="Upload Text Documents">

```python
# Example documents with metadata
docs = [
    ("Acme ships globally in 3-5 business days.", {"title": "Shipping Policy"}),
    ("Returns are accepted within 30 days of purchase.", {"title": "Returns Policy"}),
    ("Support is available 24/7 via chat and email.", {"title": "Support"}),
]

# Upload each document and collect file IDs
file_ids = []
for content, metadata in docs:
    with BytesIO(content.encode()) as file_buffer:
        # Set a descriptive filename
        file_buffer.name = f"{metadata['title'].replace(' ', '_').lower()}.txt"

        # Upload the file
        create_file_response = client.files.create(
            file=file_buffer,
            purpose="assistants"
        )
        print(f"Uploaded: {create_file_response.id}")
        file_ids.append(create_file_response.id)
```

</TabItem>
<TabItem value="files" label="Upload Files from Disk">

```python
# Upload a file from your local filesystem
with open("policy_document.pdf", "rb") as f:
    file_response = client.files.create(
        file=f,
        purpose="assistants"
    )
    file_ids.append(file_response.id)
```

</TabItem>
<TabItem value="batch" label="Upload Multiple Documents">

```python
# Batch upload multiple documents
document_paths = [
    "docs/shipping.txt",
    "docs/returns.txt",
    "docs/support.txt"
]

file_ids = []
for path in document_paths:
    with open(path, "rb") as f:
        response = client.files.create(file=f, purpose="assistants")
        file_ids.append(response.id)
        print(f"Uploaded {path}: {response.id}")
```

</TabItem>
</Tabs>

## Step 2: Create a Vector Store

Once you have uploaded your documents, create a vector store that will index them for semantic search.

```python
# Create vector store with uploaded files
vector_store = client.vector_stores.create(
    name="acme_docs",
    file_ids=file_ids,
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    embedding_dimension=384,
    provider_id="faiss"
)

print(f"Created vector store: {vector_store.name} (ID: {vector_store.id})")
```

### Configuration Options

- **name**: A descriptive name for your vector store
- **file_ids**: List of file IDs to include in the vector store
- **embedding_model**: The model to use for generating embeddings (e.g., "sentence-transformers/all-MiniLM-L6-v2", "all-MiniLM-L6-v2")
- **embedding_dimension**: Dimension of the embedding vectors (e.g., 384 for MiniLM, 768 for BERT)
- **provider_id**: The vector database backend (e.g., "faiss", "chroma")

## Step 3: Query the Vector Store

Use the Responses API with the `file_search` tool to query your documents.

<Tabs>
<TabItem value="single" label="Single Vector Store">

```python
query = "How long does shipping take?"

# Search the vector store
file_search_response = client.responses.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    input=query,
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": [vector_store.id],
        },
    ],
)

print(file_search_response)
```

</TabItem>
<TabItem value="multiple" label="Multiple Vector Stores">

You can search across multiple vector stores simultaneously:

```python
file_search_response = client.responses.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    input="What are your policies?",
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": [
                vector_store_1.id,
                vector_store_2.id,
                vector_store_3.id
            ],
        },
    ],
)
```

</TabItem>
</Tabs>

## Managing Vector Stores

### List All Vector Stores

```python
print("Listing available vector stores:")
vector_stores = client.vector_stores.list()

for vs in vector_stores:
    print(f"- {vs.name} (ID: {vs.id})")

    # List files in each vector store
    files_in_store = client.vector_stores.files.list(vector_store_id=vs.id)
    if files_in_store:
        print(f"  Files in '{vs.name}':")
        for file in files_in_store:
            print(f"    - {file.id}")
```

### Clean Up Vector Stores

<Tabs>
<TabItem value="single" label="Delete Single Store">

```python
# Delete a specific vector store
client.vector_stores.delete(vector_store_id=vector_store.id)
print(f"Deleted vector store: {vector_store.id}")
```

</TabItem>
<TabItem value="all" label="Delete All Stores">

```python
# Delete all existing vector stores
vector_stores_to_delete = [v.id for v in client.vector_stores.list()]
for del_vs_id in vector_stores_to_delete:
    client.vector_stores.delete(vector_store_id=del_vs_id)
    print(f"Deleted: {del_vs_id}")
```

</TabItem>
</Tabs>

## Complete Example: Building a RAG System

Here's a complete example that puts it all together:

```python
from io import BytesIO
from llama_stack_client import LlamaStackClient

# Initialize client
client = LlamaStackClient(base_url="http://localhost:5001")

# Step 1: Prepare and upload documents
knowledge_base = [
    ("Python is a high-level programming language.", {"category": "Programming"}),
    ("Machine learning is a subset of artificial intelligence.", {"category": "AI"}),
    ("Neural networks are inspired by the human brain.", {"category": "AI"}),
]

file_ids = []
for content, metadata in knowledge_base:
    with BytesIO(content.encode()) as file_buffer:
        file_buffer.name = f"{metadata['category'].lower()}_{len(file_ids)}.txt"
        response = client.files.create(file=file_buffer, purpose="assistants")
        file_ids.append(response.id)

# Step 2: Create vector store
vector_store = client.vector_stores.create(
    name="tech_knowledge_base",
    file_ids=file_ids,
    embedding_model="all-MiniLM-L6-v2",
    embedding_dimension=384,
    provider_id="faiss"
)

# Step 3: Query the knowledge base
queries = [
    "What is Python?",
    "Tell me about neural networks",
    "What is machine learning?"
]

for query in queries:
    print(f"\nQuery: {query}")
    response = client.responses.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        input=query,
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [vector_store.id],
            },
        ],
    )
    print(f"Response: {response}")
```

## Migration from Legacy API

:::danger[Deprecation Notice]
The legacy `vector_io` and `vector_dbs` API is deprecated. Migrate to the OpenAI-compatible APIs for better compatibility and future support.
:::

If you're migrating from the deprecated `vector_io` and `vector_dbs` API:

<Tabs>
<TabItem value="old" label="Old API (Deprecated)">

```python
# OLD - Don't use
client.vector_dbs.register(vector_db_id="my_db", ...)
client.vector_io.insert(vector_db_id="my_db", chunks=chunks)
client.vector_io.query(vector_db_id="my_db", query="...")
```

</TabItem>
<TabItem value="new" label="New API (Recommended)">

```python
# NEW - Recommended approach
# 1. Upload files
file_response = client.files.create(file=file_buffer, purpose="assistants")

# 2. Create vector store
vector_store = client.vector_stores.create(
    name="my_store",
    file_ids=[file_response.id],
    embedding_model="all-MiniLM-L6-v2",
    embedding_dimension=384,
    provider_id="faiss"
)

# 3. Query using Responses API
response = client.responses.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    input=query,
    tools=[{"type": "file_search", "vector_store_ids": [vector_store.id]}],
)
```

</TabItem>
</Tabs>

### Migration Benefits

1. **Better OpenAI Ecosystem Integration**: Direct compatibility with OpenAI tools and workflows
2. **Future-Proof**: Continued support and feature development
3. **Full OpenAI Compatibility**: Vector Stores, Files, and Search APIs work with OpenAI's Responses API
4. **Enhanced Error Handling**: Individual document failures don't crash entire operations
