"""
Gradio RAG Chatbot UI

This example provides a user-friendly Gradio interface for:
1. Building a RAG system by indexing Common Crawl content
2. Interactive chat with the indexed content

Run with: uv run python examples/gradio_rag_chatbot.py
"""

import os
import gradio as gr
from openai import OpenAI

from cc_vec import (
    stats,
    search,
    index,
    query_vector_store,
    delete_vector_store,
    FilterConfig,
    VectorStoreConfig,
)


# Global state to store vector store ID
vector_store_state = {"id": None, "name": None}


def build_rag(domain_url, crawl_ids_input, num_records, chunk_size, overlap):
    """
    Build RAG system by indexing Common Crawl content.
    
    Args:
        domain_url: Domain to crawl (e.g., commoncrawl.org)
        crawl_ids_input: Comma-separated crawl IDs (e.g., CC-MAIN-2024-33)
        num_records: Number of records to index
        chunk_size: Token chunk size for indexing
        overlap: Token overlap between chunks
        
    Returns:
        Status message with indexing results
    """
    try:
        print("\n" + "="*80)
        print("🚀 STARTING RAG SYSTEM BUILD")
        print("="*80)
        
        # Parse crawl IDs
        crawl_ids = [cid.strip() for cid in crawl_ids_input.split(",") if cid.strip()]
        
        if not domain_url:
            return "❌ Error: Please provide a domain URL"
        
        if not crawl_ids:
            return "❌ Error: Please provide at least one crawl ID"
        
        print(f"\n📋 Configuration:")
        print(f"  • Domain: {domain_url}")
        print(f"  • Crawl IDs: {', '.join(crawl_ids)}")
        print(f"  • Records to index: {num_records}")
        print(f"  • Chunk size: {chunk_size} tokens")
        print(f"  • Overlap: {overlap} tokens")
        
        # Create filter configuration
        print("\n🔧 Creating filter configuration...")
        filter_config = FilterConfig(
            url_host_names=[domain_url],
            crawl_ids=crawl_ids,
            status_codes=[200],
            mime_types=["text/html"],
        )
        print("  ✓ Filter configuration created")
        
        # Get statistics first
        print("\n📊 Getting statistics from Athena...")
        status_msg = "📊 Getting statistics...\n"
        stats_response = stats(filter_config)
        print(f"  ✓ Statistics retrieved:")
        print(f"    - Estimated records: {stats_response.estimated_records:,}")
        print(f"    - Estimated size: {stats_response.estimated_size_mb:.2f} MB")
        print(f"    - Athena cost: ${stats_response.estimated_cost_usd:.4f}")
        
        status_msg += f"  - Estimated records: {stats_response.estimated_records:,}\n"
        status_msg += f"  - Estimated size: {stats_response.estimated_size_mb:.2f} MB\n"
        status_msg += f"  - Athena cost: ${stats_response.estimated_cost_usd:.4f}\n\n"
        
        # Preview URLs
        print("\n🔍 Searching for sample URLs...")
        status_msg += "🔍 Searching for sample URLs...\n"
        results = search(filter_config, limit=3)
        print(f"  ✓ Found {len(results)} sample URLs:")
        status_msg += f"  Found {len(results)} sample URLs:\n"
        for i, record in enumerate(results[:3], 1):
            print(f"    {i}. {record.url}")
            status_msg += f"    {i}. {record.url}\n"
        
        status_msg += "\n⚙️ Indexing configuration:\n"
        
        # Create vector store configuration
        print("\n⚙️ Creating vector store configuration...")
        vector_store_name = f"rag-{domain_url.replace('.', '-')}"
        
        # Get embedding model and dimensions from environment or use defaults
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
        # Map common embedding models to their dimensions
        embedding_dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "sentence-transformers/nomic-ai/nomic-embed-text-v1.5": 768,
            "nomic-embed-text-v1.5": 768,
        }
        
        # Get dimensions from environment or use the mapping
        if os.getenv("OPENAI_EMBEDDING_DIMENSIONS"):
            embedding_dimensions = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS"))
        else:
            embedding_dimensions = embedding_dimensions_map.get(embedding_model, 1536)
        
        vector_store_config = VectorStoreConfig(
            name=vector_store_name,
            chunk_size=int(chunk_size),
            overlap=int(overlap),
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
        )
        
        print(f"  ✓ Vector store configuration:")
        print(f"    - Name: {vector_store_config.name}")
        print(f"    - Chunk size: {vector_store_config.chunk_size} tokens")
        print(f"    - Overlap: {vector_store_config.overlap} tokens")
        print(f"    - Embedding model: {vector_store_config.embedding_model}")
        print(f"    - Embedding dimensions: {vector_store_config.embedding_dimensions}")
        
        status_msg += f"  - Vector store: {vector_store_config.name}\n"
        status_msg += f"  - Chunk size: {vector_store_config.chunk_size} tokens\n"
        status_msg += f"  - Overlap: {vector_store_config.overlap} tokens\n"
        status_msg += f"  - Embedding model: {vector_store_config.embedding_model}\n"
        status_msg += f"  - Embedding dimensions: {vector_store_config.embedding_dimensions}\n"
        status_msg += f"  - Records to index: {num_records}\n\n"
        
        # Index content
        print(f"\n🔄 Starting indexing process for {num_records} records...")
        print("  (This may take 30-60 seconds depending on the number of records)")
        status_msg += f"🔄 Indexing {num_records} records (this may take 30-60 seconds)...\n"
        
        result = index(filter_config, vector_store_config, limit=int(num_records))
        
        vector_store_id = result["vector_store_id"]
        
        print(f"\n✅ Indexing complete!")
        print(f"  • Vector Store ID: {vector_store_id}")
        print(f"  • Records processed: {result['total_fetched']}")
        print(f"  • Successfully indexed: {result['successful_fetches']}")
        
        # Store in global state
        vector_store_state["id"] = vector_store_id
        vector_store_state["name"] = vector_store_name
        
        status_msg += "\n✅ Indexing complete!\n"
        status_msg += f"  - Vector Store ID: {vector_store_id}\n"
        status_msg += f"  - Records processed: {result['total_fetched']}\n"
        status_msg += f"  - Successfully indexed: {result['successful_fetches']}\n\n"
        status_msg += "🤖 RAG chatbot is now ready! You can start chatting in the chatbot tab.\n"
        
        print("\n🤖 RAG chatbot is now ready!")
        print("="*80)
        print()
        
        return status_msg
        
    except Exception as e:
        error_msg = f"❌ Error building RAG: {str(e)}"
        print(f"\n{error_msg}")
        print("="*80)
        return error_msg


