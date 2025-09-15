#!/usr/bin/env python3
"""Simple test script to test MCP server with stdio."""

import subprocess
import json
import os
import time


def test_mcp_server():
    """Test MCP server by sending it stats, search, and fetch requests."""
    print("=== Testing MCP Server ===")

    # Set environment variables
    env = os.environ.copy()
    # OpenAI key is optional for test (only needed for index/query/list operations)
    if "OPENAI_API_KEY" in env:
        print("Using OpenAI API key from environment")
    else:
        print("Warning: OPENAI_API_KEY not set - index/query/list operations will fail")
    env["ATHENA_OUTPUT_BUCKET"] = "s3://llama-stack-dev-test0/athena-results/"

    # Start MCP server process
    cmd = ["uv", "run", "cc-vec-mcp"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        # MCP initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        print("Sending initialize request...")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        print(f"Initialize response: {response_line.strip()}")

        # Send initialized notification
        initialized_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        print("Sending initialized notification...")
        proc.stdin.write(json.dumps(initialized_notif) + "\n")
        proc.stdin.flush()

        # Test 1: Stats request
        print("\n=== Testing Stats ===")
        test_stats(proc)

        # Test 2: Search request
        print("\n=== Testing Search ===")
        test_search(proc)

        # Test 3: Fetch request
        print("\n=== Testing Fetch ===")
        test_fetch(proc)

        # Test 4: Index request (if OpenAI key available)
        if os.getenv("OPENAI_API_KEY"):
            print("\n=== Testing Index ===")
            test_index(proc)

            # Test 5: List vector stores
            print("\n=== Testing List Vector Stores ===")
            test_list_vector_stores(proc)

            # Test 6: Query vector store (requires an existing store)
            print("\n=== Testing Query Vector Store ===")
            test_query_vector_store(proc)
        else:
            print("\n=== Skipping Index/List/Query Tests (no real OpenAI API key) ===")

    except Exception as e:
        print(f"Error during test: {e}")

    finally:
        # Clean up
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        # Print any stderr
        stderr = proc.stderr.read()
        if stderr:
            print(f"\nStderr: {stderr}")


def test_stats(proc):
    """Test cc_stats tool."""
    stats_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "cc_stats", "arguments": {"url_pattern": "%.example.com%"}},
    }

    print("Sending stats request:")
    print(json.dumps(stats_request, indent=2))
    proc.stdin.write(json.dumps(stats_request) + "\n")
    proc.stdin.flush()

    # Read stats response
    stats_response = proc.stdout.readline()
    print(f"Stats response: {stats_response.strip()}")

    # Try to parse and pretty print the response
    try:
        response_obj = json.loads(stats_response)
        if "result" in response_obj and "content" in response_obj["result"]:
            content = response_obj["result"]["content"]
            if content and len(content) > 0:
                print("\n=== Stats Results ===")
                result_text = content[0].get("text", "No text content")
                # Print just first few lines for brevity
                lines = result_text.split("\n")[:10]
                print("\n".join(lines))
                if len(result_text.split("\n")) > 10:
                    print("...")
    except json.JSONDecodeError:
        print("Could not parse JSON response")


def test_search(proc):
    """Test cc_search tool."""
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "cc_search",
            "arguments": {"url_pattern": "%.example.com%", "limit": 2},
        },
    }

    print("Sending search request:")
    print(json.dumps(search_request, indent=2))
    proc.stdin.write(json.dumps(search_request) + "\n")
    proc.stdin.flush()

    # Read search response
    search_response = proc.stdout.readline()
    print(f"Search response: {search_response.strip()}")

    # Try to parse and pretty print the response
    try:
        response_obj = json.loads(search_response)
        if "result" in response_obj and "content" in response_obj["result"]:
            content = response_obj["result"]["content"]
            if content and len(content) > 0:
                print("\n=== Search Results ===")
                result_text = content[0].get("text", "No text content")
                # Print just first few lines for brevity
                lines = result_text.split("\n")[:15]
                print("\n".join(lines))
                if len(result_text.split("\n")) > 15:
                    print("...")
    except json.JSONDecodeError:
        print("Could not parse JSON response")


def test_fetch(proc):
    """Test cc_fetch tool."""
    fetch_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "cc_fetch",
            "arguments": {
                "url_pattern": "%.example.com%",
                "limit": 1,
                "max_bytes": 200,
            },
        },
    }

    print("Sending fetch request:")
    print(json.dumps(fetch_request, indent=2))
    proc.stdin.write(json.dumps(fetch_request) + "\n")
    proc.stdin.flush()

    # Read fetch response
    fetch_response = proc.stdout.readline()
    print(f"Fetch response: {fetch_response.strip()}")

    # Try to parse and pretty print the response
    try:
        response_obj = json.loads(fetch_response)
        if "result" in response_obj and "content" in response_obj["result"]:
            content = response_obj["result"]["content"]
            if content and len(content) > 0:
                print("\n=== Fetch Results ===")
                result_text = content[0].get("text", "No text content")
                # Print just first few lines for brevity
                lines = result_text.split("\n")[:20]
                print("\n".join(lines))
                if len(result_text.split("\n")) > 20:
                    print("...")
    except json.JSONDecodeError:
        print("Could not parse JSON response")


def test_index(proc):
    """Test cc_index tool."""
    vector_store_name = f"mcp-test-{int(time.time())}"

    index_request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "cc_index",
            "arguments": {
                "url_pattern": "%.example.com%",
                "vector_store_name": vector_store_name,
                "limit": 1,
            },
        },
    }

    print("Sending index request:")
    print(json.dumps(index_request, indent=2))
    proc.stdin.write(json.dumps(index_request) + "\n")
    proc.stdin.flush()

    # Read index response
    index_response = proc.stdout.readline()
    print(f"Index response: {index_response.strip()}")

    # Try to parse and pretty print the response
    try:
        response_obj = json.loads(index_response)
        if "result" in response_obj and "content" in response_obj["result"]:
            content = response_obj["result"]["content"]
            if content and len(content) > 0:
                print("\n=== Index Results ===")
                result_text = content[0].get("text", "No text content")
                # Print just first few lines for brevity
                lines = result_text.split("\n")[:15]
                print("\n".join(lines))
                if len(result_text.split("\n")) > 15:
                    print("...")
    except json.JSONDecodeError:
        print("Could not parse JSON response")


def test_list_vector_stores(proc):
    """Test cc_list_vector_stores tool."""
    list_request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {"name": "cc_list_vector_stores", "arguments": {}},
    }

    print("Sending list vector stores request:")
    print(json.dumps(list_request, indent=2))
    proc.stdin.write(json.dumps(list_request) + "\n")
    proc.stdin.flush()

    # Read list response
    list_response = proc.stdout.readline()
    print(f"List response: {list_response.strip()}")


def test_query_vector_store(proc):
    """Test cc_query tool."""
    # Note: This would require an existing vector store ID
    query_request = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "cc_query",
            "arguments": {
                "query": "What is machine learning?",
                "vector_store_name": "test-store",
                "limit": 3,
            },
        },
    }

    print("Sending query request:")
    print(json.dumps(query_request, indent=2))
    proc.stdin.write(json.dumps(query_request) + "\n")
    proc.stdin.flush()

    # Read query response
    query_response = proc.stdout.readline()
    print(f"Query response: {query_response.strip()}")


if __name__ == "__main__":
    test_mcp_server()
