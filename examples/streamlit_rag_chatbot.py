"""
Streamlit RAG Chatbot UI

This example provides a beautiful Streamlit interface for:
1. Building a RAG system by indexing Common Crawl content
2. Interactive chat with the indexed content

Run with: uv run streamlit run examples/streamlit_rag_chatbot.py
"""

import os
import streamlit as st
from openai import OpenAI
from pathlib import Path

from cc_vec import (
    stats,
    search,
    index,
    query_vector_store,
    delete_vector_store,
    list_vector_stores,
    FilterConfig,
    VectorStoreConfig,
)

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    
    # Look for .env file in current directory or parent directories
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        # Try current directory
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"✅ Loaded environment variables from {env_path}")
        else:
            print("ℹ️  No .env file found, using system environment variables")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Proceeding with system environment variables only")


# Page configuration
st.set_page_config(
    page_title="RAG Chatbot with Common Crawl",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stTab {
        font-size: 1.1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None
if "vector_store_name" not in st.session_state:
    st.session_state.vector_store_name = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "build_complete" not in st.session_state:
    st.session_state.build_complete = False
if "config_saved" not in st.session_state:
    st.session_state.config_saved = False


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
        Success status and results dictionary
    """
    try:
        print("\n" + "="*80)
        print("🚀 STARTING RAG SYSTEM BUILD")
        print("="*80)
        
        # Parse crawl IDs
        crawl_ids = [cid.strip() for cid in crawl_ids_input.split(",") if cid.strip()]
        
        if not domain_url:
            return False, {"error": "Please provide a domain URL"}
        
        if not crawl_ids:
            return False, {"error": "Please provide at least one crawl ID"}
        
        print(f"\n📋 Configuration:")
        print(f"  • Domain: {domain_url}")
        print(f"  • Crawl IDs: {', '.join(crawl_ids)}")
        print(f"  • Records to index: {'ALL (no limit)' if num_records is None else num_records}")
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
        stats_response = stats(filter_config)
        print(f"  ✓ Statistics retrieved:")
        print(f"    - Estimated records: {stats_response.total_estimated_records:,}")
        print(f"    - Estimated size: {stats_response.total_estimated_size_mb:.2f} MB")
        cost_usd = stats_response.total_estimated_cost_usd if stats_response.total_estimated_cost_usd is not None else 0.0
        print(f"    - Athena cost: ${cost_usd:.4f}")
        
        # Preview URLs
        print("\n🔍 Searching for sample URLs...")
        results = search(filter_config, limit=3)
        print(f"  ✓ Found {len(results)} sample URLs:")
        sample_urls = []
        for i, record in enumerate(results[:3], 1):
            print(f"    {i}. {record.url}")
            sample_urls.append(str(record.url))
        
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
        
        # Index content
        if num_records is None:
            print(f"\n🔄 Starting indexing process for ALL available records...")
            print("  (This may take several minutes depending on the number of records)")
        else:
            print(f"\n🔄 Starting indexing process for {num_records} records...")
            print("  (This may take 30-60 seconds depending on the number of records)")

        result = index(filter_config, vector_store_config, limit=int(num_records) if num_records is not None else None)
        
        vector_store_id = result["vector_store_id"]
        
        print(f"\n✅ Indexing complete!")
        print(f"  • Vector Store ID: {vector_store_id}")
        print(f"  • Records processed: {result['total_fetched']}")
        print(f"  • Successfully indexed: {result['successful_fetches']}")
        print("\n🤖 RAG chatbot is now ready!")
        print("="*80)
        print()
        
        return True, {
            "vector_store_id": vector_store_id,
            "vector_store_name": vector_store_name,
            "stats": stats_response,
            "sample_urls": sample_urls,
            "result": result,
            "config": {
                "embedding_model": embedding_model,
                "embedding_dimensions": embedding_dimensions,
                "chunk_size": chunk_size,
                "overlap": overlap,
            }
        }
        
    except Exception as e:
        error_msg = f"Error building RAG: {str(e)}"
        print(f"\n❌ {error_msg}")
        print("="*80)
        return False, {"error": error_msg}


def chat_with_rag(message):
    """
    Chat with the RAG system using indexed content.
    
    Args:
        message: User's message
        
    Returns:
        Response from the RAG system
    """
    try:
        if not st.session_state.vector_store_id:
            return "❌ Please build the RAG system first in the 'Build RAG' tab."
        
        vector_store_id = st.session_state.vector_store_id
        
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


# Main UI
st.markdown('<h1 class="main-header">🤖 RAG Chatbot</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Build a RAG system from Common Crawl data and chat with it!</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Settings", "🔨 Build RAG", "💬 Chat", "📦 Manage"])

# Tab 1: Settings
with tab1:
    st.header("⚙️ Environment Configuration")
    st.markdown("Configure your API keys and environment settings here. These will be used throughout the application.")
    
    # Save config button at top
    col_save, col_reset = st.columns([1, 1])
    
    st.markdown("---")
    
    # Configuration inputs
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔑 API Configuration")
        
        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            help="Your OpenAI API key or 'dummy' for llama-stack"
        )
        
        openai_base_url = st.text_input(
            "OpenAI Base URL",
            value=os.getenv("OPENAI_BASE_URL", ""),
            help="API endpoint (e.g., http://localhost:8321/v1/openai/v1)"
        )
        
        openai_embedding_model = st.text_input(
            "Embedding Model",
            value=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            help="Embedding model name"
        )
    
    with col2:
        st.subheader("☁️ AWS & Model Configuration")
        
        model_name = st.text_input(
            "Model Name",
            value=os.getenv("MODEL_NAME", "gpt-4"),
            help="LLM model for chat responses"
        )
        
        athena_output_bucket = st.text_input(
            "Athena Output Bucket",
            value=os.getenv("ATHENA_OUTPUT_BUCKET", ""),
            help="S3 bucket path (e.g., s3://my-bucket/)"
        )
        
        aws_region = st.text_input(
            "AWS Region",
            value=os.getenv("AWS_DEFAULT_REGION", "us-west-2"),
            help="AWS region for Athena queries"
        )
    
    st.markdown("---")
    
    # Save button
    if st.button("💾 Save Configuration", type="primary", use_container_width=True):
        # Set environment variables
        os.environ["OPENAI_API_KEY"] = openai_api_key
        os.environ["OPENAI_BASE_URL"] = openai_base_url
        os.environ["OPENAI_EMBEDDING_MODEL"] = openai_embedding_model
        os.environ["MODEL_NAME"] = model_name
        os.environ["ATHENA_OUTPUT_BUCKET"] = athena_output_bucket
        os.environ["AWS_DEFAULT_REGION"] = aws_region
        
        st.session_state.config_saved = True
        st.success("✅ Configuration saved successfully!")
        st.info("You can now proceed to the 'Build RAG' tab to create your vector store.")
    
    # Show current status
    st.markdown("---")
    with st.expander("📋 Current Configuration Status"):
        status_items = [
            ("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
            ("OPENAI_BASE_URL", os.getenv("OPENAI_BASE_URL")),
            ("OPENAI_EMBEDDING_MODEL", os.getenv("OPENAI_EMBEDDING_MODEL")),
            ("MODEL_NAME", os.getenv("MODEL_NAME")),
            ("ATHENA_OUTPUT_BUCKET", os.getenv("ATHENA_OUTPUT_BUCKET")),
            ("AWS_DEFAULT_REGION", os.getenv("AWS_DEFAULT_REGION")),
        ]
        
        for var_name, var_value in status_items:
            if var_value:
                # Mask sensitive values
                if "KEY" in var_name and var_value != "dummy":
                    display_value = f"{var_value[:8]}..." if len(var_value) > 8 else "***"
                else:
                    display_value = var_value
                st.write(f"✅ **{var_name}:** `{display_value}`")
            else:
                st.write(f"❌ **{var_name}:** Not Set")

# Tab 2: Build RAG
with tab2:
    st.header("Configure and Build Your RAG System")
    
    # Check if configuration is set
    required_vars = ["OPENAI_API_KEY", "ATHENA_OUTPUT_BUCKET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"❌ Missing required configuration: {', '.join(missing_vars)}")
        st.info("⚠️ Please configure the required settings in the **Settings** tab first.")
        st.stop()
    
    # Configuration inputs
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Data Source")
        domain_url = st.text_input(
            "Domain URL",
            value="commoncrawl.org",
            help="Domain to crawl (e.g., commoncrawl.org)"
        )
        crawl_ids = st.text_input(
            "Crawl IDs (comma-separated)",
            value="CC-MAIN-2024-33",
            help="e.g., CC-MAIN-2024-33, CC-MAIN-2024-30"
        )
    
    with col2:
        st.subheader("⚙️ Indexing Configuration")

        # Checkbox for unlimited records
        unlimited = st.checkbox(
            "No limit (index all available records)",
            value=False,
            help="When checked, all matching records will be indexed"
        )

        if unlimited:
            num_records = None
            st.info("📊 Will index all available records")
        else:
            num_records = st.number_input(
                "Number of Records to Index",
                min_value=1,
                value=5,
                step=1,
                help="Enter any number. More records = more content but longer processing time"
            )

        st.info(f"📊 Embedding Model: {os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')}")
        st.info(f"🔧 Using default chunking: 1000 tokens with 200 token overlap")
    
    st.markdown("---")
    
    # Build button
    if st.button("🚀 Build RAG System", type="primary", use_container_width=True):
        with st.spinner("🔄 Building RAG system... This may take 30-60 seconds"):
            # Create progress placeholder
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            progress_placeholder.progress(0.1, "Creating filter configuration...")
            
            # Use default values for chunking
            chunk_size = 1000
            overlap = 200
            
            success, result = build_rag(domain_url, crawl_ids, num_records, chunk_size, overlap)
            
            if success:
                progress_placeholder.progress(1.0, "✅ Complete!")
                
                # Store in session state
                st.session_state.vector_store_id = result["vector_store_id"]
                st.session_state.vector_store_name = result["vector_store_name"]
                st.session_state.build_complete = True
                
                # Display success message with details
                st.success("✅ RAG system built successfully!")
                
                # Show statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Estimated Records", f"{result['stats'].total_estimated_records:,}")
                with col2:
                    st.metric("Data Size", f"{result['stats'].total_estimated_size_mb:.2f} MB")
                with col3:
                    st.metric("Athena Cost", f"${result['stats'].total_estimated_cost_usd:.4f}")
                
                # Show configuration
                with st.expander("📋 Configuration Details", expanded=True):
                    st.write(f"**Vector Store ID:** `{result['vector_store_id']}`")
                    st.write(f"**Vector Store Name:** `{result['vector_store_name']}`")
                    st.write(f"**Embedding Model:** {result['config']['embedding_model']}")
                    st.write(f"**Embedding Dimensions:** {result['config']['embedding_dimensions']}")
                    st.write(f"**Chunk Size:** {result['config']['chunk_size']} tokens")
                    st.write(f"**Overlap:** {result['config']['overlap']} tokens")
                    st.write(f"**Records Processed:** {result['result']['total_fetched']}")
                    st.write(f"**Successfully Indexed:** {result['result']['successful_fetches']}")
                
                # Show sample URLs
                with st.expander("🔍 Sample URLs Indexed"):
                    for i, url in enumerate(result['sample_urls'], 1):
                        st.write(f"{i}. {url}")
                
                st.info("💬 Ready to chat! Go to the **Chat** tab to start asking questions.")
                
            else:
                progress_placeholder.empty()
                st.error(f"❌ {result.get('error', 'Unknown error occurred')}")

# Tab 3: Chat
with tab3:
    st.header("Chat with Your RAG System")
    
    # Show vector store info
    if st.session_state.vector_store_id:
        with st.expander("📦 Vector Store Info", expanded=False):
            st.write(f"**ID:** `{st.session_state.vector_store_id}`")
            st.write(f"**Name:** `{st.session_state.vector_store_name}`")
            st.success("✅ Vector store is active")
    else:
        st.warning("⚠️ No vector store initialized. Please build RAG first in the 'Build RAG' tab.")
    
    st.markdown("---")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the indexed content..."):
        if not st.session_state.vector_store_id:
            st.error("❌ Please build the RAG system first in the 'Build RAG' tab.")
        else:
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Get bot response
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking..."):
                    response = chat_with_rag(prompt)
                st.markdown(response)
            
            # Add assistant response to chat
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Tab 4: Manage
with tab4:
    st.header("Manage Your Vector Stores")

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # List all vector stores
    st.subheader("📦 All Vector Stores")

    try:
        vector_stores = list_vector_stores(cc_vec_only=True)

        if vector_stores:
            st.write(f"Found **{len(vector_stores)}** vector store(s):")

            for store in vector_stores:
                with st.expander(f"📦 {store['name']} ({store['id']})", expanded=True):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Basic Info:**")
                        st.write(f"- **ID:** `{store['id']}`")
                        st.write(f"- **Name:** `{store['name']}`")
                        st.write(f"- **Status:** {store['status']}")
                        st.write(f"- **Created:** {store['created_at']}")

                        if store.get('file_counts'):
                            st.write("\n**File Counts:**")
                            st.write(f"- Total: {store['file_counts'].get('total', 0)}")
                            st.write(f"- Completed: {store['file_counts'].get('completed', 0)}")
                            st.write(f"- Failed: {store['file_counts'].get('failed', 0)}")

                    with col2:
                        if store.get('metadata'):
                            st.write("**Metadata:**")
                            metadata = store['metadata']
                            for key, value in metadata.items():
                                st.write(f"- **{key}:** {value}")

                    # Action buttons
                    st.markdown("---")
                    action_col1, action_col2, action_col3 = st.columns(3)

                    with action_col1:
                        # Load button
                        is_current = st.session_state.vector_store_id == store['id']
                        if st.button(
                            "✅ Current" if is_current else "📥 Load",
                            key=f"load_{store['id']}",
                            disabled=is_current,
                            use_container_width=True
                        ):
                            st.session_state.vector_store_id = store['id']
                            st.session_state.vector_store_name = store['name']
                            st.session_state.build_complete = True
                            st.success(f"✅ Loaded vector store: {store['name']}")
                            st.rerun()

                    with action_col2:
                        # Query test button
                        if st.button("🔍 Test Query", key=f"query_{store['id']}", use_container_width=True):
                            st.info("Go to the Chat tab to query this vector store")

                    with action_col3:
                        # Delete button
                        if st.button("🗑️ Delete", key=f"delete_{store['id']}", type="secondary", use_container_width=True):
                            try:
                                delete_result = delete_vector_store(store['id'])

                                # Clear session state if this was the active store
                                if st.session_state.vector_store_id == store['id']:
                                    st.session_state.vector_store_id = None
                                    st.session_state.vector_store_name = None
                                    st.session_state.build_complete = False
                                    st.session_state.messages = []

                                st.success(f"✅ Deleted vector store: {store['name']}")
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Error deleting vector store: {str(e)}")
        else:
            st.info("ℹ️ No vector stores found. Build one in the 'Build RAG' tab.")

    except Exception as e:
        st.error(f"❌ Error fetching vector stores: {str(e)}")
        st.info("Make sure your OpenAI API configuration is correct in the Settings tab.")

    st.markdown("---")

    # Current session info
    if st.session_state.vector_store_id:
        st.subheader("🎯 Active Vector Store")
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.write(f"**ID:** `{st.session_state.vector_store_id}`")
        st.write(f"**Name:** `{st.session_state.vector_store_name}`")
        st.write("**Status:** ✅ Loaded and ready for chat")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("ℹ️ No vector store currently loaded. Load one from the list above or build a new one.")

    st.markdown("---")

    # Environment info
    with st.expander("🔧 Environment Configuration"):
        st.write("**Required Environment Variables:**")
        st.code(f"""
OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not Set'}
OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', '❌ Not Set')}
OPENAI_EMBEDDING_MODEL: {os.getenv('OPENAI_EMBEDDING_MODEL', '❌ Not Set')}
MODEL_NAME: {os.getenv('MODEL_NAME', '❌ Not Set')}
ATHENA_OUTPUT_BUCKET: {'✅ Set' if os.getenv('ATHENA_OUTPUT_BUCKET') else '❌ Not Set'}
        """)

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/streamlit/develop/logo.svg", width=50)
    st.title("Navigation")
    
    st.markdown("---")
    
    st.subheader("📖 Quick Guide")
    st.markdown("""
    1. **Build RAG** 🔨
       - Configure domain and crawl IDs
       - Set chunking parameters
       - Build your vector store
    
    2. **Chat** 💬
       - Ask questions about indexed content
       - Get answers with source citations
    
    3. **Manage** ⚙️
       - View vector store status
       - Delete when done
    """)
    
    st.markdown("---")
    
    if st.session_state.vector_store_id:
        st.success("✅ Vector Store Active")
    else:
        st.info("⚠️ No Vector Store")
    
    st.markdown("---")
    
    st.caption("Built with ❤️ using cc-vec")
    st.caption("Powered by Streamlit")


if __name__ == "__main__":
    # Check required environment variables
    required_vars = ["OPENAI_API_KEY", "ATHENA_OUTPUT_BUCKET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        st.info("""
        Please set the following environment variables:
        - `OPENAI_API_KEY`: Your OpenAI API key (or 'dummy' for llama-stack)
        - `OPENAI_BASE_URL`: API base URL (e.g., http://localhost:8321/v1/openai/v1)
        - `OPENAI_EMBEDDING_MODEL`: Embedding model to use
        - `MODEL_NAME`: Model name for responses
        - `ATHENA_OUTPUT_BUCKET`: S3 bucket for Athena output
        """)
        st.stop()
