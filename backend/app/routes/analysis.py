
import tempfile
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
import structlog
from typing import Dict, Any

from app.dependencies import GlobalServices

# Create Router
router = APIRouter()
logger = structlog.get_logger(__name__)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and analyze insurance policy."""
    logger.info(f"📥 Received file upload request: {file.filename}")
    try:
        if not GlobalServices.document_service or not GlobalServices.policy_service:
            logger.error("Services not initialized")
            raise HTTPException(status_code=503, detail="Services not initialized")

        # Validate file size before processing
        # Note: file.size may be None for streaming uploads, so we also check after reading
        if file.size is not None and file.size > GlobalServices.document_service.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({file.size} bytes) exceeds maximum allowed size ({GlobalServices.document_service.max_file_size} bytes)"
            )
        
        # Check file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in GlobalServices.document_service.supported_formats:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Validate file size after reading (for streaming uploads where file.size may be None)
        content = await file.read()
        if len(content) > GlobalServices.document_service.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size ({len(content)} bytes) exceeds maximum allowed size ({GlobalServices.document_service.max_file_size} bytes)"
            )
        
        # Use TemporaryDirectory for automatic cleanup even on crashes
        # This ensures temp files are always cleaned up, preventing disk exhaustion and security leaks
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_file_path = Path(tmp_dir) / f"upload{file_extension}"
            tmp_file_path.write_bytes(content)
            
            logger.info(f"📂 File saved to temp: {tmp_file_path}")

            try:
                # Extract text - SYNC call (no nested threading issues)
                logger.info("⚙️ Starting text extraction...")
                extracted_text, pages = GlobalServices.document_service.extract_text_from_file(tmp_file_path)
                logger.info(f"✅ Text extraction complete: {len(extracted_text)} chars")

                if not extracted_text.strip():
                    raise HTTPException(status_code=400, detail="No text could be extracted")
                
                # Analyze policy - SYNC call (avoids nested ThreadPoolExecutor deadlock)
                logger.info("🔍 Starting policy analysis...")
                analysis = GlobalServices.policy_service.analyze_policy(extracted_text, pages=pages)
                logger.info("✅ Policy analysis complete")
                
                if analysis.get("status") == "error":
                    raise HTTPException(status_code=500, detail=f"Analysis failed: {analysis.get('error')}")
                
                return {
                    "filename": file.filename,
                    "analysis": analysis,
                    "document_id": f"doc_{time.time()}" 
                }
            except ValueError as e:
                # Re-raise ValueError as HTTPException with appropriate status code
                if "exceeds maximum" in str(e).lower():
                    raise HTTPException(status_code=413, detail=str(e))
                raise HTTPException(status_code=400, detail=str(e))
            # TemporaryDirectory context manager automatically cleans up on exit
            # No need for manual cleanup - this prevents orphaned files on crashes
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask_document")
async def ask_document(data: Dict[str, Any] = Body(...)):
    """
    Ask questions about the currently indexed policy document.
    """
    try:
        question = data.get("question")
        if not question:
             raise HTTPException(status_code=400, detail="Question is required")
             
        if not GlobalServices.policy_service:
             raise HTTPException(status_code=503, detail="Policy service unavailable")

        # Delegate to policy service answer_question
        # Note: In the simplified refactor, we rely on the session state held in RAG/Ollama services
        # effectively maintained by the singletons. 
        # Ideally, we pass session ID, but current implementation is single-session/global demo.
        
        # We need to access the text? 'answer_question' in original Code 
        # used `rag_service.query_document` significantly.
        # PolicyService.answer_question encapsulates this.
        
        # PolicyService.answer_question now returns a rich dictionary:
        # { "answer": str, "document_excerpts": list, "irdai_context": list, "confidence": float }
        result = GlobalServices.policy_service.answer_question(document_text="", question=question)
        
        return {
            "answer": result.get("answer"),
            "document_excerpts": result.get("document_excerpts", []),
            "irdai_context": result.get("irdai_context", []),
            "confidence": result.get("confidence", 0.0),
            "status": "success"
        }

    except Exception as e:
         logger.error("Ask Data failed", error=str(e))
         raise HTTPException(status_code=500, detail=str(e))