def chat_with_rag(message, history):
    """
    Chat with the RAG system using indexed content.
    
    Args:
        message: User's message
        history: Chat history
        
    Returns:
        Response from the RAG system
    """
    try:
        # Check if vector store is initialized
        if not vector_store_state["id"]:
            return "❌ Please build the RAG system first in the 'Build RAG' tab."
        
        vector_store_id = vector_store_state["id"]
        
        # Set up OpenAI client
        client = OpenAI()
        model = os.getenv("MODEL_NAME", "gpt-4")
        
        # Create a response with file_search tool
        response = client.responses.create(
            model=model,
            input=message,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id],
                },
            ],
        )
        
        # Extract response text
        response_text = ""
        citations = []
        
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        response_text = content.text
                        
                        # Collect citations
                        if content.annotations:
                            unique_files = set()
                            for annotation in content.annotations:
                                if annotation.type == "file_citation":
                                    if annotation.file_id not in unique_files:
                                        citations.append(f"📄 {annotation.filename}")
                                        unique_files.add(annotation.file_id)
        
        # Add citations to response if any
        if citations:
            response_text += "\n\n**Sources:**\n" + "\n".join(citations)
        
        return response_text
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def cleanup_vector_store():
    """
    Delete the current vector store.
    
    Returns:
        Status message
    """
    try:
        if not vector_store_state["id"]:
            return "❌ No vector store to clean up."
        
        vector_store_id = vector_store_state["id"]
        delete_result = delete_vector_store(vector_store_id)
        
        msg = f"✅ Deleted vector store: {vector_store_id}\n"
        msg += f"Status: {delete_result.get('status', 'deleted')}"
        
        # Clear state
        vector_store_state["id"] = None
        vector_store_state["name"] = None
        
        return msg
        
    except Exception as e:
        return f"❌ Error cleaning up: {str(e)}"


def get_vector_store_info():
    """
    Get current vector store information.
    
    Returns:
        Vector store info or message if none exists
    """
    if vector_store_state["id"]:
        return f"📦 Vector Store ID: {vector_store_state['id']}\n📝 Name: {vector_store_state['name']}"
    else:
        return "⚠️ No vector store initialized. Please build RAG first."


