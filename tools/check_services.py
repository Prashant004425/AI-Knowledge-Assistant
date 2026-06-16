import requests
import sys
from core.retrieval import retrieve

print('Checking Ollama...')
try:
    r = requests.get('http://localhost:11434/api/tags', timeout=3)
    print('Ollama HTTP status:', r.status_code)
    try:
        print('Ollama response sample:', r.json())
    except Exception:
        print('Ollama response text:', r.text[:200])
except Exception as e:
    print('Ollama check failed:', e)

print('\nChecking retrieval/search...')
try:
    res = retrieve.search('What is FloCard?', n_results=3)
    print('Search succeeded. num_results=', res.get('num_results'))
    for idx, r in enumerate(res.get('results', []), 1):
        print(f"{idx}. {r['source']} (sim={r['similarity']})")
except Exception as e:
    print('Search failed:', e)
    sys.exit(1)

print('\nAttempting full RAG generate...')
from core.rag.generate import generate_answer
try:
    out = generate_answer('What is FloCard?', n_retrieve=3)
    if out is None:
        print('generate_answer returned None (LLM or other failure)')
    else:
        print('generate_answer OK: answer length=', len(out.get('answer','')))
except Exception as e:
    print('generate_answer raised:', e)
    sys.exit(1)
