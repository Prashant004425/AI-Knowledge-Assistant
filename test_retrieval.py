import json
import logging
from pathlib import Path

# Configure logging to suppress HF Hub warnings
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

from core.retrieval.retrieve import search, format_results

BASE_DIR = Path.cwd()

print("=" * 70)
print("SEMANTIC SEARCH TEST - AI Knowledge Assistant")
print("=" * 70)

test_queries = [
    "What is FloCard?",
    "How do I authenticate?",
    "What are company policies?",
]

for query in test_queries:
    print(f"\n🔍 Query: {query}")
    print("-" * 70)
    
    try:
        results = search(query, n_results=2)
        
        print(f"✓ Found {results['num_results']} relevant chunks\n")
        
        for i, result in enumerate(results["results"], 1):
            print(f"  [{i}] Source: {result['source']}")
            print(f"      Similarity: {result['similarity']}")
            print(f"      ID: {result['id']}")
            print(f"      Text: {result['text'][:80]}...")
            print()
            
    except Exception as e:
        print(f"✗ Error: {e}\n")

print("=" * 70)
print("Test completed!")
print("=" * 70)
