"""
Middleware package for SaralPolicy.
"""

from app.middleware.input_validation import InputValidationMiddleware

__all__ = ["InputValidationMiddleware"]

