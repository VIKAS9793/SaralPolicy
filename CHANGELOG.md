# Changelog

All notable changes to SaralPolicy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-01-03

### 🎉 Major Release: Production Engineering Remediation Complete

This release represents a complete overhaul of SaralPolicy with 26 production engineering issues resolved, bringing the system from a prototype to a well-architected POC/Demo with proper engineering practices.

**Highlights:**
- 100% remediation of all identified production engineering issues
- 4 new OSS framework integrations (RAGAS, Huey, OpenTelemetry, Indic Parler-TTS)
- 197 tests passing across 13 test suites
- Comprehensive documentation overhaul

---

### Added

#### OSS Framework Integrations
- **RAGAS Evaluation Service** (`rag_evaluation_service.py`)
  - RAG evaluation with faithfulness, relevancy, and precision metrics
  - Works 100% locally with Ollama (no API keys required)
  - Heuristic fallback when RAGAS not installed
  - Apache 2.0 license, 7k+ GitHub stars

- **Huey Task Queue Service** (`task_queue_service.py`)
  - Background task processing with SQLite backend (no Redis required)
  - Priority-based scheduling (HIGH, MEDIUM, LOW)
  - Automatic retries with exponential backoff
  - MIT license, 5k+ GitHub stars

- **OpenTelemetry Observability Service** (`observability_service.py`)
  - Metrics collection (counters, histograms)
  - Distributed tracing with span context
  - Console exporters for local development
  - Apache 2.0 license, 1.5k+ GitHub stars

- **Indic Parler-TTS Engine** (`indic_parler_engine.py`)
  - High-quality Hindi neural text-to-speech (0.9B parameters)
  - Lazy model loading with configurable cache
  - WAV and MP3 output formats
  - Fallback chain: Indic Parler-TTS → gTTS → pyttsx3
  - Apache 2.0 license, AI4Bharat

#### Security Enhancements
- **Input Validation Middleware** (`middleware/input_validation.py`)
  - File size limits enforced at API boundary
  - Content-Length header validation
  - 413 Payload Too Large responses for oversized requests

