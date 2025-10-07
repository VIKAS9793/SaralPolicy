# Ollama Setup Guide for SaralPolicy

## Overview
SaralPolicy now uses **Ollama** with **Gemma 3 4B** model for complete local AI processing. No HuggingFace or cloud dependencies required!

## Why Ollama + Gemma 3 4B?
- ✅ **100% Local**: Everything runs on your machine
- ✅ **No API Keys**: No cloud services, complete privacy
- ✅ **Fast & Efficient**: Gemma 3 4B is optimized for speed
- ✅ **IRDAI Compliant**: Insurance-specific knowledge built-in
- ✅ **Easy to Use**: Simple API, no complex dependencies

---

## Installation Steps

### 1. Install Ollama

**Windows:**
```powershell
# Download from official site
# Visit: https://ollama.ai/download
# Run the installer
```

**Verify Installation:**
```powershell
ollama --version
```

### 2. Pull Gemma 3 4B Model
```powershell
ollama pull gemma3:4b
```

This will download the Gemma 3 4B model (~3.3GB). First-time download takes a few minutes.

### 3. Start Ollama Service
```powershell
ollama serve
```

Keep this terminal window open while using SaralPolicy.

---

## Usage

### Start SaralPolicy

1. **Ensure Ollama is running:**
   ```powershell
   ollama serve
   ```

2. **In a new terminal, activate venv and start app:**
   ```powershell
   cd C:\Users\vikas\Downloads\SaralPolicy\backend
   ..\venv\Scripts\Activate.ps1
   python main.py
   ```

3. **Access the app:**
   ```
   http://localhost:8000
   ```

---

## Verify Setup

### Check Ollama Status
```powershell
# List available models
ollama list

# Test the model
ollama run gemma3:4b
```

### Test SaralPolicy Integration
Upload a sample insurance policy document and check:
- ✅ Model shows as "Gemma 3 4B (Ollama)"
- ✅ Analysis completes successfully
- ✅ No HuggingFace warnings in logs

---

## Troubleshooting

### Issue: "Ollama service not available"
**Solution:**
```powershell
# Start Ollama service
ollama serve
```

### Issue: "Model gemma3:4b not found"
**Solution:**
```powershell
# Pull the model
ollama pull gemma3:4b

# Verify it's installed
ollama list
```

### Issue: Slow performance
**Solutions:**
- Ensure you have at least 8GB RAM
- Close other heavy applications
- Consider using a smaller model: `ollama pull gemma3:2b`
- Update model in `main.py`: `OllamaLLMService(model_name="gemma3:2b")`

### Issue: Connection refused
**Check:**
1. Ollama is running: `ollama serve`
2. Port 11434 is not blocked
3. Try: `curl http://localhost:11434/api/tags`

---

## Advanced Configuration

### Change Model
Edit `backend/main.py`:
```python
ollama_service = OllamaLLMService(model_name="gemma3:4b")
```

Available models:
- `gemma3:4b` - Recommended (balanced)
- `gemma3:2b` - Faster, lower RAM
- `llama3:8b` - More powerful, needs more RAM
- `mistral` - Alternative option

### Change Ollama Host
If running Ollama on a different machine:
```python
ollama_service = OllamaLLMService(
    model_name="gemma3:4b",
    ollama_host="http://192.168.1.100:11434"
)
```

### Adjust Response Temperature
Edit `backend/app/services/ollama_llm_service.py`:
```python
"options": {
    "temperature": 0.3,  # Lower = more focused, Higher = more creative
    "num_predict": 2000
}
```

---

## Model Comparison

| Model | Size | RAM Required | Speed | Quality |
|-------|------|--------------|-------|---------|
| gemma3:2b | ~1.5GB | 4GB+ | Fast | Good |
| **gemma3:4b** | ~3.3GB | 8GB+ | Balanced | **Excellent** |
| llama3:8b | ~4.7GB | 16GB+ | Slower | Best |

---

## Benefits Over HuggingFace

| Feature | Ollama | HuggingFace |
|---------|--------|-------------|
| Installation | Simple | Complex |
| Dependencies | Minimal | 20+ packages |
| Model Loading | Fast | Slow |
| Memory Usage | Optimized | High |
| API | Clean REST | Transformers library |
| Updates | `ollama pull` | pip upgrade + model redownload |

---

## Performance Tips

1. **First Run**: Model loads into memory (10-20 seconds)
2. **Subsequent Runs**: Fast responses (~2-5 seconds)
3. **Warm-up**: First query after idle might be slower
4. **Concurrent Requests**: Ollama handles queuing automatically

---

## Resources

- **Ollama Website**: https://ollama.ai
- **Ollama GitHub**: https://github.com/ollama/ollama
- **Gemma Models**: https://ai.google.dev/gemma
- **Model Library**: https://ollama.ai/library

---

## Support

For issues specific to:
- **Ollama**: Check Ollama GitHub issues
- **SaralPolicy**: Check project documentation
- **Gemma Model**: Check Google AI documentation

---

**Status**: ✅ Production Ready with Ollama + Gemma 3 4B
