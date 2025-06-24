"""
Data models for the Harmonia API.

This module contains all Pydantic models used for request/response serialization
and data validation throughout the application.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class BaseIssue(BaseModel):
    """Base model for issue-related data."""
    
    id: str = Field(..., description="GitHub issue ID")
    number: int = Field(..., description="GitHub issue number")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue description/body")
    url: Optional[str] = Field(None, description="GitHub issue URL")


class Issue(BaseIssue):
    """Complete issue model with all metadata."""
    
    assignee: Optional[str] = Field(None, description="Issue assignee username")
    status: str = Field(..., description="Current issue status")
    created_at: str = Field(..., description="Issue creation timestamp")
    updated_at: str = Field(..., description="Issue last update timestamp")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    repo: str = Field(..., description="Repository name")


class IssueCreateRequest(BaseModel):
    """Request model for creating new issues."""
    
    title: str = Field(..., min_length=1, max_length=256, description="Issue title")
    body: Optional[str] = Field(None, description="Issue description")
    assignee: Optional[str] = Field(None, description="Assignee username")
    labels: List[str] = Field(default_factory=list, description="Issue labels")


class IssueUpdateRequest(BaseModel):
    """Request model for updating issue descriptions."""
    
    body: str = Field(..., description="New issue description")


class IssueStatusUpdateRequest(BaseModel):
    """Request model for updating issue status."""
    
    status: str = Field(..., description="New issue status")


class Sprint(BaseModel):
    """Sprint model representing a project iteration."""
    
    id: str = Field(..., description="Sprint identifier")
    name: str = Field(..., description="Sprint display name with dates")
    original_name: str = Field(..., description="Original sprint name for API calls")
    start_date: str = Field(..., description="Sprint start date (ISO format)")
    end_date: str = Field(..., description="Sprint end date (ISO format)")
    iteration_id: Optional[str] = Field(None, description="GitHub iteration ID")
    duration: Optional[int] = Field(None, description="Sprint duration in days")
    is_current: bool = Field(False, description="Whether this is the current sprint")


class SprintSummary(BaseModel):
    """Comprehensive sprint summary with metrics."""
    
    current_sprint: str = Field(..., description="Current sprint name")
    start_date: str = Field(..., description="Sprint start date")
    end_date: str = Field(..., description="Sprint end date")
    days_remaining: int = Field(..., description="Days remaining in sprint")
    sprint_goals: str = Field(..., description="Sprint goals description")
    total_issues: int = Field(..., description="Total issues in sprint")
    backlog: int = Field(..., description="Issues in backlog")
    ready: int = Field(..., description="Issues ready for development")
    in_progress: int = Field(..., description="Issues currently in progress")
    in_review: int = Field(..., description="Issues under review")


class PullRequest(BaseModel):
    """Pull request model."""
    
    id: int = Field(..., description="Pull request ID")
    number: int = Field(..., description="Pull request number")
    title: str = Field(..., description="Pull request title")
    author: str = Field(..., description="Pull request author")
    branch: str = Field(..., description="Source branch name")
    status: str = Field(..., description="Pull request status")
    url: str = Field(..., description="Pull request URL")
    created_at: str = Field(..., description="Creation timestamp")


class CodexRequest(BaseModel):
    """Request model for Codex operations."""
    
    prompt: str = Field(..., min_length=1, description="Codex prompt")
    repo: str = Field(..., description="Target repository")


class CodexResponse(BaseModel):
    """Response model for Codex operations."""
    
    message: str = Field(..., description="Operation result message")
    branch_name: Optional[str] = Field(None, description="Created branch name")
    pr_url: Optional[str] = Field(None, description="Pull request URL")


class ApiResponse(BaseModel):
    """Generic API response model."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: Optional[dict] = Field(None, description="Response data")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