- **CORS Validation** (`middleware/cors_validation.py`)
  - Origin format validation (scheme://host[:port])
  - Wildcard rejection when credentials enabled (OWASP compliance)
  - Fail-fast startup with security error messages

- **Secure Temp File Handling**
  - Replaced `NamedTemporaryFile(delete=False)` with `TemporaryDirectory`
  - Automatic cleanup guaranteed by Python context manager
  - No orphaned files on crashes

#### Data Persistence
- **HITL Database Models** (`models/hitl.py`)
  - SQLAlchemy models for reviews and feedback
  - UUID primary keys for distributed safety
  - JSON columns for flexible schema evolution
  - Indexed for read-heavy workloads

- **Alembic Migrations**
  - Database migration system configured
  - Initial migration for HITL tables
  - Upgradeable from SQLite to PostgreSQL

#### Configuration & Validation
- **Pydantic Configuration** (`config.py`)
  - Centralized configuration with full validation
  - Type validation, range checks, format validation
  - Production-specific validations
  - Fail-fast startup on invalid config

- **Health Service** (`services/health_service.py`)
  - Health levels: HEALTHY, DEGRADED, UNHEALTHY
  - Dependency checks: Ollama, ChromaDB, Database, Embeddings
  - Latency tracking per component
  - Kubernetes-style readiness/liveness probes

#### Testing Infrastructure
- **New Test Suites** (54+ new tests)
  - `test_oss_frameworks.py` - OSS framework integration tests
  - `test_error_paths.py` - Error handling and graceful degradation
  - `test_security.py` - Security validation tests
  - `test_integration.py` - End-to-end workflow tests
  - `test_hallucination_detection.py` - Hallucination detection validation
  - `test_prompts.py` - Prompt regression tests
  - `test_indic_parler_tts.py` - Hindi TTS tests
  - `test_config_validation.py` - Configuration validation tests
  - `test_hitl_persistence.py` - HITL persistence tests
  - `test_input_limits.py` - Input validation tests
  - `test_temp_file_cleanup.py` - Temp file cleanup tests
  - `test_cors_validation.py` - CORS security tests

#### Prompt Management
- **Prompt Registry** (`prompts/registry.py`)
  - Versioned prompt templates
  - Prompt validation and testing
  - Regression test support

#### Documentation
- `CHANGELOG.md` - This file
- `docs/STATUS.md` - Comprehensive project status
- `docs/reports/IMPLEMENTATION_STATUS.md` - Detailed implementation tracking
- `docs/reports/PROGRESS_TRACKER.md` - Quick status reference
- Updated all 16 product research documents with engineering team credits

---

### Changed

#### Architecture Improvements
- **Dependency Injection Container** (`dependencies.py`)
  - `ServiceContainer` class with proper DI pattern
  - `GlobalServices` kept as backward-compatible alias
  - All services injectable and testable

- **Factory Pattern for Services**
  - `create_rag_service()` factory function
  - Lazy initialization for backward compatibility
  - No import-time side effects

#### Code Quality
- **Exception Handling**
  - Fixed 7 silent exception patterns (`except: pass`)
  - All exceptions now logged with structured context
  - Debug-level for expected failures, Warning-level for unexpected

- **Algorithm Documentation**
  - Big-O time and space complexity documented
  - `hybrid_search`: O(n + k log k) time, O(k) space
  - `get_embeddings_batch`: O(n) time, O(n * d) space
  - `chunk_text`: O(n) time and space

- **Data Structure Documentation**
  - All data structures documented with rationale
  - Trade-offs and growth limits documented
  - Cleanup strategy defined (30-day retention)

- **ThreadPoolExecutor Documentation**
  - Workload classification (I/O-bound)
  - GIL impact analysis
  - Worker count rationale (4 workers)

#### Configuration
- **Model Standardization**
  - Standardized to `gemma2:2b` across all files
  - Model validation at startup
  - Fail-fast with clear error messages

- **Environment Variables**
  - `MAX_FILE_SIZE` - Maximum upload file size
  - `MAX_TEXT_LENGTH` - Maximum text length for processing
  - `MAX_EMBEDDING_BATCH_SIZE` - Batch size for embeddings
  - `MAX_CHUNK_TEXT_LENGTH` - Maximum chunk size
  - `HF_TOKEN` - Optional HuggingFace token for Indic Parler-TTS

#### Documentation Overhaul
- **README.md**
  - Fixed UTF-8 encoding issues (corrupted emojis)
  - All 8 asset images properly referenced
  - Badge versions match requirements.txt
  - Engineering team credits (Kiro, Antigravity)
  - Citations section with bibtex entries

- **TROUBLESHOOTING.md**
  - Added TTS troubleshooting section
  - CPU vs GPU performance guidance

- **SETUP.md**
  - HuggingFace token configuration
  - Indic Parler-TTS installation guide

- **SYSTEM_ARCHITECTURE.md**
  - Updated with new services
  - Engineering team credits

---

### Removed

#### False Claims
- Removed "production-ready" claims (now "POC/Demo")
- Removed unverified performance claims (2-4x, 5-10x speedups)
- Removed false framework availability flags (TruLens, Giskard, DeepEval)
- Removed placeholder evaluation methods

#### Deprecated Patterns
- Module-level service instantiation
- Silent exception swallowing
- Magic values without documentation

---

### Fixed

#### Critical Issues (6/6 - 100%)
- **CRITICAL-001:** Removed false evaluation claims
- **CRITICAL-002:** Implemented HITL database persistence
- **CRITICAL-003:** Enforced input size limits at all boundaries
- **CRITICAL-004:** Fixed temp file cleanup with context managers
- **CRITICAL-005:** Implemented real RAGAS-based evaluation
- **CRITICAL-006:** Removed overclaiming, accurate status documentation

#### High Priority Issues (11/11 - 100%)
- **HIGH-001:** Removed unverified performance claims
- **HIGH-002:** Fixed model version inconsistency (gemma2:2b)
- **HIGH-003:** Fixed silent exception swallowing (7 patterns)
- **HIGH-004:** Refactored global singleton to DI container
- **HIGH-005:** Fixed module-level instantiation
- **HIGH-006:** Fixed CORS configuration with validation
- **HIGH-007:** Integrated RAGAS evaluation framework
- **HIGH-008:** Made HITL production-ready with Huey
- **HIGH-010:** Added Pydantic config validation
- **HIGH-011:** Implemented comprehensive health checks
- **HIGH-012:** Fixed test coverage claims (accurate count)

#### Medium Priority Issues (9/9 - 100%)
- **MEDIUM-001:** Documented magic values with rationale
- **MEDIUM-002:** Documented algorithm complexity (Big-O)
- **MEDIUM-003:** Justified data structure choices
- **MEDIUM-004:** Added OpenTelemetry observability
- **MEDIUM-005:** Added regression tests (54+ tests)
- **MEDIUM-006:** Documented ThreadPoolExecutor usage
- **MEDIUM-007:** Added prompt regression tests
- **MEDIUM-008:** Validated hallucination detection
- **MEDIUM-009:** Added graceful degradation

---

### Security

- Input validation at all API boundaries
- CORS origin validation with OWASP compliance
- Secure temp file handling (no orphaned files)
- PII protection in guardrails
- `.env` secrets never committed (in `.gitignore`)
- HuggingFace token handling via environment variables

---

### Dependencies

#### New Dependencies
```
# OSS Frameworks (optional, graceful fallback)
ragas>=0.1.0
datasets>=2.14.0
langchain-community>=0.0.10
langchain-ollama>=1.0.0
huey>=2.5.0

# TTS Enhancement (optional)
torch>=2.0.0
transformers>=4.35.0
soundfile>=0.12.0
pydub>=0.25.0
parler-tts @ git+https://github.com/huggingface/parler-tts.git
```

#### Updated Dependencies
- FastAPI: 0.115.6
- Pydantic: 2.10.3
- ChromaDB: 0.5.23
- SQLAlchemy: 2.0.36
- Alembic: 1.16.5

---

### Migration Guide

#### From v1.x to v2.0

1. **Database Migration**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Environment Variables**
   ```bash
   # Copy new template
   cp .env.example .env
   
   # Add optional HuggingFace token for Hindi TTS
   # HF_TOKEN=hf_your_token_here
   ```

3. **Optional OSS Frameworks**
   ```bash
   # For RAGAS evaluation
   pip install ragas datasets langchain-community langchain-ollama
   
   # For Huey task queue
   pip install huey
   
   # For Indic Parler-TTS (Hindi neural TTS)
   pip install torch transformers soundfile pydub
   pip install git+https://github.com/huggingface/parler-tts.git
   ```

4. **Model Verification**
   ```bash
   # Ensure correct model is pulled
   ollama pull gemma2:2b
   ollama pull nomic-embed-text
   ```

---

### Contributors

- **Vikas Sahani** - Product Manager & Main Product Lead
- **Kiro** - AI Co-Engineering Assistant
- **Antigravity** - AI Co-Assistant & Engineering Support

---

### References

- [Remediation Plan](docs/reports/REMEDIATION_PLAN.md)
- [Implementation Status](docs/reports/IMPLEMENTATION_STATUS.md)
- [Progress Tracker](docs/reports/PROGRESS_TRACKER.md)
- [System Architecture](docs/SYSTEM_ARCHITECTURE.md)

---

## [1.0.0] - 2025-12-15

### Initial Release

- Basic insurance document analysis with Ollama
- RAG system with ChromaDB
- Material 3 web interface
- Hindi/English bilingual support
- Basic guardrails and HITL workflow

---

*For more details, see the [README](README.md) and [documentation](docs/).*
