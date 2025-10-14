## How to use this example
### Prerequisites
1. Install [llama-stack](https://github.com/llama-stack/llama-stack) from source: `git clone https://github.com/llama-stack/llama-stack`
2. Install llama-stack: `cd llama-stack & pip install -e .`
3. Choose a API provider, eg Fireworks.ai or together.ai, export API keys to environment variables: `export FIREWORKS_API_KEY=xxx` or `export TOGETHER_API_KEY=xxx`.
3. Start llama-stack: `llama stack build --template starter --image-type venv --run`
4. setup environment variables: Environment variables:
     ATHENA_OUTPUT_BUCKET - Required S3 bucket for Athena query results (needed for reliable queries to Common Crawl metadata)
     AWS_ACCESS_KEY_ID - Required for Athena/S3 access (needed to run Athena queries)
     AWS_SECRET_ACCESS_KEY - Required for Athena/S3 access (needed to run Athena queries)
    AWS_SESSION_TOKEN - Optional for Athena/S3 access (needed to run Athena queries). This is required for temporary credentials
    OPENAI_API_KEY - Required for vector operations (index, query, list)
    OPENAI_BASE_URL - Optional custom OpenAI endpoint (e.g., http://localhost:8321/v1 for Llama Stack)
    OPENAI_EMBEDDING_MODEL - Embedding model to use (e.g., text-embedding-3-small, nomic-embed-text)
    OPENAI_EMBEDDING_DIMENSIONS - Embedding dimensions (optional, model-specific)
5. Start the example: `python3 cc_vec_complete_rag_workflow.py`
