# 🚀 Streamlit RAG Chatbot

A beautiful, modern interface for building and chatting with a RAG (Retrieval-Augmented Generation) system powered by Common Crawl data.

## ✨ Features

- **🎨 Beautiful UI**: Clean, modern interface with gradient headers and custom styling
- **📊 Real-time Statistics**: View estimated records, data size, and Athena costs
- **💬 Interactive Chat**: Native Streamlit chat interface with message history
- **📦 Vector Store Management**: Easy creation and deletion of vector stores
- **🔍 Source Citations**: Automatic source attribution in responses
- **⚙️ Configuration Panel**: Intuitive controls for all parameters
- **📱 Responsive Design**: Works beautifully on desktop and mobile

## 🚀 Quick Start

### Option 1: Using .env File (Recommended)

1. **Install python-dotenv**:
   ```bash
   pip install python-dotenv
   # or with uv
   uv pip install python-dotenv
   ```

2. **Create a `.env` file** in the project root (`/Users/kaiwu/work/kaiwu/cc-vec/.env`):
   ```env
   OPENAI_API_KEY=dummy
   OPENAI_BASE_URL=http://localhost:8321/v1/openai/v1
   OPENAI_EMBEDDING_MODEL=sentence-transformers/nomic-ai/nomic-embed-text-v1.5
   MODEL_NAME=together/meta-llama/Llama-3.3-70B-Instruct-Turbo
   ATHENA_OUTPUT_BUCKET=s3://my-bucket/
   AWS_DEFAULT_REGION=us-west-2
   ```

3. **Run the app**:
   ```bash
   # Using uv (recommended)
   uv run streamlit run examples/streamlit_rag_chatbot.py

   # Or using regular Python
   streamlit run examples/streamlit_rag_chatbot.py
   ```

The app will automatically load your `.env` file on startup and use those values as defaults.

### Option 2: Configure in the UI

The app will open in your browser at `http://localhost:8501`

**Note:** You can configure environment variables directly in the app's Settings tab, which will override `.env` values for the current session.

## 📖 How to Use

### 1. Configure Settings (⚙️ Settings Tab)

**First-time setup:** Configure your environment variables in the Settings tab:

1. **API Configuration**:
   - OpenAI API Key (e.g., `dummy` for llama-stack)
   - OpenAI Base URL (e.g., `http://localhost:8321/v1/openai/v1`)
   - Embedding Model (e.g., `sentence-transformers/nomic-ai/nomic-embed-text-v1.5`)

2. **AWS & Model Configuration**:
   - Model Name (e.g., `together/meta-llama/Llama-3.3-70B-Instruct-Turbo`)
   - Athena Output Bucket (e.g., `s3://your-bucket/`)
   - AWS Region (default: `us-west-2`)

3. Click "💾 Save Configuration"

### 2. Build RAG System (🔨 Build RAG Tab)

1. **Configure Data Source**:
   - Enter the domain URL (e.g., `commoncrawl.org`)
   - Specify crawl IDs (e.g., `CC-MAIN-2024-33`)
   - Choose number of records to index (1-100)

2. **Build**:
   - Click "🚀 Build RAG System"
   - Watch the progress bar
   - View statistics and configuration details
   - See sample URLs that were indexed

**Note:** Chunking is automatically configured with optimal defaults (1000 tokens, 200 overlap)

### 2. Chat with RAG (💬 Chat Tab)

1. Navigate to the Chat tab
2. Type your question in the input box
3. Get intelligent responses based on indexed content
4. View source citations for each response
5. Clear chat history when needed

### 3. Manage Vector Store (⚙️ Manage Tab)

- View current vector store status
- Check environment configuration
- Delete vector store when done (careful - irreversible!)

## 🎯 Key Improvements over Gradio

- **Better Visual Design**: Gradient headers, custom CSS, cleaner layout
- **Native Chat Interface**: Streamlit's built-in chat components
- **Session State Management**: Persistent state across interactions
- **Better Progress Indicators**: Real-time feedback during build
- **Expandable Sections**: Cleaner information display
- **Sidebar Navigation**: Quick guide and status at a glance
- **Metrics Display**: Beautiful metric cards for statistics
- **Better Error Handling**: Clear, styled error messages

## 🎨 UI Features

### Main Page
- Gradient title with modern design
- Three organized tabs for different functions
- Responsive columns for inputs
- Clear visual hierarchy

### Build RAG Tab
- Two-column layout for configuration
- Interactive sliders with tooltips
- Real-time embedding model display
- Progress indicators during build
- Detailed statistics with metric cards
- Expandable configuration details
- Sample URL preview

### Chat Tab
- Native Streamlit chat interface
- Message bubbles for user and assistant
- Source citations in responses
- Clear chat history button
- Vector store status indicator

### Manage Tab
- Styled info boxes for status
- Warning for destructive actions
- Environment variable checker
- Clean delete interface

### Sidebar
- Navigation guide
- Quick status indicator
- Visual separation with markdown
- Branding elements

## 🔧 Technical Details

### Embedding Dimension Auto-Detection

The app automatically detects the correct embedding dimensions based on the model:

- `text-embedding-3-small`: 1536 dimensions
- `text-embedding-3-large`: 3072 dimensions
- `text-embedding-ada-002`: 1536 dimensions
- `sentence-transformers/nomic-ai/nomic-embed-text-v1.5`: 768 dimensions
- `nomic-embed-text-v1.5`: 768 dimensions

You can override this with the `OPENAI_EMBEDDING_DIMENSIONS` environment variable.

### Console Logging

The app includes detailed console logging for debugging:
- Configuration details
- Progress indicators with checkmarks
- Statistics from Athena
- Vector store information
- Error messages

Watch the console output for detailed progress information!

## 🐛 Troubleshooting

### "Missing required environment variables"
Make sure `OPENAI_API_KEY` and `ATHENA_OUTPUT_BUCKET` are set.

### "Unable to verify/create output bucket"
Ensure your S3 bucket path includes the `s3://` prefix (e.g., `s3://my-bucket/`).

### "Embedding dimension inconsistent"
The app now auto-detects dimensions. If you see this error, set `OPENAI_EMBEDDING_DIMENSIONS` explicitly.

### Chat not responding
Make sure you've built the RAG system first in the "Build RAG" tab.

## 📝 Example Workflow

```bash
# 1. Set environment variables
export OPENAI_API_KEY="dummy"
export OPENAI_BASE_URL="http://localhost:8321/v1/openai/v1"
export OPENAI_EMBEDDING_MODEL="sentence-transformers/nomic-ai/nomic-embed-text-v1.5"
export MODEL_NAME="together/meta-llama/Llama-3.3-70B-Instruct-Turbo"
export ATHENA_OUTPUT_BUCKET="s3://my-bucket/"

# 2. Start the app
uv run streamlit run examples/streamlit_rag_chatbot.py

# 3. In the browser:
#    - Go to "Build RAG" tab
#    - Configure: commoncrawl.org, CC-MAIN-2024-33, 5 records
#    - Click "Build RAG System"
#    - Wait for completion
#    - Go to "Chat" tab
#    - Ask: "What is Common Crawl?"
#    - Get intelligent responses with citations!
```

## 🎉 Enjoy!

The Streamlit version provides a much cleaner, more professional interface compared to Gradio. The app is production-ready with proper error handling, beautiful UI, and all the features you need for building and using RAG systems with Common Crawl data.

---

Built with ❤️ using [cc-vec](https://github.com/yourusername/cc-vec) and [Streamlit](https://streamlit.io)
