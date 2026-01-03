"""
IRDAI Knowledge Base Indexing Script

Indexes IRDAI regulatory documents into ChromaDB for RAG-enhanced policy analysis.
Processes documents with contextual chunking for improved retrieval accuracy.
"""

import sys

from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag_service import rag_service
import structlog

logger = structlog.get_logger(__name__)

# IRDAI knowledge directory
IRDAI_KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "irdai_knowledge"


def index_irdai_documents():
    """
    Index all IRDAI regulatory documents into ChromaDB.
    """
    print("=" * 80)
    print(" IRDAI KNOWLEDGE BASE INDEXING")
    print("=" * 80)
    print()
    
    if not rag_service:
        print("❌ RAG Service not available!")
        print("   Install: pip install chromadb rank-bm25")
        print("   Pull model: ollama pull nomic-embed-text")
        return False
    
    # Check if IRDAI directory exists
    if not IRDAI_KNOWLEDGE_DIR.exists():
        print(f"❌ IRDAI knowledge directory not found: {IRDAI_KNOWLEDGE_DIR}")
        return False
    
    # Get all .txt files in IRDAI directory
    knowledge_files = sorted(IRDAI_KNOWLEDGE_DIR.glob("*.txt"))
    
    if not knowledge_files:
        print(f"❌ No knowledge files found in {IRDAI_KNOWLEDGE_DIR}")
        return False
    
    print(f"[DOCS] Found {len(knowledge_files)} IRDAI document(s) to index")
    print()
    
    total_chunks = 0
    indexed_docs = 0
    
    for file_path in knowledge_files:
        print(f"[FILE] Processing: {file_path.name}")
        print("-" * 80)
        
        try:
            # Read document content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract document type from filename
            filename = file_path.stem
            if "health" in filename.lower():
                doc_type = "health_insurance"
                category = "Health Insurance"
            elif "motor" in filename.lower():
                doc_type = "motor_insurance"
                category = "Motor Insurance"
            elif "life" in filename.lower():
                doc_type = "life_insurance"
                category = "Life Insurance"
            else:
                doc_type = "general"
                category = "General"
            
            # Prepare metadata
            metadata = {
                'title': f"IRDAI {category} Guidelines",
                'document_type': 'irdai_regulation',
                'insurance_category': doc_type,
                'source': file_path.name,
                'authority': 'IRDAI',
                'version': '2024.1'
            }
            
            # Create document ID
            doc_id = f"irdai_{doc_type}_guidelines"
            
            # Index document into IRDAI collection
            success = rag_service.index_document(
                text=content,
                document_id=doc_id,
                metadata=metadata,
                collection_name="irdai_knowledge"
            )
            
            if success:
                indexed_docs += 1
                # Get statistics
                stats = rag_service.get_stats()
                doc_chunks = stats.get('irdai_indexed', 0)
                total_chunks = doc_chunks
                
                print(f"   [OK] Indexed successfully")
                print(f"   [STATS] Total chunks in IRDAI collection: {doc_chunks}")
            else:
                print(f"   [FAIL] Failed to index")
            
            print()
        
        except Exception as e:
            print(f"   [ERROR] Error processing {file_path.name}: {e}")
            print()
            continue
    
    # Final summary
    print("=" * 80)
    print(" INDEXING SUMMARY")
    print("=" * 80)
    print(f"[RESULT] Documents indexed: {indexed_docs}/{len(knowledge_files)}")
    print(f"[STATS] Total chunks in IRDAI knowledge base: {total_chunks}")
    print()
    
    if indexed_docs == len(knowledge_files):
        print("[SUCCESS] All IRDAI documents indexed successfully!")
        print()
        print("Next steps:")
        print("1. Test IRDAI knowledge queries")
        print("2. Integrate with policy analysis endpoint")
        print("3. Add document-specific Q&A")
        return True
    else:
        print("[WARNING] Some documents failed to index")
        return False


def test_irdai_query():
    """
    Test querying the IRDAI knowledge base.
    """
    print("=" * 80)
    print(" TESTING IRDAI KNOWLEDGE BASE")
    print("=" * 80)
    print()
    
    if not rag_service:
        print("[ERROR] RAG Service not available!")
        return
    
    # Test queries
    test_queries = [
        "What is the maximum waiting period for pre-existing diseases in health insurance?",
        "What is the grace period for motor insurance renewal?",
        "What is the contestability period for life insurance claims?"
    ]
    
    for query in test_queries:
        print(f"[QUERY] {query}")
        print("-" * 80)
        
        results = rag_service.query_knowledge_base(query, top_k=2)
        
        if results:
            print(f"   Found {len(results)} relevant results:")
            for i, result in enumerate(results, 1):
                print(f"\n   Result {i}:")
                print(f"   Category: {result.get('insurance_category', 'Unknown')}")
                print(f"   Hybrid Score: {result['hybrid_score']:.3f}")
                print(f"   Content: {result['content'][:150]}...")
        else:
            print("   [NOTFOUND] No results found")
        
        print()
    
    print("[OK] IRDAI knowledge base query test complete")
    print()


if __name__ == "__main__":
    print()
    
    # Index documents
    success = index_irdai_documents()
    
    if success:
        # Test queries
        print()
        test_irdai_query()
    
    print("=" * 80)
    print()
