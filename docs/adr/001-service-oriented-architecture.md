# ADR 001: Refactoring to Service-Oriented Architecture

**Status:** Accepted  
**Date:** 2025-12-31  
**Author:** Vikas Sahani (Product Lead)

## Context

The initial implementation of `SaralPolicy` was a monolithic `main.py` file containing:
- FastAPI route definitions.
- Business logic for RAG, Document Parsing, and Policy Analysis.
- Dependencies and initialization code.

This structure made the codebase:
1. Hard to test (unit tests required spinning up the full app or complex mocking).
2. Hard to read and maintain (file size grew rapidly).
3. Difficult to extend (adding new features meant modifying the single massive file).

## Decision

We decided to refactor the application into a modular, **Service-Oriented Architecture (SOA)** within the monolith.

### Key Changes:

1.  **Service Extraction**: Business logic moved to dedicated service classes in `app/services/`:
    - `DocumentService`: File parsing (PDF/DOCX), hashing, caching.
    - `PolicyService`: Orchestration of RAG, LLM, and Guardrails.
    - `RAGService` (Existing): Enhanced for independence.
    - `OllamaLLMService` (Existing): Decoupled from main.
    
2.  **Route Decoupling**: API endpoints moved to `app/routes/`:
    - `analysis.py`: `/upload`, `/analyze`, `/ask_document`.
    - `rag_routes.py`: RAG-specific queries (if needed).
    
3.  **Dependency Injection**: Created `app/dependencies.py` to manage singleton instances of services (`GlobalServices`), preventing circular imports and simplifying testing.

4.  **Main Bootstrapper**: `main.py` was reduced to a thin bootstrapper that:
    - Configures FastAPI app.
    - Sets up CORS and Middleware.
    - Registers Routers.
    - Initializes Global Dependencies on startup.

## Consequences

### Positive
- **Testability**: Services can be tested in isolation (e.g., `test_rag_citations.py` imports `RAGService` directly).
- **Maintainability**: Clear separation of concerns. `main.py` is now stable and rarely needs editing.
- **Scalability**: Easier to add new routes (e.g., `audit.py`) or services (`FeedbackService`) without touching existing core logic.

### Negative
- **Complexity**: Increased number of files and directories.
- **Boilerplate**: Need for dependency management infrastructure (`dependencies.py`).
- **Imports**: Requires careful management of imports to avoid circular dependencies (solved via `dependencies.py`).

## Compliance
This refactor adheres to the "Eagle Eye" cleanup goal of Phase 1.5, ensuring no stale code or monolithic debt remains.
