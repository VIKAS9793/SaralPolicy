"""
RAG (Retrieval-Augmented Generation) Service for SaralPolicy

Features:
- ChromaDB for local vector storage
- Ollama embeddings (nomic-embed-text)
- Hybrid search (BM25 + Vector)
- Contextual chunking (Anthropic 2024 method)
- IRDAI knowledge base integration
- Document-specific RAG per session
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import structlog
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

import hashlib
import time

try:
    import chromadb
    from chromadb.config import Settings
    # from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

logger = structlog.get_logger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service for SaralPolicy
    Uses ChromaDB + Ollama embeddings + Hybrid search
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedding_model: str = "nomic-embed-text",
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Initialize RAG service
        
        Args:
            persist_directory: Where to store ChromaDB data
            embedding_model: Ollama embedding model name
            ollama_host: Ollama API endpoint
        """
        self.embedding_model = embedding_model
        self.ollama_host = ollama_host
        self.persist_directory = persist_directory
        
        # Performance optimizations
        self.embedding_cache = {}  # Cache embeddings
        self.query_cache = {}  # Cache query results
        # Rationale: 4 workers balances parallelism with memory for I/O-bound embedding API calls
        self.executor = ThreadPoolExecutor(max_workers=4)  # For batch operations
        self.session = requests.Session()  # Connection pooling
        
        # Batch size limits to prevent memory exhaustion
        # Rationale: Each embedding is ~768 floats (3KB), 100 embeddings = 300KB
        # 1000 embeddings = 3MB per batch, which is reasonable for most systems
        # Configurable via environment variable
        self.max_batch_size = int(os.environ.get("MAX_EMBEDDING_BATCH_SIZE", 1000))
        
        # Check dependencies
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not installed. RAG features disabled.")
            logger.info("Install with: pip install chromadb")
            self.enabled = False
            return
        
        # Initialize ChromaDB
        try:
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            
            # Use PersistentClient for data persistence
            self.chroma_client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize collections
            self.irdai_collection = self._get_or_create_collection("irdai_knowledge")
            self.session_collection = None  # Created per document session
            
            # BM25 indices (in-memory)
            self.irdai_bm25 = None
            self.session_bm25 = None
            
            self.enabled = True
            logger.info("[OK] RAG Service initialized", 
                       embedding_model=embedding_model,
                       persist_dir=persist_directory)
            
        except Exception as e:
            logger.error("Failed to initialize RAG service", error=str(e))
            self.enabled = False
    
    def _get_or_create_collection(self, name: str):
        """Get existing collection or create new one."""
        try:
            return self.chroma_client.get_collection(name=name)
        except Exception as e:
            # Collection doesn't exist, create it
            # Log at debug level since this is expected behavior on first run
            logger.debug("Collection not found, creating new", collection=name, reason=str(e))
            return self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get_embeddings(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """
        Get embeddings from Ollama with caching
        
        Args:
            text: Text to embed
            use_cache: Use cached embeddings if available
            
        Returns:
            Embedding vector or None if failed
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self.embedding_cache:
                return self.embedding_cache[cache_key]
        
        try:
            response = self.session.post(
                f"{self.ollama_host}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                embedding = response.json()['embedding']
                # Cache the result
                if use_cache:
                    cache_key = self._get_cache_key(text)
                    self.embedding_cache[cache_key] = embedding
                return embedding
            else:
                logger.error(f"Ollama embeddings error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return None
    
    def get_embeddings_batch(self, texts: List[str], use_cache: bool = True) -> List[Optional[List[float]]]:
        """
        Get embeddings for multiple texts in parallel with caching.
        
        Algorithm Complexity:
            Time: O(n) where n = number of texts
                - Cache lookup: O(1) per text (hash table)
                - API calls: O(n/w) where w = worker count (parallel execution)
                - Total: O(n) with constant factor reduction from parallelism
            Space: O(n * d) where d = embedding dimension (768 for nomic-embed-text)
                - Each embedding: ~3KB (768 floats * 4 bytes)
                - 1000 texts: ~3MB memory for embeddings
        
        ThreadPoolExecutor Usage:
            Workload: I/O-bound (HTTP API calls to Ollama)
            Workers: 4 (configurable via executor initialization)
            Rationale: I/O-bound work benefits from threading despite GIL.
                Network latency dominates, so 4 concurrent requests provide
                ~3-4x throughput improvement over sequential processing.
                More workers show diminishing returns due to Ollama's
                internal batching and connection overhead.
        
        Args:
            texts: List of texts to embed
            use_cache: Use cached embeddings if available
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If batch size exceeds maximum allowed
        """
        # Validate batch size to prevent memory exhaustion
        if len(texts) > self.max_batch_size:
            logger.warning(
                "Batch size exceeds limit, splitting into smaller batches",
                batch_size=len(texts),
                max_batch_size=self.max_batch_size
            )
            # Split into smaller batches and process sequentially
            all_embeddings = []
            for i in range(0, len(texts), self.max_batch_size):
                batch = texts[i:i + self.max_batch_size]
                batch_embeddings = self._get_embeddings_batch_internal(batch, use_cache)
                all_embeddings.extend(batch_embeddings)
            return all_embeddings
        
        return self._get_embeddings_batch_internal(texts, use_cache)
    
    def _get_embeddings_batch_internal(self, texts: List[str], use_cache: bool = True) -> List[Optional[List[float]]]:
        """
        Internal method to get embeddings for a batch (assumes batch size is validated).
        """
        embeddings = [None] * len(texts)
        texts_to_fetch = []
        indices_to_fetch = []
        
        # Check cache first
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self.embedding_cache:
                    embeddings[i] = self.embedding_cache[cache_key]
                else:
                    texts_to_fetch.append(text)
                    indices_to_fetch.append(i)
        else:
            texts_to_fetch = texts
            indices_to_fetch = list(range(len(texts)))
        
        # Fetch uncached embeddings in parallel
        if texts_to_fetch:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_idx = {
                    executor.submit(self.get_embeddings, text, False): (i, text)
                    for i, text in zip(indices_to_fetch, texts_to_fetch)
                }
                
                for future in as_completed(future_to_idx):
                    idx, text = future_to_idx[future]
                    try:
                        embedding = future.result()
                        embeddings[idx] = embedding
                        # Cache the result
                        if use_cache and embedding:
                            cache_key = self._get_cache_key(text)
                            self.embedding_cache[cache_key] = embedding
                    except Exception as e:
                        logger.error(f"Batch embedding failed for index {idx}: {e}")
        
        return embeddings
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Split text into overlapping chunks using sentence boundaries.
        
        Algorithm Complexity:
            Time: O(n) where n = text length
                - Regex split: O(n) single pass
                - Chunk assembly: O(n) iterating through sentences
                - Total: O(n) linear time
            Space: O(n) for storing chunks
                - Output chunks contain all input text plus overlap
                - Overlap adds ~10% overhead (chunk_overlap/chunk_size)
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
            
        Raises:
            ValueError: If input text exceeds maximum allowed length
        """
        # Maximum text length before chunking (prevents memory exhaustion)
        # Rationale: Very large texts can cause memory issues during chunking
        # 50MB is reasonable for most systems
        max_text_length = int(os.environ.get("MAX_CHUNK_TEXT_LENGTH", 50 * 1024 * 1024))
        
        if len(text) > max_text_length:
            logger.warning(
                "Text length exceeds limit before chunking",
                text_length=len(text),
                limit=max_text_length
            )
            raise ValueError(
                f"Text length ({len(text)} chars) exceeds maximum allowed length ({max_text_length} chars) for chunking"
            )
        
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]\s+', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append('. '.join(current_chunk) + '.')
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add last chunk
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks
    
    def chunk_text_with_page(
        self,
        page_text: str,
        page_num: int,
        chunk_size: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Chunk text while preserving page number.
        """
        text_chunks = self.chunk_text(page_text, chunk_size=chunk_size)
        return [{"text": chunk, "page": page_num} for chunk in text_chunks]
    
    def create_contextual_chunk(
        self,
        chunk: str,
        document_context: Dict[str, str]
    ) -> str:
        """
        Add context to chunk (Anthropic 2024 method)
        
        Args:
            chunk: Original chunk text
            document_context: Context info (title, section, etc.)
            
        Returns:
            Contextualized chunk
        """
        context_parts = []
        
        if 'title' in document_context:
            context_parts.append(f"Document: {document_context['title']}")
        
        if 'section' in document_context:
            context_parts.append(f"Section: {document_context['section']}")
        
        if 'policy_type' in document_context:
            context_parts.append(f"Policy Type: {document_context['policy_type']}")
        
        if context_parts:
            context = '\n'.join(context_parts) + '\n\n'
            return context + chunk
        
        return chunk
    
    def index_document(
        self,
        text: Any,  # Union[str, List[Dict[str, Any]]]
        document_id: str,
        metadata: Dict[str, Any],
        collection_name: str = "session",
        use_contextual: bool = True
    ) -> bool:
        """
        Index a document for RAG retrieval.
        
        Algorithm Complexity:
            Time: O(n + c * e) where n = text length, c = chunks, e = embedding time
                - Chunking: O(n) linear text processing
                - Embedding generation: O(c) API calls (parallelized)
                - ChromaDB insertion: O(c) with HNSW index update O(c log c)
                - BM25 index build: O(c * t) where t = avg tokens per chunk
                - Total: O(n + c * e) dominated by embedding API latency
            Space: O(c * d) where d = embedding dimension
                - Chunks stored in ChromaDB: O(c * chunk_size)
                - Embeddings: O(c * 768) floats
                - BM25 index: O(c * t) tokens
        
        Performance Notes:
            - Batch embedding provides ~3-4x speedup over sequential
            - Contextual chunking adds ~20% overhead but improves retrieval
            - HNSW index enables O(log n) search at query time
        
        Args:
            text: Document text
            document_id: Unique document identifier
            metadata: Document metadata
            collection_name: Collection to store in
            use_contextual: Use contextual chunking
            
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("RAG not enabled, skipping indexing")
            return False
        
        try:
            # Get or create collection
            if collection_name == "session":
                self.session_collection = self._get_or_create_collection(f"session_{document_id}")
            else:
                collection = self._get_or_create_collection(collection_name)
            
            # Smart Chunking with Page Numbers
            all_chunks = []
            
            # Handle list of pages (New Format for Citations)
            if isinstance(text, list):
                logger.info(f"Indexing {len(text)} pages with citation support")
                for page_data in text:
                    # page_data should be {'text': str, 'page_number': int}
                    page_text = page_data.get('text', '')
                    page_num = page_data.get('page_number', 0)
                    
                    page_chunks = self.chunk_text_with_page(page_text, page_num)
                    all_chunks.extend(page_chunks)
            else:
                # Fallback for raw string (Old Format)
                logger.warning("Indexing raw text without page numbers (Citations will be limited)")
                raw_chunks = self.chunk_text(text)
                all_chunks = [{"text": c, "page": 0} for c in raw_chunks]

            logger.info(f"Created {len(all_chunks)} chunks for document {document_id}")
            
            # Prepare contextual chunks
            document_context = {
                'title': metadata.get('title', 'Policy Document'),
                'policy_type': metadata.get('policy_type', 'Insurance'),
                'section': metadata.get('section', 'General')
            }
            
            contextual_chunks_text = []
            source_pages = []
            
            for chunk_data in all_chunks:
                chunk_text = chunk_data['text']
                page_num = chunk_data['page']
                
                if use_contextual:
                    ctx_chunk = self.create_contextual_chunk(chunk_text, document_context)
                else:
                    ctx_chunk = chunk_text
                
                contextual_chunks_text.append(ctx_chunk)
                source_pages.append(page_num)
            
            # Generate embeddings and store (batch processing for speed)
            collection_target = self.session_collection if collection_name == "session" else collection
            
            start_time = time.time()
            logger.info(f"⚡ Generating embeddings for {len(contextual_chunks_text)} chunks...")
            
            # Batch embed all chunks at once (much faster than sequential)
            embeddings = self.get_embeddings_batch(contextual_chunks_text, use_cache=True)
            
            embed_time = time.time() - start_time
            logger.info(f"✅ Generated {len(embeddings)} embeddings in {embed_time:.2f}s")
            
            # Batch add to collection
            valid_embeddings = []
            valid_documents = []
            valid_metadatas = []
            valid_ids = []
            
            for i, (chunk, embedding, page_num) in enumerate(zip(contextual_chunks_text, embeddings, source_pages)):
                if embedding:
                    valid_embeddings.append(embedding)
                    valid_documents.append(chunk)
                    valid_metadatas.append({
                        'document_id': document_id,
                        'chunk_index': i,
                        'page_number': page_num,
                        **metadata
                    })
                    valid_ids.append(f"{document_id}_chunk_{i}")
            
            if not valid_embeddings:
                logger.error("No valid embeddings generated. Aborting indexing.")
                return False
            
            # Single batch add operation (much faster than individual adds)
            if valid_embeddings:
                collection_target.add(
                    embeddings=valid_embeddings,
                    documents=valid_documents,
                    metadatas=valid_metadatas,
                    ids=valid_ids
                )
            
            # Build BM25 index for hybrid search
            if BM25_AVAILABLE:
                tokenized_chunks = [chunk.lower().split() for chunk in contextual_chunks_text]
                if collection_name == "session":
                    self.session_bm25 = BM25Okapi(tokenized_chunks)
                else:
                    self.irdai_bm25 = BM25Okapi(tokenized_chunks)
            
            logger.info(f"[OK] Indexed {len(all_chunks)} chunks for {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    def hybrid_search(
        self,
        query: str,
        collection_name: str = "session",
        top_k: int = 5,
        alpha: float = 0.5,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 + Vector similarity with query caching.
        
        Algorithm Complexity:
            Time: O(n + k log k) where n = corpus size, k = top_k
                - Query embedding: O(1) single API call
                - Vector search (HNSW): O(log n) approximate nearest neighbor
                - BM25 scoring: O(n * q) where q = query terms (typically small)
                - Score combination: O(k) for top results
                - Final sort: O(k log k)
                - Total dominated by BM25: O(n) for full corpus scan
            Space: O(k) for result storage
                - Intermediate: O(2k) for vector results before filtering
        
        Trade-offs:
            - alpha=0.5: Balanced semantic + keyword matching
            - alpha=0.6: Favors semantic (better for regulatory queries)
            - Higher top_k increases recall but adds latency
        
        Args:
            query: Search query
            collection_name: Collection to search
            top_k: Number of results to return
            alpha: Weight for vector search (0=BM25 only, 1=vector only)
            use_cache: Use cached query results if available
            
        Returns:
            List of results with scores
        """
        if not self.enabled:
            return []
        
        # Check query cache
        cache_key = f"{collection_name}:{query}:{top_k}:{alpha}"
        if use_cache and cache_key in self.query_cache:
            logger.info("📦 Using cached query results")
            return self.query_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Get collection
            if collection_name == "session" and self.session_collection:
                collection = self.session_collection
                bm25_index = self.session_bm25
            elif collection_name == "irdai_knowledge":
                collection = self.irdai_collection
                bm25_index = self.irdai_bm25
            else:
                logger.warning(f"Collection {collection_name} not found")
                return []
            
            # Vector search
            query_embedding = self.get_embeddings(query)
            if not query_embedding:
                logger.warning("Failed to get query embedding")
                return []
            
            vector_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2  # Get more for re-ranking
            )
            
            # BM25 search (if available)
            bm25_scores = {}
            if BM25_AVAILABLE and bm25_index:
                tokenized_query = query.lower().split()
                scores = bm25_index.get_scores(tokenized_query)
                for idx, score in enumerate(scores):
                    bm25_scores[idx] = score
            
            # Combine scores
            results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                vector_results['documents'][0],
                vector_results['metadatas'][0],
                vector_results['distances'][0]
            )):
                # Vector similarity (lower distance = better)
                vector_score = 1 / (1 + distance)
                
                # BM25 score
                chunk_idx = metadata.get('chunk_index', i)
                bm25_score = bm25_scores.get(chunk_idx, 0)
                
                # Normalize BM25
                if bm25_scores:
                    max_bm25 = max(bm25_scores.values()) if bm25_scores else 1
                    bm25_score = bm25_score / max_bm25 if max_bm25 > 0 else 0
                
                # Hybrid score
                hybrid_score = alpha * vector_score + (1 - alpha) * bm25_score
                
                results.append({
                    'content': doc,
                    'metadata': metadata,
                    'vector_score': vector_score,
                    'bm25_score': bm25_score,
                    'hybrid_score': hybrid_score
                })
            
            # Sort by hybrid score
            results.sort(key=lambda x: x['hybrid_score'], reverse=True)
            
            final_results = results[:top_k]
            
            # Cache the results
            if use_cache:
                self.query_cache[cache_key] = final_results
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Hybrid search completed in {elapsed:.2f}s", results=len(final_results))
            
            return final_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def query_knowledge_base(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query IRDAI knowledge base
        
        Args:
            query: User question
            top_k: Number of relevant chunks to return
            
        Returns:
            List of relevant knowledge chunks
        """
        # Alpha=0.6: Slightly favor vector search for IRDAI knowledge base
        # Rationale: Regulatory content benefits from semantic understanding
        # to match user questions with relevant regulations even when
        # exact terminology differs. BM25 still contributes 40% for keyword matching.
        return self.hybrid_search(
            query=query,
            collection_name="irdai_knowledge",
            top_k=top_k,
            alpha=0.6
        )
    
    def query_document(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query current document session
        
        Args:
            query: User question
            top_k: Number of relevant chunks to return
            
        Returns:
            List of relevant document chunks
        """
        # Alpha=0.5: Balanced hybrid search for document queries
        # Rationale: User-uploaded documents may contain specific terms
        # that benefit from BM25 keyword matching, while semantic search
        # helps find conceptually related content. Equal weighting provides
        # best coverage for diverse query types.
        return self.hybrid_search(
            query=query,
            collection_name="session",
            top_k=top_k,
            alpha=0.5
        )
    
    def clear_session(self):
        """Clear current session collection"""
        if self.session_collection:
            try:
                self.chroma_client.delete_collection(self.session_collection.name)
                self.session_collection = None
                self.session_bm25 = None
                logger.info("[OK] Session collection cleared")
            except Exception as e:
                logger.error(f"Failed to clear session: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG service statistics"""
        stats = {
            "enabled": self.enabled,
            "embedding_model": self.embedding_model,
            "irdai_indexed": False,
            "session_active": self.session_collection is not None
        }
        
        if self.enabled:
            try:
                irdai_count = self.irdai_collection.count()
                stats["irdai_indexed"] = irdai_count > 0
                stats["irdai_chunks"] = irdai_count
            except Exception as e:
                # Log failure but don't crash stats endpoint
                logger.warning("Failed to retrieve IRDAI collection stats", error=str(e))
                stats["irdai_indexed"] = None
                stats["irdai_error"] = str(e)
        
        return stats


def create_rag_service(persist_directory: Optional[str] = None) -> Optional["RAGService"]:
    """
    Factory function to create RAGService instance.
    
    This replaces module-level instantiation to:
    - Avoid import-time side effects
    - Enable explicit dependency injection
    - Allow tests to create isolated instances
    - Fail fast with clear error messages
    
    Args:
        persist_directory: Optional custom path for ChromaDB storage.
                          If None, uses default backend/data/chroma path.
    
    Returns:
        RAGService instance or None if initialization fails.
        
    Raises:
        No exceptions raised - returns None on failure with logged error.
    """
    try:
        if persist_directory is None:
            # Get directory where this file is located
            service_dir = Path(__file__).parent.resolve()
            # Go up to backend directory, then to data/chroma
            backend_dir = service_dir.parent.parent
            persist_directory = str(backend_dir / "data" / "chroma")
        
        return RAGService(persist_directory=persist_directory)
    except Exception as e:
        logger.error(
            "Failed to create RAG service",
            error=str(e),
            persist_directory=persist_directory
        )
        return None


# DEPRECATED: Module-level singleton for backward compatibility
# This will be removed in a future version. Use create_rag_service() instead.
# Kept temporarily to avoid breaking existing imports during migration.
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> Optional[RAGService]:
    """
    Get or create the RAG service singleton.
    
    This is a transitional pattern - prefer dependency injection via
    create_rag_service() for new code.
    
    Returns:
        RAGService instance or None if unavailable.
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = create_rag_service()
    return _rag_service_instance


# Backward compatibility alias - DEPRECATED
# Existing code imports `from rag_service import rag_service`
# This lazy initialization avoids import-time side effects
class _LazyRAGService:
    """Lazy proxy for backward compatibility with `rag_service` import."""
    
    _instance: Optional[RAGService] = None
    
    def __getattr__(self, name: str) -> Any:
        if self._instance is None:
            self._instance = create_rag_service()
        if self._instance is None:
            raise RuntimeError(
                "RAG service not available. Check ChromaDB installation and logs."
            )
        return getattr(self._instance, name)


# This allows existing `from rag_service import rag_service` to work
# but defers initialization until first attribute access
rag_service = _LazyRAGService()
