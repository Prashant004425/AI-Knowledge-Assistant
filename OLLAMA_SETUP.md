# Ollama Setup Guide

Ollama is a lightweight framework for running large language models locally. It's required for Phase 7 (RAG Pipeline).

## Installation

### Windows

1. **Download Ollama**
   - Visit: https://ollama.ai
   - Click "Download"
   - Select "Windows"
   - Download the installer

2. **Install**
   - Run the downloaded `.exe` file
   - Follow the installation wizard
   - Ollama will be installed in `C:\Users\<YourName>\AppData\Local\Programs\Ollama`

3. **Verify Installation**
   ```bash
   ollama --version
   # Output: ollama version X.X.X
   ```

### macOS

```bash
# Download and install via Homebrew
brew install ollama

# Or download from https://ollama.ai
```

### Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

---

## Running Ollama

### Start the Service

Open a terminal and run:

```bash
ollama serve
```

**Expected Output:**
```
2026-05-29 12:00:00 INFO Listening on http://localhost:11434
```

The Ollama API will be available at: `http://localhost:11434`

**Keep this terminal window open.** It will continue running in the background.

### Download a Model

In a **new terminal**, pull the Llama 3.1 model:

```bash
ollama pull llama3.1
```

**Expected Output:**
```
pulling manifest
pulling 9f438cb83e99
pulling d00ed0ee0a7c
pulling ...
success
```

**Download Size:** ~4.7 GB  
**First Run Duration:** 5-15 minutes (depends on internet speed)

### Alternative Models

If you want a smaller/faster model:

```bash
# Smaller models
ollama pull mistral         # ~4.0 GB
ollama pull neural-chat     # ~4.8 GB
ollama pull dolphin-mix     # ~3.5 GB

# List available models
ollama list
```

---

## Verify Installation

Test the Ollama API:

### Using curl (Windows PowerShell)

```powershell
curl.exe -X POST http://localhost:11434/api/generate -d @{
    model = "llama3.1"
    prompt = "What is artificial intelligence?"
    stream = $false
} | ConvertFrom-Json
```

### Using curl (Mac/Linux)

```bash
curl -X POST http://localhost:11434/api/generate -d '{
  "model": "llama3.1",
  "prompt": "What is artificial intelligence?",
  "stream": false
}'
```

### Using Python

```python
import requests
import json

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.1",
        "prompt": "What is artificial intelligence?",
        "stream": False
    }
)

result = response.json()
print(result["response"])
```

---

## Running the RAG Pipeline

Once Ollama is running and the model is pulled:

```bash
# In a new terminal (keep Ollama running in the other terminal)
cd ai-knowledge-assistant

# Test RAG pipeline with examples
python core/rag/generate.py
```

**Output:**
```
======================================================================
RAG PIPELINE DEMO - AI Knowledge Assistant
======================================================================
Using model: llama3.1
Ollama endpoint: http://localhost:11434/api/generate

❓ Question: What is FloCard?
💬 Answer: FloCard is an internal payment platform used for...
📚 Sources (2 cited):
  [1] flocard_api_guide.md (relevance: 84.56%)
  [2] payments_guide.md (relevance: 72.34%)
🔧 Model: llama3.1
📊 Context chunks: 3
```

---

## Usage in Your Code

```python
from core.rag.generate import generate_answer, format_response

# Generate an answer
result = generate_answer("What is FloCard?")

# Display formatted response
if result:
    print(format_response(result))
else:
    print("Failed to generate answer. Is Ollama running?")
```

---

## Troubleshooting

### Issue: "Failed to connect to Ollama at http://localhost:11434"

**Solution:**
1. Ensure Ollama is running: `ollama serve`
2. Check if port 11434 is not blocked by firewall
3. Verify endpoint: `curl http://localhost:11434/api/tags`

### Issue: "model 'llama3.1' not found"

**Solution:**
```bash
ollama pull llama3.1
```

### Issue: Out of Memory / Very Slow

**Solution:**
1. Use a smaller model:
   ```bash
   ollama pull mistral
   ```

2. Or limit context:
   ```python
   generate_answer("Question?", n_retrieve=2)
   ```

### Issue: Ollama doesn't start

**Solution:**
- Windows: Check System Settings > Apps for Ollama, reinstall if needed
- Mac/Linux: Check permissions, reinstall with appropriate privileges

### Issue: Port 11434 already in use

**Solution:**
```bash
# Find process using port 11434 and kill it
# Then restart Ollama on a different port (advanced usage)
```

---

## Performance Tips

1. **Keep Ollama running**: The first request after startup will download the model from cache (~30s). Subsequent requests are faster (~10-30s).

2. **Use smaller models for speed**:
   ```python
   generate_answer("Question?", model="mistral")
   ```

3. **Reduce context for faster generation**:
   ```python
   generate_answer("Question?", n_retrieve=2)
   ```

4. **Lower temperature for faster, deterministic output**:
   ```python
   generate_answer("Question?", temperature=0.1)
   ```

---

## Resource Requirements

- **Disk Space**: ~5 GB per model
- **RAM**: 8GB minimum (16GB recommended)
- **Internet**: Required for first model download
- **CPU**: Modern multi-core processor

---

## Using Remote Ollama

If you have Ollama running on another machine:

```python
from core.rag.generate import generate_answer

result = generate_answer(
    question="What is FloCard?",
    ollama_url="http://remote-machine:11434/api/generate"
)
```

---

## Advanced: GPU Support

Ollama automatically uses GPU if available:
- **NVIDIA**: CUDA support
- **AMD**: ROCm support
- **CPU**: Fallback (slower)

Check GPU usage:
```bash
ollama list
# GPU support info shown here
```

---

## Stopping Ollama

Press `Ctrl+C` in the terminal where you ran `ollama serve`.

---

## Documentation

- Ollama Docs: https://ollama.ai/docs
- Available Models: https://ollama.ai/library
- API Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md

---

## Next Steps

Once Ollama is running:

1. ✅ Start Ollama service: `ollama serve`
2. ✅ Pull model: `ollama pull llama3.1`
3. ✅ Verify: `curl http://localhost:11434/api/tags`
4. ✅ Run RAG pipeline: `python core/rag/generate.py`
5. ✅ Integrate into your app (Phase 8: API)
