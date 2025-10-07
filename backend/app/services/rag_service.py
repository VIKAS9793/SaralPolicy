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
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import structlog
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib
import time

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
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
        self.executor = ThreadPoolExecutor(max_workers=4)  # For batch operations
        self.session = requests.Session()  # Connection pooling
        
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
        """Get existing collection or create new one"""
        try:
            return self.chroma_client.get_collection(name=name)
        except:
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
        Get embeddings for multiple texts in parallel with caching
        
        Args:
            texts: List of texts to embed
            use_cache: Use cached embeddings if available
            
        Returns:
            List of embedding vectors
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
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
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
        text: str,
        document_id: str,
        metadata: Dict[str, Any],
        collection_name: str = "session",
        use_contextual: bool = True
    ) -> bool:
        """
        Index a document for RAG retrieval
        
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
            
            # Chunk document
            chunks = self.chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks for document {document_id}")
            
            # Prepare contextual chunks
            document_context = {
                'title': metadata.get('title', 'Policy Document'),
                'policy_type': metadata.get('policy_type', 'Insurance'),
                'section': metadata.get('section', 'General')
            }
            
            contextual_chunks = []
            for i, chunk in enumerate(chunks):
                if use_contextual:
                    ctx_chunk = self.create_contextual_chunk(chunk, document_context)
                else:
                    ctx_chunk = chunk
                contextual_chunks.append(ctx_chunk)
            
            # Generate embeddings and store (batch processing for speed)
            collection_target = self.session_collection if collection_name == "session" else collection
            
            start_time = time.time()
            logger.info(f"⚡ Generating embeddings for {len(contextual_chunks)} chunks...")
            
            # Batch embed all chunks at once (much faster than sequential)
            embeddings = self.get_embeddings_batch(contextual_chunks, use_cache=True)
            
            embed_time = time.time() - start_time
            logger.info(f"✅ Generated {len(embeddings)} embeddings in {embed_time:.2f}s")
            
            # Batch add to collection
            valid_embeddings = []
            valid_documents = []
            valid_metadatas = []
            valid_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(contextual_chunks, embeddings)):
                if embedding:
                    valid_embeddings.append(embedding)
                    valid_documents.append(chunk)
                    valid_metadatas.append({
                        'document_id': document_id,
                        'chunk_index': i,
                        **metadata
                    })
                    valid_ids.append(f"{document_id}_chunk_{i}")
            
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
                tokenized_chunks = [chunk.lower().split() for chunk in chunks]
                if collection_name == "session":
                    self.session_bm25 = BM25Okapi(tokenized_chunks)
                else:
                    self.irdai_bm25 = BM25Okapi(tokenized_chunks)
            
            logger.info(f"[OK] Indexed {len(chunks)} chunks for {document_id}")
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
        Hybrid search combining BM25 + Vector similarity with query caching
        
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
        return self.hybrid_search(
            query=query,
            collection_name="irdai_knowledge",
            top_k=top_k,
            alpha=0.6  # Slightly favor vector search for semantic understanding
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
        return self.hybrid_search(
            query=query,
            collection_name="session",
            top_k=top_k,
            alpha=0.5  # Balanced for document-specific queries
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
            except:
                pass
        
        return stats


# Global RAG service instance
# Use absolute path relative to this file to ensure consistent storage
try:
    # Get directory where this file is located
    service_dir = Path(__file__).parent.resolve()
    # Go up to backend directory, then to data/chroma
    backend_dir = service_dir.parent.parent
    persist_dir = backend_dir / "data" / "chroma"
    
    rag_service = RAGService(persist_directory=str(persist_dir))
except Exception as e:
    logger.error(f"Failed to initialize global RAG service: {e}")
    rag_service = None