# Create Gradio interface
with gr.Blocks(title="RAG Chatbot", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 RAG Chatbot with Common Crawl")
    gr.Markdown("Build a RAG system from Common Crawl data and chat with it!")
    
    with gr.Tabs():
        # Tab 1: Build RAG
        with gr.Tab("🔨 Build RAG"):
            gr.Markdown("## Configure and Build Your RAG System")
            
            with gr.Row():
                with gr.Column():
                    domain_input = gr.Textbox(
                        label="Domain URL",
                        placeholder="e.g., commoncrawl.org",
                        value="commoncrawl.org",
                    )
                    crawl_ids_input = gr.Textbox(
                        label="Crawl IDs (comma-separated)",
                        placeholder="e.g., CC-MAIN-2024-33, CC-MAIN-2024-30",
                        value="CC-MAIN-2024-33",
                    )
                
                with gr.Column():
                    num_records = gr.Slider(
                        minimum=1,
                        maximum=100,
                        value=5,
                        step=1,
                        label="Number of Records to Index",
                    )
                    chunk_size = gr.Slider(
                        minimum=100,
                        maximum=2000,
                        value=1000,
                        step=100,
                        label="Chunk Size (tokens)",
                    )
                    overlap = gr.Slider(
                        minimum=0,
                        maximum=500,
                        value=200,
                        step=50,
                        label="Overlap (tokens)",
                    )
            
            build_button = gr.Button("🚀 Build RAG System", variant="primary", size="lg")
            build_output = gr.Textbox(
                label="Build Status",
                lines=15,
                max_lines=20,
                show_copy_button=True,
            )
            
            build_button.click(
                fn=build_rag,
                inputs=[domain_input, crawl_ids_input, num_records, chunk_size, overlap],
                outputs=build_output,
            )
        
        # Tab 2: Chat
        with gr.Tab("💬 Chat"):
            gr.Markdown("## Chat with Your RAG System")
            
            vector_store_info = gr.Textbox(
                label="Vector Store Info",
                value=get_vector_store_info(),
                interactive=False,
                lines=2,
            )
            
            chatbot = gr.Chatbot(
                height=500,
                label="RAG Chatbot",
                show_copy_button=True,
            )
            
            msg = gr.Textbox(
                label="Your Message",
                placeholder="Ask a question about the indexed content...",
                lines=2,
            )
            
            with gr.Row():
                submit_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear Chat")
                refresh_info_btn = gr.Button("🔄 Refresh Info")
            
            # Handle chat
            def respond(message, chat_history):
                bot_message = chat_with_rag(message, chat_history)
                chat_history.append((message, bot_message))
                return "", chat_history
            
            msg.submit(respond, [msg, chatbot], [msg, chatbot])
            submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
            clear_btn.click(lambda: None, None, chatbot, queue=False)
            refresh_info_btn.click(get_vector_store_info, None, vector_store_info)
        
        # Tab 3: Manage
        with gr.Tab("⚙️ Manage"):
            gr.Markdown("## Manage Your Vector Store")
            
            current_info = gr.Textbox(
                label="Current Vector Store",
                value=get_vector_store_info(),
                interactive=False,
                lines=3,
            )
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Info")
                cleanup_btn = gr.Button("🗑️ Delete Vector Store", variant="stop")
            
            cleanup_output = gr.Textbox(
                label="Cleanup Status",
                lines=3,
            )
            
            refresh_btn.click(get_vector_store_info, None, current_info)
            cleanup_btn.click(cleanup_vector_store, None, cleanup_output)
    
    gr.Markdown("""
    ---
    ### 📖 Instructions:
    1. **Build RAG**: Configure your domain, crawl IDs, and indexing parameters, then click "Build RAG System"
    2. **Chat**: Once built, go to the Chat tab and start asking questions about the indexed content
    3. **Manage**: Clean up resources when done
    
    ### 🔧 Environment Variables Required:
    - `OPENAI_API_KEY`: Your OpenAI API key (or 'dummy' for llama-stack)
    - `OPENAI_BASE_URL`: API base URL (e.g., http://localhost:8321/v1/openai/v1)
    - `OPENAI_EMBEDDING_MODEL`: Embedding model to use
    - `MODEL_NAME`: Model name for responses
    - `ATHENA_OUTPUT_BUCKET`: S3 bucket for Athena output
    """)


if __name__ == "__main__":
    # Set up environment (modify as needed)
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "dummy"
    if not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = "http://localhost:8321/v1/openai/v1"
    if not os.getenv("OPENAI_EMBEDDING_MODEL"):
        os.environ["OPENAI_EMBEDDING_MODEL"] = "dummy"
    if not os.getenv("MODEL_NAME"):
        os.environ["MODEL_NAME"] = "together/meta-llama/Llama-3.3-70B-Instruct-Turbo"
    
    # Check required environment variables
    required_vars = ["OPENAI_API_KEY", "ATHENA_OUTPUT_BUCKET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    print("🚀 Starting Gradio RAG Chatbot...")
    print(f"📝 Domain: Configure in the UI")
    print(f"🔗 URL: http://localhost:7860")
    
    # Launch Gradio app
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
