
import pytest

from app.services.rag_service import RAGService

# Setup/Teardown for ChromaDB
@pytest.fixture
def rag_service():
    service = RAGService()
    # Use a temporary collection for testing
    yield service
    # Cleanup (not strictly necessary with persistent client unless we specific path)
    # Chroma creates local folder "data". 
    # For now we just test logic.

def test_rag_citation_indexing(rag_service: RAGService):
    """Verify RAG service indexes page numbers correctly."""
    
    doc_id = "test_doc_citation"
    metadata = {'title': 'Test Policy', 'policy_type': 'test'}
    
    # Simulate pages input (Text + Page Number)
    pages_input = [
        {"text": "This is page one content about exclusions.", "page_number": 1},
        {"text": "This is page two content about coverage limits.", "page_number": 2}
    ]
    
    # 1. Index
    success = rag_service.index_document(
        text=pages_input,
        document_id=doc_id,
        metadata=metadata
    )
    assert success is True
    
    # 2. Query
    results = rag_service.query_document("What are the exclusions?", top_k=1)
    
    # 3. Verify
    assert len(results) > 0
    first_result = results[0]
    
    # Check if page_number is in metadata
    assert 'metadata' in first_result
    # Chroma metadata key might vary, but we put 'page_number'
    assert first_result['metadata']['page_number'] == 1
    assert "exclusions" in first_result['content']

def test_rag_citation_retrieval_page_2(rag_service: RAGService):
    """Verify querying retrieves correct page."""
    doc_id = "test_doc_citation_2"
    pages_input = [
        {"text": "Nothing here.", "page_number": 1},
        {"text": "Terms and conditions apply.", "page_number": 75}
    ]
    
    rag_service.index_document(pages_input, doc_id, {})
    
    results = rag_service.query_document("terms conditions", top_k=1)
    assert results[0]['metadata']['page_number'] == 75
