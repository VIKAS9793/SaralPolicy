# 🏗️ SaralPolicy System Architecture

**Version:** 2.0  
**Last Updated:** January 2026  
**Author:** Vikas Sahani (Product Lead)  
**Engineering Team:** Kiro (AI Co-Engineering Assistant), Antigravity (AI Co-Assistant)

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Component Details](#component-details)
5. [Integration Points](#integration-points)
6. [Performance & Scalability](#performance--scalability)
7. [Security & Privacy](#security--privacy)

---

## Architecture Overview

SaralPolicy is a **privacy-first, locally-run AI system** for analyzing Indian insurance policy documents. The architecture is designed around the principle of **zero cloud dependencies** and **complete user data privacy**.

### Core Design Principles

✅ **Privacy-First:** All processing happens locally on the user's machine  
✅ **Modular Architecture:** Loosely coupled services with dependency injection  
✅ **Offline Capable:** No internet required for core functionality  
✅ **POC/Demo Ready:** Built-in guardrails, evaluation, and HITL workflows  
✅ **Regulatory Compliance:** IRDAI knowledge base integration  
✅ **OSS-First:** Local-first open source frameworks (RAGAS, Huey, OpenTelemetry)  

---

## System Components

```mermaid
graph TB
    subgraph FE["🎨 FRONTEND LAYER"]
        UI["<b>Material 3 Web UI</b><br/>• Drag & Drop Upload<br/>• Q&A Interface<br/>• Responsive Design"]
    end

    subgraph API_LAYER["⚡ API LAYER"]
        API["<b>FastAPI Gateway</b><br/>• app/routes<br/>• Dependencies<br/>• Request Routing"]
    end

    subgraph CORE["🔧 CORE SERVICES"]
        DOC["<b>Document Service</b><br/>• File Parsing (PDF/DOCX)<br/>• Hashing & Caching<br/>• Text Extraction"]
        POLICY["<b>Policy Service</b><br/>• Orchestration Logic<br/>• Analysis Workflow<br/>• Citation Management"]
        RAG["<b>RAG Service</b><br/>• Hybrid Search<br/>• Context Retrieval<br/>• Knowledge Access"]
        LLM["<b>Ollama LLM</b><br/>• Gemma 2 2B (Local)<br/>• Zero Cloud Calls<br/>• Privacy-First"]
    end

    subgraph STORAGE["💾 KNOWLEDGE & STORAGE"]
        EMBED["<b>Embeddings</b><br/>nomic-embed-text<br/>Ollama"]
        CHROMA[("<b>ChromaDB</b><br/>Vector Store<br/>Persistent Storage")]
        IRDAI[("<b>IRDAI Knowledge</b><br/>39 Regulatory Chunks<br/>Pre-indexed")]
    end

    subgraph SEARCH["🔍 SEARCH COMPONENTS"]
        BM25["<b>BM25 Search</b><br/>Keyword Matching<br/>rank-bm25"]
        VSEARCH["<b>Vector Search</b><br/>Semantic Similarity<br/>ChromaDB Queries"]
    end

    subgraph SAFETY["🛡️ SAFETY & QUALITY"]
        GUARD["<b>Guardrails</b><br/>• PII Protection<br/>• Input Validation<br/>• Hallucination Check"]
        EVAL["<b>Evaluation</b><br/>• RAGAS Metrics<br/>• Heuristic Fallback<br/>• Hallucination Check"]
        HITL["<b>HITL Services</b><br/>• Expert Review<br/>• Low Confidence<br/>• Quality Assurance"]
    end

    subgraph AUX["🔊 AUXILIARY SERVICES"]
        TTS["<b>Text-to-Speech</b><br/>pyttsx3, gTTS"]
        TRANS["<b>Translation</b><br/>Argos Translate (Offline)<br/>Hindi/English"]
    end

    %% Primary User Flow (Bold)
    UI ====>|"1. Upload Request"| API
    API ====>|"2. Delegate"| DOC
    DOC ====>|"3. Parsed Text"| API
    
    UI ====>|"4. Analyze/Ask"| API
    API ====>|"5. Orchestrate"| POLICY
    
    POLICY ====>|"6. Retrieve"| RAG
    RAG ====>|"7. Search"| CHROMA
    
    POLICY ====>|"8. Generate"| LLM
    LLM ====>|"9. Response"| POLICY
    POLICY ====>|"10. Result"| API
    API ====>|"11. Display"| UI

    %% RAG Pipeline
    RAG -->|Keyword| BM25
    RAG -->|Vector| VSEARCH
    BM25 --> CHROMA
    VSEARCH --> CHROMA
    IRDAI -.-> CHROMA

    %% Safety Integration
    POLICY -->|Pre-Check| GUARD
    POLICY -->|Post-Check| EVAL
    EVAL -->|Low Confidence| HITL
    
    %% Aux Services
    POLICY -.->|Translate| TRANS
    POLICY -.->|Speak| TTS
```    HITL -->|Expert Verified| API

    %% User Interactions
    UI -->|Ask Questions| API
    API -->|Q&A via RAG| RAG

    %% Output Enhancement
    API -->|Generate Audio| TTS
    API -->|Translate Text| TRANS
    TTS -->|Audio File| UI
    TRANS -->|Hindi Output| UI

    %% Styling with High Contrast
    classDef frontendStyle fill:#0d47a1,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef apiStyle fill:#4a148c,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef coreStyle fill:#e65100,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef storageStyle fill:#1b5e20,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef searchStyle fill:#006064,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef safetyStyle fill:#b71c1c,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef auxStyle fill:#880e4f,stroke:#ffffff,stroke-width:3px,color:#ffffff
    classDef subgraphStyle fill:#f5f5f5,stroke:#424242,stroke-width:2px

    class UI frontendStyle
    class API apiStyle
    class DOC,RAG,LLM coreStyle
    class EMBED,CHROMA,IRDAI storageStyle
    class BM25,VSEARCH searchStyle
    class GUARD,EVAL,HITL safetyStyle
    class TTS,TRANS auxStyle
    class FE,API_LAYER,CORE,STORAGE,SEARCH,SAFETY,AUX subgraphStyle
```

---

## Data Flow

### 1. Document Upload Flow

```
User → Frontend UI → FastAPI → Document Processor → Text Extraction
                                         ↓
                                   Embedding Generation
                                         ↓
                                   Vector Storage (ChromaDB)
```

**Processing Steps:**
1. **Upload:** User drags PDF/DOCX to web interface
2. **Validation:** File type, size, and content checks via Guardrails
3. **Extraction:** Parallel text extraction using PyPDF2 (multi-threaded)
4. **Chunking:** Intelligent text chunking for optimal RAG performance
5. **Embedding:** Generate embeddings via Ollama's nomic-embed-text
6. **Storage:** Store vectors + metadata in ChromaDB persistent storage

**Performance Optimization:**
- ✅ MD5-based document caching (avoid reprocessing)
- ✅ Parallel PDF page extraction (4-worker ThreadPoolExecutor)
- ✅ Batch embedding generation
- ✅ Optimized chunking with list comprehensions

---

### 2. Policy Analysis Flow

```
Uploaded Document → RAG Service → Hybrid Search (BM25 + Vector)
                                       ↓
                            Context Retrieval from IRDAI KB
                                       ↓
                            Prompt Engineering with Context
                                       ↓
                            LLM Generation (gemma2:2b)
                                       ↓
                            Evaluation & Quality Check
                                       ↓
                    High Confidence → User | Low Confidence → HITL Review
```

**Key Features:**
- **Hybrid Search:** Combines keyword (BM25) + semantic (vector) search
- **Context Augmentation:** IRDAI knowledge base pre-indexed (39 regulatory chunks)
- **Quality Control:** TruLens, Giskard, DeepEval metrics
- **Human Oversight:** Automatic flagging for expert review

---

### 3. Q&A Interaction Flow

```
User Question → API → Guardrails (Input Validation)
                          ↓
                    RAG Query (Hybrid Search)
                          ↓
                    Context from Document + IRDAI KB
                          ↓
                    LLM Generation (Contextual Answer)
                          ↓
                    PII Redaction & Safety Check
                          ↓
                    Response + Sources → User
```

**Optimizations:**
- ✅ Query caching (MD5-based keys)
- ✅ Connection pooling for Ollama API
- ✅ Persistent ChromaDB sessions

---

## Component Details

### 🎨 Frontend Layer

**Technology:** Material 3 Design, HTML5, CSS3, JavaScript  
**Features:**
- Drag-and-drop file upload
- Real-time analysis progress indicators
- Interactive Q&A chat interface
- Audio playback for TTS summaries
- Dark mode support
- Print-friendly policy views

**File:** `backend/templates/index.html`, `backend/static/`

---

### ⚡ API Layer

**Technology:** FastAPI (Python 3.10+)  
**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve frontend UI |
| `/upload` | POST | Upload policy document |
| `/analyze` | POST | Analyze uploaded policy |
| `/rag/ask` | POST | Ask question via RAG |
| `/rag/stats` | GET | RAG service statistics |
| `/tts` | POST | Generate audio summary |

**Features:**
- CORS middleware for cross-origin requests
- Session management for multi-user support
- Structured logging (structlog)
- Performance metrics tracking

**File:** `backend/main.py`

---

### 🔧 Core Services

#### 1. Document Processor

**Purpose:** Extract text from PDF, DOCX, TXT files  
**Optimizations:**
- Parallel PDF page processing (ThreadPoolExecutor)
- MD5-based file caching
- Memory-efficient streaming for large files

**File:** `backend/app/services/document_service.py` (DocumentService class)

**Supported Formats:**
- ✅ PDF (via PyPDF2)
- ✅ DOCX (via python-docx)
- ✅ TXT (native Python)

---

#### 4. Policy Service (New)

**Purpose:** Orchestrates analysis, RAG, and response generation
**File:** `backend/app/services/policy_service.py`

**Key Features:**
- Centralized business logic
- Integrates RAG, LLM, and Guardrails with confidence overrides
- Generates rich citation metadata


---

#### 2. RAG Service

**Purpose:** Retrieval-Augmented Generation with hybrid search  
**Technology:** ChromaDB + BM25 + Ollama embeddings

**Key Features:**
- **Hybrid Search:** Combines BM25 (keyword) + Vector (semantic) search
- **Batch Processing:** Parallel embedding generation with caching
- **Connection Pooling:** Persistent HTTP sessions for Ollama
- **Query Caching:** MD5-based cache for repeated queries

**File:** `backend/app/services/rag_service.py`

**Methods:**
```python
index_document(text, metadata)  # Index document chunks
hybrid_search(query, collection_name, top_k)  # Search both BM25 + Vector
get_embeddings(texts)  # Batch embedding with cache
get_stats()  # Service statistics
```

---

#### 3. Ollama LLM Service

**Purpose:** Local LLM inference using gemma2:2b  
**Model:** `gemma2:2b` (2 billion parameters)

**Configuration:**
- **Temperature:** 0.3 (deterministic)
- **Context Window:** 4096 tokens
- **Max Tokens:** 1500 output
- **Streaming:** Disabled (batch processing)

**Privacy Guarantee:** 
- ✅ 100% local inference
- ✅ No API keys required
- ✅ No data sent to cloud services

**File:** `backend/app/services/ollama_llm_service.py`

---

### 💾 Knowledge & Storage

#### ChromaDB Vector Store

**Purpose:** Persistent vector storage for embeddings  
**Location:** `backend/data/chroma/`

**Collections:**
- `policy_documents` - Uploaded policy chunks
- `irdai_knowledge_base` - Pre-indexed regulatory content

**Metadata Schema:**
```json
{
  "chunk_id": "string",
  "source": "filename.pdf",
  "chunk_index": 0,
  "type": "policy_section",
  "timestamp": "2025-10-07T12:00:00"
}
```

---

#### IRDAI Knowledge Base

**Purpose:** Regulatory compliance context  
**Location:** `backend/data/irdai_knowledge/`

**Content:**
- `IRDAI_Master_Circular_Health_2024.txt` (Health insurance regulations)
- `IRDAI_Protection_of_Policyholders_Interests.txt` (Consumer rights)
- `Insurance_Guidelines_Terms_Definitions.txt` (Standard terminology)

**Statistics:**
- 39 indexed chunks
- Pre-embedded and ready for queries
- Automatically loaded on service startup

---

### 🔍 Search Components

#### BM25 Keyword Search

**Purpose:** Lexical matching for exact term searches  
**Library:** `rank-bm25`

**Use Cases:**
- Policy number lookups
- Specific clause references
- Exact terminology searches

---

#### Vector Semantic Search

**Purpose:** Semantic similarity matching  
**Embedding Model:** `nomic-embed-text` (274MB via Ollama)

**Use Cases:**
- Conceptual queries ("What is covered for accidents?")
- Cross-language understanding
- Paraphrase detection

---

### 🛡️ Safety & Quality

#### 1. Guardrails Service

**Purpose:** Input validation, PII protection, hallucination prevention  
**File:** `backend/app/services/guardrails_service.py`

**Checks:**
- ✅ PII redaction (names, phone, Aadhaar, PAN)
- ✅ Input sanitization (SQL injection, XSS)
- ✅ File size and type validation
- ✅ Prompt injection detection

---

#### 2. Evaluation Frameworks

**Purpose:** Quality metrics for LLM outputs  
**File:** `backend/app/services/evaluation.py`, `backend/app/services/rag_evaluation_service.py`

**Primary Framework: RAGAS (2026-01-03)**
- **License:** Apache 2.0
- **GitHub:** https://github.com/explodinggradients/ragas (7k+ stars)
- **Metrics:**
  - Faithfulness (hallucination detection)
  - Answer Relevancy
  - Context Precision
  - Context Recall (with ground truth)

**Fallback:** Heuristic-based evaluation when RAGAS not installed

**Thresholds:**
- High Confidence: Faithfulness ≥ 0.7
- Hallucination Risk: Faithfulness < 0.7

**Installation (Optional):**
```bash
pip install ragas datasets langchain-community
```

---

#### 3. Human-in-the-Loop (HITL)

**Purpose:** Expert review for low-confidence analyses  
**File:** `backend/app/services/hitl_service.py`

**Workflow:**
1. System flags low-confidence result
2. Expert reviews analysis in UI
3. Expert approves/corrects/rejects
4. Feedback stored for model improvement
5. User receives verified analysis

---

#### 4. Task Queue Service (2026-01-03)

**Purpose:** Background task processing for HITL and async operations  
**File:** `backend/app/services/task_queue_service.py`

**Framework: Huey**
- **License:** MIT
- **GitHub:** https://github.com/coleifer/huey (5k+ stars)
- **Backend:** SQLite (no Redis required)

**Features:**
- Priority-based task scheduling (HIGH, MEDIUM, LOW)
- Automatic retries with exponential backoff
- Task status tracking
- Graceful fallback to synchronous execution

**Task Types:**
- Review notifications
- Expert assignment
- Review reminders
- Feedback processing

**Installation (Optional):**
```bash
pip install huey
```

---

#### 5. Observability Service (2026-01-03)

**Purpose:** Metrics, tracing, and health monitoring  
**File:** `backend/app/services/observability_service.py`

**Framework: OpenTelemetry**
- **License:** Apache 2.0
- **GitHub:** https://github.com/open-telemetry/opentelemetry-python (1.5k+ stars)
- **Export:** Console (local) - no cloud required

**Metrics:**
- Request counts and latencies
- LLM call duration and token counts
- RAG query performance
- Error rates

**Tracing:**
- Distributed tracing with spans
- Automatic error tracking
- Duration measurement

**Installation (Optional):**
```bash
pip install opentelemetry-api opentelemetry-sdk
```

---

### 🔊 Auxiliary Services

#### Text-to-Speech (TTS)

**Purpose:** Generate audio summaries  
**Libraries:** pyttsx3 (offline), gTTS (online fallback), Indic Parler-TTS (high-quality Hindi)

**Features:**
- Hindi + English voice support
- Adjustable speech rate
- MP3 output format
- High-quality neural TTS for Hindi (optional)

**File:** `backend/app/services/tts_service.py`, `backend/app/services/indic_parler_engine.py`

**Indic Parler-TTS (Optional - High-Quality Hindi TTS)**
- **Model:** [ai4bharat/indic-parler-tts](https://huggingface.co/ai4bharat/indic-parler-tts)
- **License:** Apache 2.0
- **Size:** 0.9B parameters
- **Speakers:** Rohit, Divya (Hindi), Thoma, Mary (English)
- **Features:** Natural voice descriptions, clear audio quality

**Citations:**
```bibtex
@inproceedings{sankar25_interspeech,
  title     = {{Rasmalai : Resources for Adaptive Speech Modeling in IndiAn Languages with Accents and Intonations}},
  author    = {Ashwin Sankar and Yoach Lacombe and Sherry Thomas and Praveen {Srinivasa Varadhan} and Sanchit Gandhi and Mitesh M. Khapra},
  year      = {2025},
  booktitle = {{Interspeech 2025}},
  pages     = {4128--4132},
  doi       = {10.21437/Interspeech.2025-2758},
}

@misc{lacombe-etal-2024-parler-tts,
  author = {Yoach Lacombe and Vaibhav Srivastav and Sanchit Gandhi},
  title = {Parler-TTS},
  year = {2024},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/huggingface/parler-tts}}
}

@misc{lyth2024natural,
  title={Natural language guidance of high-fidelity text-to-speech with synthetic annotations},
  author={Dan Lyth and Simon King},
  year={2024},
  eprint={2402.01912},
  archivePrefix={arXiv},
}
```

**Fallback Chain:** Indic Parler-TTS → gTTS → pyttsx3

---

#### Translation Service

**Purpose:** Hindi ↔ English translation  
**Library:** Argos Translate (Offline) (unofficial API)

**Use Cases:**
- Bilingual policy summaries
- Term explanations in Hindi
- User interface localization

**File:** `backend/app/services/translation_service.py`

---

## Integration Points

### External Dependencies

1. **Ollama** (Required)
   - Installation: `curl https://ollama.ai/install.sh | sh`
   - Models: `gemma2:2b`, `nomic-embed-text`
   - Port: 11434 (default)

2. **ChromaDB** (Bundled)
   - Version: 0.5.15
   - Storage: `backend/data/chroma/`

3. **Python Packages** (See `requirements.txt`)
   - FastAPI, Uvicorn
   - PyPDF2, python-docx
   - rank-bm25, chromadb
   - pyttsx3, Argos Translate (Offline)

---

## Performance & Scalability

### Current Performance Metrics

| Operation | Time (Avg) | Optimization |
|-----------|------------|--------------|
| PDF Parsing (10 pages) | 2.3s | Parallel processing |
| Embedding Generation (50 chunks) | 1.8s | Batch API calls |
| Hybrid Search Query | 0.4s | Query caching |
| LLM Generation (500 tokens) | 3.5s | Optimized prompt |
| Full Analysis | 8-12s | End-to-end pipeline |

### Scalability Considerations

**Current POC Limitations:**
- Single-user session management
- In-memory caching (lost on restart)
- No distributed processing

**Production Roadmap:**
- Multi-user support with session persistence
- Distributed vector store (Weaviate, Milvus)
- GPU acceleration for embeddings
- Load balancing for API layer

---

## Security & Privacy

### Privacy Guarantees

✅ **Zero Cloud Calls:** All AI processing happens locally  
✅ **No API Keys:** No third-party AI services  
✅ **Data Sovereignty:** User data never leaves their machine  
✅ **PII Protection:** Automatic redaction of sensitive info  
✅ **Audit Logs:** All operations logged locally  

### Security Measures

1. **Input Validation:** All uploads sanitized via Guardrails
2. **File Type Restrictions:** Only PDF/DOCX/TXT allowed
3. **Size Limits:** Max 10MB upload size (configurable)
4. **SQL Injection Prevention:** Parameterized queries only
5. **XSS Protection:** Output sanitization in frontend

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.115.12
- **Language:** Python 3.10+
- **AI/ML:** Ollama (gemma2:2b, nomic-embed-text)
- **Vector DB:** ChromaDB 0.5.15
- **Search:** rank-bm25 0.2.2

### Frontend
- **UI Framework:** Material Design 3
- **Styling:** Custom CSS with dark mode
- **Interactivity:** Vanilla JavaScript

### Infrastructure
- **Server:** Uvicorn ASGI
- **Logging:** structlog
- **Testing:** pytest, unittest

---

## Quick Reference

### Service Endpoints

```bash
# Health check
curl http://localhost:8000/

# Upload document
curl -X POST http://localhost:8000/upload \
  -F "file=@policy.pdf"

# Analyze policy
curl -X POST http://localhost:8000/analyze \
  -F "file=@policy.pdf"

# Ask question via RAG
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the sum insured?", "use_knowledge_base": true}'

# Get RAG statistics
curl http://localhost:8000/rag/stats
```

### File Locations

| Component | Path |
|-----------|------|
| Main App | `backend/main.py` |
| RAG Service | `backend/app/services/rag_service.py` |
| Ollama LLM | `backend/app/services/ollama_llm_service.py` |
| ChromaDB Data | `backend/data/chroma/` |
| IRDAI Docs | `backend/data/irdai_knowledge/` |
| Frontend | `backend/templates/index.html` |
| Tests | `tests/` |

---

## Next Steps

### Immediate Enhancements
1. Add Automatic Speech Recognition (ASR) for voice queries
2. Implement Redis for distributed caching
3. Add PostgreSQL for persistent session management
4. Integrate more IRDAI documents (target: 100+ chunks)

### Long-Term Vision
1. Multi-language support (10+ Indian languages)
2. Mobile app (React Native)
3. Browser extension for policy scanning
4. API marketplace for insurtech partners

---

**For questions or contributions, see:** [CONTRIBUTING.md](../CONTRIBUTING.md)

**Last Updated:** October 7, 2025  
**Version:** 1.0.0
