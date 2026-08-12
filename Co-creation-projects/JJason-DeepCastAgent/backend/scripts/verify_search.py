import os
import sys

from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from config import Configuration
from services.search import get_global_search_tool


def test_search_configuration():
    print("Testing search configuration...")
    
    # Load config from env
    config = Configuration.from_env()
    
    # Print loaded keys (masked)
    tavily_key = config.tavily_api_key
    serpapi_key = config.serpapi_api_key
    
    print(f"Tavily Key: {'*' * 8 + tavily_key[-4:] if tavily_key else 'None'}")
    print(f"SerpApi Key: {'*' * 8 + serpapi_key[-4:] if serpapi_key else 'None'}")
    print(f"Search API: {config.search_api}")
    
    # Initialize search tool
    search_tool = get_global_search_tool(config)
    print(f"Search Tool Backend: {search_tool.backend}")
    print(f"Available Backends: {search_tool.available_backends}")
    
    if not search_tool.available_backends:
        print("❌ No search backends available. Please check API keys.")
        return

    # Test search
    query = "DeepSeek technology overview"
    print(f"\nRunning search for: '{query}'...")
    
    try:
        response = search_tool.run({
            "input": query,
            "backend": "hybrid",
            "max_results": 2
        })
        
        if isinstance(response, dict):
            backend = response.get("backend", "unknown")
            results = response.get("results", [])
            print(f"✅ Search successful using backend: {backend}")
            print(f"Found {len(results)} results:")
            for i, res in enumerate(results, 1):
                print(f"  {i}. {res.get('title')} ({res.get('url')})")
        else:
            print(f"❌ Unexpected response format: {type(response)}")
            print(response)
            
    except Exception as e:
        print(f"❌ Search failed: {e}")

if __name__ == "__main__":
    test_search_configuration()
