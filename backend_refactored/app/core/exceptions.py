"""
Custom exception classes for the Harmonia API.

This module defines domain-specific exceptions that provide clear error handling
and meaningful error messages throughout the application.
"""

from typing import Optional, Any


class HarmoniaException(Exception):
    """Base exception class for Harmonia API."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class GitHubAPIError(HarmoniaException):
    """Raised when GitHub API operations fail."""
    pass


class ProjectNotFoundError(HarmoniaException):
    """Raised when a GitHub project is not found or not accessible."""
    pass


class SprintNotFoundError(HarmoniaException):
    """Raised when a sprint view is not found."""
    pass


class IssueNotFoundError(HarmoniaException):
    """Raised when an issue is not found."""
    pass


class InvalidSprintNameError(HarmoniaException):
    """Raised when a sprint name format is invalid."""
    pass


class ConfigurationError(HarmoniaException):
    """Raised when there are configuration issues."""
    pass


class CodexExecutionError(HarmoniaException):
    """Raised when Codex CLI execution fails."""
    pass
