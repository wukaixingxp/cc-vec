"""
Complete RAG Workflow: Index, Query, and Use with OpenAI Assistant

This comprehensive example shows:
1. Searching and getting stats before indexing
2. Indexing content with custom chunking configuration
3. Listing vector stores
4. Direct vector store queries (using cc-vec)
5. Advanced RAG with OpenAI Assistant + file_search tool
6. Cleanup

Run with: uv run python examples/complete_rag_workflow.py
"""

import os
import time
from openai import OpenAI

from cc_vec import (
    stats,
    search,
    index,
    list_vector_stores,
    query_vector_store,
    delete_vector_store,
    FilterConfig,
    VectorStoreConfig,
)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def main():
    # =========================================================================
    # Most important configuration: set your OpenAI API key and base URL to llama-stack endpoint
    # Configuration

    filter_config = FilterConfig(
        url_host_names=["commoncrawl.org"],  # search for commoncrawl.org 
        crawl_ids=["CC-MAIN-2024-33"],
        status_codes=[200],
        mime_types=["text/html"],
    )

    # =========================================================================
    # PART 1: Explore before indexing
    # =========================================================================
    print_section("PART 1: Explore Common Crawl Data")

    # Get statistics
    print("📊 Getting statistics for common-crawl content...")
    stats_response = stats(filter_config)
    print(f"  - Estimated records: {stats_response.estimated_records:,}")
    print(f"  - Estimated size: {stats_response.estimated_size_mb:.2f} MB")
    print(f"  - Athena cost: ${stats_response.estimated_cost_usd:.4f}")
    print(f"  - Data to scan: {stats_response.data_scanned_gb:.2f} GB")

    # Preview actual URLs
    print("\n🔍 Searching for sample URLs...")
    results = search(filter_config, limit=5)
    print(f"  Found {len(results)} sample URLs:")
    for i, record in enumerate(results[:3], 1):
        print(f"    {i}. {record.url}")
        print(f"       Status: {record.status}, MIME: {record.mime}")

    # =========================================================================
    # PART 2: Index into Vector Store
    # =========================================================================
    print_section("PART 2: Index Content into Vector Store")

    vector_store_config = VectorStoreConfig(
        name="cc-ls",
        chunk_size=1000,  # Larger chunks for academic content
        overlap=200,  # Less overlap for distinct sections
        embedding_model= os.getenv("OPENAI_EMBEDDING_MODEL"),  # Use sentence-transformers/all-MiniLM-L6-v2
    )
    print("⚙️  Indexing configuration:")
    print(f"  - Vector store: {vector_store_config.name}")
    print(f"  - Chunk size: {vector_store_config.chunk_size} tokens")
    print(f"  - Overlap: {vector_store_config.overlap} tokens")
    print(f"  - Embedding model: {vector_store_config.embedding_model}")
    print("  - Records to index: 5")

    print("\n🔄 Indexing (this may take 30-60 seconds)...")
    result = index(filter_config, vector_store_config, limit=5)

    vector_store_id = result["vector_store_id"]
    print("\n✅ Indexing complete!")
    print(f"  - Vector Store ID: {vector_store_id}")
    print(f"  - Records processed: {result['total_fetched']}")
    print(f"  - Successfully indexed: {result['successful_fetches']}")

    # =========================================================================
    # PART 3: List and Query Vector Stores
    # =========================================================================
    print_section("PART 3: Vector Store Operations")

    # List all cc-vec vector stores
    print("📋 Listing cc-vec vector stores...")
    stores = list_vector_stores(cc_vec_only=True)
    print(f"  Found {len(stores)} cc-vec vector store(s):")
    for store in stores[-3:]:  # Show last 3
        print(f"    - {store['name']} (ID: {store['id']}, Status: {store['status']})")

    # Direct query using cc-vec
    print("\n🔎 Direct vector store query (using cc-vec)...")
    query_result = query_vector_store(
        vector_store_id=vector_store_id,
        query="What is Common Crawl?",
        limit=3,
    )
    print(f"  Found {len(query_result.get('results', []))} results:")
    for i, res in enumerate(query_result.get("results", [])[:2], 1):
        content = res.get("content", "")
        if hasattr(content, "text"):
            content = content.text
        preview = str(content)[:150].replace("\n", " ")
        print(f"    {i}. Score: {res.get('score', 0):.3f}")
        print(f"       Preview: {preview}...")

    # =========================================================================
    # PART 4: Advanced RAG with OpenAI Responses API
    # =========================================================================
    print_section("PART 4: Advanced RAG with OpenAI Responses API")
    # Set up OpenAI client to llama-stack endpoint
    client = OpenAI()
    # Get the list of available models and use the first one
    model = os.getenv("MODEL_NAME")
    print(f"🤖 Using model: {model}")
    
    # Multiple questions demonstrating RAG
    questions = [
        "What is Common Crawl? How does it work?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 80}")
        print(f"💭 Question {i}: {question}")
        print("─" * 80)

        # Create a response with file_search tool
        response = client.responses.create(
            model=model,
            input=question,
            tools=[
                {  # Using Responses API built-in tools
                "type": "file_search",
                "vector_store_ids": [vector_store_id],  # Vector store containing uploaded files
                },
            ],
        )

        # Display response
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        print(f"\n💡 Answer:\n{content.text}\n")

                        # Show file citations
                        if content.annotations:
                            print("📚 Citations:")
                            unique_files = set()
                            for annotation in content.annotations:
                                if annotation.type == "file_citation":
                                    if annotation.file_id not in unique_files:
                                        print(
                                            f"  - File: {annotation.file_id} ({annotation.filename})"
                                        )
                                        unique_files.add(annotation.file_id)

        # Small delay between questions
        if i < len(questions):
            time.sleep(1)

    # =========================================================================
    # PART 5: Cleanup
    # =========================================================================
    print_section("PART 5: Cleanup")

    # Ask user if they want to cleanup
    cleanup = input("\n🗑️  Delete vector store? (y/N): ").strip().lower()

    if cleanup == "y":
        print("\n🧹 Cleaning up...")

        # Delete vector store
        delete_result = delete_vector_store(vector_store_id)
        print(f"  ✓ Deleted vector store: {vector_store_id}")
        print(f"    Status: {delete_result.get('status', 'deleted')}")

        print("\n✅ Cleanup complete!")
    else:
        print("\n📌 Resources preserved:")
        print(f"  - Vector Store ID: {vector_store_id}")
        print("\nTo clean up later:")
        print(f"  - CLI: uv run cc-vec delete-vector-store {vector_store_id}")
        print(f"  - Python: delete_vector_store('{vector_store_id}')")

    print_section("Example Complete! 🎉")
    print("You've learned how to:")
    print("  ✓ Explore Common Crawl data (stats, search)")
    print("  ✓ Index content into vector stores")
    print("  ✓ Query vector stores directly")
    print("  ✓ Use OpenAI Responses API with file_search for RAG")
    print("  ✓ Manage and cleanup resources")


if __name__ == "__main__":
    # Check environment
    os.environ["OPENAI_API_KEY"] = 'dummy'
    os.environ["OPENAI_BASE_URL"] = 'http://localhost:8321/v1/openai/v1'
    os.environ["OPENAI_EMBEDDING_MODEL"] = 'dummy'
    # set llama-stack model name to use for testing
    #os.environ["MODEL_NAME"] = 'fireworks/accounts/fireworks/models/llama-v3p3-70b-instruct'
    os.environ["MODEL_NAME"] = 'together/meta-llama/Llama-3.3-70B-Instruct-Turbo'
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        exit(1)
    if not os.getenv("ATHENA_OUTPUT_BUCKET"):
        print("❌ ATHENA_OUTPUT_BUCKET not set")
        exit(1)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
