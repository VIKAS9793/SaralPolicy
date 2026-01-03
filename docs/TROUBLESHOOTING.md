# 🔧 Troubleshooting Guide

This document provides solutions to common issues encountered while setting up or running SaralPolicy.

---

## 🔊 Text-to-Speech (TTS) Issues

### Indic Parler-TTS Takes 5+ Minutes
**Symptoms:** Hindi TTS generation takes 5-10 minutes.
**Cause:** Neural TTS model (0.9B parameters) running on CPU.
**This is expected behavior.** Neural TTS on CPU is slow but produces high-quality audio.

**Solutions:**
1. **Use GPU (if available):**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```
2. **Use gTTS fallback:** Set `TTS_ENGINE=gtts` in `.env` for instant (lower quality) TTS
3. **Pre-generate audio:** For demos, generate audio in advance
4. **Accept the trade-off:** High-quality Hindi TTS on CPU is slow - this is normal

**Expected Times:**
| Hardware | ~100 chars | ~500 chars |
|----------|-----------|-----------|
| CPU | 2-5 min | 5-10 min |
| GPU (CUDA) | 5-15 sec | 15-45 sec |

### "prompt_attention_mask is specified but attention_mask is not"
**Symptoms:** Warning message during TTS generation.
**Cause:** Informational message from the model.
**Solution:** This is safe to ignore. The model handles it automatically.

### "HuggingFace token not configured"
**Symptoms:** TTS falls back to gTTS instead of Indic Parler-TTS.
**Solution:**
1. Get a token from https://huggingface.co/settings/tokens
2. Add to `backend/.env`:
   ```
   HF_TOKEN=hf_your_token_here
   ```
3. Restart the application

### "ffmpeg not found" Warning
**Symptoms:** MP3 conversion fails, falls back to WAV.
**Cause:** ffmpeg not installed on system.
**Solution:**
- **Windows:** `winget install ffmpeg` or download from https://ffmpeg.org
- **Linux:** `sudo apt install ffmpeg`
- **Mac:** `brew install ffmpeg`

---

## 🤖 Ollama & AI Model Issues

### "Ollama service not available" or Connection Refused
**Symptoms:** Application fails to start or crashes when analyzing; logs show connection errors.
**Cause:** Ollama background service is not running.
**Solution:**
Open a separate terminal and run:
```bash
ollama serve
```
Keep this terminal open.

### "Model gemma2:2b not found"
**Symptoms:** Error logs indicate model 404 or not found.
**Solution:**
```bash
ollama pull gemma2:2b
```
Verify installation:
```bash
ollama list
```

### Slow Analysis Speed
**Symptoms:** Document analysis takes >30 seconds.
**Cause:**
1. Running on CPU with limited RAM.
2. Large PDF size.
**Solutions:**
- Ensure you have at least 8GB RAM.
- Close other memory-intensive applications (browser tabs, IDEs).
- **Advanced:** Switch to a smaller model (e.g., `gemma:2b`) in `app/services/ollama_llm_service.py` if hardware is very limited.

---

## 📄 Document Processing Issues

### "Unsupported file format"
**Symptoms:** Upload fails immediately.
**Solution:** Only `.pdf`, `.docx`, and `.txt` files are supported. Ensure the file has the correct extension.

### "Main logic... moved to DocumentService"
**Symptoms:** You see this in strict logs or older traces.
**Solution:** This is a legacy artifact message. The system now uses `app/services/document_service.py`. Ensure you are running the latest `main.py`.

---

## 🐍 Python & Environment Issues

### "ModuleNotFoundError: No module named 'app'"
**Symptoms:** Running scripts directly fails.
**Cause:** Python path not set correctly.
**Solution:**
Run scripts as modules from the `backend` directory:
```bash
# Correct
python -m scripts.index_irdai_knowledge

# Or ensure PYTHONPATH includes backend
$env:PYTHONPATH="C:\path\to\backend"
python scripts/index_irdai_knowledge.py
```

### "Access Denied" when deleting files
**Symptoms:** Cleanup scripts fail.
**Cause:** Files are locked by a running python process or OS.
**Solution:** Stop all `python.exe` processes and try again.

---

## 🌐 Network & UI Issues

### "CORS Error" in Browser Console
**Symptoms:** Frontend loads but API calls fail.
**Cause:** Mismatch between frontend origin and backend allowed origins.
**Solution:** Check `app/dependencies.py` and ensure your localhost port (usually 8000) is in `allowed_origins`.

### UI Stuck on "Processing..."
**Symptoms:** Progress bar hangs indefinitely.
**Cause:** Backend error during RAG or LLM step.
**Solution:** Check the terminal running `python main.py` for traceback errors. Common causes include Ollama being down or memory overflows.

---

## 🐛 Still stuck?

1. **Check Logs:** The application uses structured logging. Check the console output.
2. **Run Tests:** `python -m pytest tests/` to isolate failing components.
3. **Open Issue:** Report on GitHub with your log output.
