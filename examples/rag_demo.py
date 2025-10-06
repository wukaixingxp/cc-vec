import os

from cc_vec.rag_agent import CCVecRAGAgent

os.environ["ATHENA_OUTPUT_BUCKET"] = "s3://llama-stack-dev-test0/athena-results/"
# Custom Llama Stack configuration
rag_agent = CCVecRAGAgent(
    llama_stack_url="http://localhost:8321", model="groq/llama-3.1-8b-instant"
)

# Advanced knowledge base creation
result = rag_agent.create_knowledge_base_from_common_crawl(
    url_pattern="%.commoncrawl.org",
    vector_store_name="commoncrawl",
    limit=200,
    crawl="CC-MAIN-2025-33",
    status_codes=[200],
    mime_types=["text/html", "application/pdf"],
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    embedding_dimension=384,
    provider_id="faiss",
)

print(f"Knowledge base created successfully:")
print(f"  ID: {result['vector_store_id']}")
print(f"  Name: {result['vector_store_name']}")
print(f"  Documents: {result['total_documents']}")

# Query the knowledge base
vector_store_id = result["vector_store_id"]

# Example queries
queries = [
    "What is common crawl?",
]

print("\n" + "="*50)
print("Querying the Knowledge Base")
print("="*50)

for i, query in enumerate(queries, 1):
    print(f"\nQuery {i}: {query}")
    print("-" * 40)
    
    query_result = rag_agent.query_knowledge_base(vector_store_id, query)
    response = query_result["response"]
    
    print(f"Response: {response}")
    print()
