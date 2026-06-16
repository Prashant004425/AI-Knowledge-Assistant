#!/usr/bin/env python
import sys
print("Python version:", sys.version)
print("Current working directory:", __file__)

try:
    print("Importing chromadb...")
    import chromadb
    print("✓ chromadb imported")
except ImportError as e:
    print("✗ Failed to import chromadb:", e)

try:
    print("Importing sentence_transformers...")
    import sentence_transformers
    print("✓ sentence_transformers imported")
except ImportError as e:
    print("✗ Failed to import sentence_transformers:", e)

print("Test complete")
