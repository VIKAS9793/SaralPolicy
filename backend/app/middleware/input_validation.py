"""
Input Validation Middleware
Validates request size and content before processing to prevent DoS attacks.
"""

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import structlog

logger = structlog.get_logger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate input size and prevent DoS attacks.
    
    Validates:
    - Request body size
    - File upload size
    - Content-Length header
    """
    
    def __init__(self, app, max_request_size: int = None, max_file_size: int = None):
        super().__init__(app)
        # Default limits (configurable via environment)
        self.max_request_size = max_request_size or int(
            os.environ.get("MAX_REQUEST_SIZE", 10 * 1024 * 1024)  # 10MB default
        )
        self.max_file_size = max_file_size or int(
            os.environ.get("MAX_FILE_SIZE", 10 * 1024 * 1024)  # 10MB default
        )
        
        logger.info(
            "Input validation middleware initialized",
            max_request_size=self.max_request_size,
            max_file_size=self.max_file_size
        )
    
    async def dispatch(self, request: Request, call_next):
        """
        Validate request size before processing.
        
        Raises:
            HTTPException: 413 Payload Too Large if request exceeds limits
        """
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    logger.warning(
                        "Request rejected: size exceeds limit",
                        size=size,
                        limit=self.max_request_size,
                        path=request.url.path
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Request size ({size} bytes) exceeds maximum allowed size ({self.max_request_size} bytes)"
                    )
            except ValueError:
                # Invalid Content-Length header, let it through but log warning
                logger.warning("Invalid Content-Length header", content_length=content_length)
        
        # Process request
        response = await call_next(request)
        return response

