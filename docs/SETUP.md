# 🛠️ SaralPolicy Setup Guide

This guide covers the complete setup process for SaralPolicy, including environment configuration, dependency installation, and local AI setup.

## 📋 Prerequisites

- **OS**: Windows, Linux, or macOS
- **Python**: 3.9 or higher
- **RAM**: Minimum 8GB (16GB recommended for optimal performance)
- **Disk Space**: ~10GB (for models and virtual environment)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/VIKAS9793/SaralPolicy.git
cd SaralPolicy
```

### 2. Environment Setup

Create and activate a virtual environment to keep dependencies isolated.

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Local AI Setup (Ollama)

SaralPolicy uses **Ollama** for privacy-first, local AI processing.

> **Detailed Guide:** See [Ollama Setup Guide](setup/OLLAMA_SETUP.md) for full instructions.

**Summary:**
1. [Download Ollama](https://ollama.ai/download)
2. Pull the required model:
   ```bash
   ollama pull gemma2:2b
   ```
3. Pull the embedding model:
   ```bash
   ollama pull nomic-embed-text
   ```
4. Start the server (keep running in background):
   ```bash
   ollama serve
   ```

### 5. Environment Configuration (Optional)

For high-quality Hindi TTS using Indic Parler-TTS:

```bash
# Copy environment template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

Edit `backend/.env` and add your HuggingFace token:
```
HF_TOKEN=hf_your_token_here
```

Get a token from: https://huggingface.co/settings/tokens

> **Note:** This is optional. Without the token, TTS falls back to gTTS (instant but lower quality).

### 6. Initialize Knowledge Base

Index the IRDAI regulatory documents into the local vector database.

```bash
# Ensure you are in the 'backend' directory
python scripts/index_irdai_knowledge.py
```

### 7. Run Application

```bash
python main.py
```

Visit `http://localhost:8000` in your browser.

---

## 🔊 Optional: High-Quality Hindi TTS

SaralPolicy supports Indic Parler-TTS for high-quality Hindi speech synthesis.

### Requirements
- HuggingFace token (free)
- ~4GB RAM during inference
- ~2GB disk for model cache

### Setup
1. Get token from https://huggingface.co/settings/tokens
2. Add to `backend/.env`:
   ```
   HF_TOKEN=hf_your_token_here
   ```

### Performance Notes
- **CPU:** 2-5 minutes per generation (expected)
- **GPU (CUDA):** 5-15 seconds per generation
- Falls back to gTTS automatically if unavailable

---

## 🧪 Verifying Installation

To ensure everything is working correctly, you can run the integration tests:

```bash
python -m pytest tests/test_rag_citations.py
python -m pytest tests/test_translation_offline.py
```

## 📝 Configuration

Configuration is managed via environment variables and `main.py` constants.

- **Port**: Default `8000`. Change in `main.py`.
- **Allowed Origins**: Configured in `app/dependencies.py`.
- **Ollama Host**: Default `localhost:11434`.

See [System Architecture](../SYSTEM_ARCHITECTURE.md) for deeper technical details.
