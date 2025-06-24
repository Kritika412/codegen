"""
Sprints API routes for managing sprints and generating summaries.

This module provides endpoints for retrieving sprint information,
generating sprint summaries, and managing sprint-related data.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import Sprint, SprintSummary
from app.services.sprint_service import SprintService
from app.core.config import logger
from app.core.exceptions import (
    SprintNotFoundError,
    GitHubAPIError
)

router = APIRouter(prefix="/sprints", tags=["sprints"])

# Add compatibility route for the original API endpoint
compat_router = APIRouter(tags=["sprints-compat"])


@router.get("/", response_model=List[Sprint])
async def get_sprints():
    """
    Get all sprint views from GitHub organization project.
    
    Returns views that start with "Sprint" and converts them into Sprint objects
    sorted by sprint number (descending - newest first).
    
    Returns:
        List of Sprint objects
        
    Raises:
        HTTPException: If sprints cannot be retrieved
    """
    try:
        sprint_service = SprintService()
        sprints = sprint_service.get_all_sprints()
        
        logger.info(f"Successfully returned {len(sprints)} sprints")
        return sprints
        
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in get_sprints: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sprint fetch error: {str(e)}")


@router.get("/summary", response_model=SprintSummary)
async def get_sprint_summary(
    sprint_name: str = Query(..., description="Name of the sprint to analyze")
):
    """
    Get comprehensive sprint summary including status counts and dates.
    
    Args:
        sprint_name: Name of the sprint view to analyze
    
    Returns:
        SprintSummary with all sprint information including:
        - Sprint dates and duration
        - Days remaining
        - Issue counts by status
        - Sprint goals
        
    Raises:
        HTTPException: If sprint is not found or summary cannot be generated
    """
    try:
        sprint_service = SprintService()
        
        # Normalize the sprint name to handle frontend display names
        normalized_sprint_name = sprint_service.normalize_sprint_name(sprint_name)
        
        summary = sprint_service.get_sprint_summary(normalized_sprint_name)
        
        logger.info(f"Successfully generated summary for sprint '{normalized_sprint_name}'")
        return summary
        
    except SprintNotFoundError as e:
        logger.error(f"Sprint not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error in get_sprint_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sprint summary error: {str(e)}")


@router.get("/{sprint_name}/issues")
async def get_sprint_issues(
    sprint_name: str,
    status: str = Query(None, description="Filter issues by status")
):
    """
    Get issues from a specific sprint, optionally filtered by status.
    
    Args:
        sprint_name: Name of the sprint
        status: Optional status filter
        
    Returns:
        List of issues from the sprint
        
    Raises:
        HTTPException: If sprint is not found
    """
    try:
        sprint_service = SprintService()
        
        if status:
            issues = sprint_service.get_sprint_issues_by_status(sprint_name, status)
        else:
            # Get all issues from the sprint
            github_service = sprint_service.github_service
            issues = github_service.get_project_items_by_iteration(sprint_name)
        
        logger.info(f"Retrieved {len(issues)} issues from sprint '{sprint_name}'")
        return {"sprint_name": sprint_name, "issues": issues, "count": len(issues)}
        
    except SprintNotFoundError as e:
        logger.error(f"Sprint not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting sprint issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving sprint issues: {str(e)}")


@router.post("/{sprint_name}/validate")
async def validate_sprint(sprint_name: str):
    """
    Validate that a sprint exists and is accessible.
    
    Args:
        sprint_name: Name of the sprint to validate
        
    Returns:
        Validation result
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        sprint_service = SprintService()
        exists = sprint_service.validate_sprint_exists(sprint_name)
        
        if exists:
            return {
                "valid": True,
                "message": f"Sprint '{sprint_name}' exists and is accessible"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Sprint '{sprint_name}' not found"
            )
            
    except Exception as e:
        logger.error(f"Error validating sprint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/{sprint_name}/metrics")
async def get_sprint_metrics(sprint_name: str):
    """
    Get detailed metrics for a specific sprint.
    
    Args:
        sprint_name: Name of the sprint
        
    Returns:
        Detailed sprint metrics
        
    Raises:
        HTTPException: If sprint is not found
    """
    try:
        sprint_service = SprintService()
        summary = sprint_service.get_sprint_summary(sprint_name)
        
        # Calculate additional metrics
        total_issues = summary.total_issues
        completed_percentage = 0
        in_progress_percentage = 0
        
        if total_issues > 0:
            # Assuming "in_review" issues are essentially completed
            completed_issues = summary.in_review
            completed_percentage = round((completed_issues / total_issues) * 100, 1)
            in_progress_percentage = round((summary.in_progress / total_issues) * 100, 1)
        
        metrics = {
            "sprint_name": sprint_name,
            "total_issues": total_issues,
            "completed_percentage": completed_percentage,
            "in_progress_percentage": in_progress_percentage,
            "days_remaining": summary.days_remaining,
            "status_breakdown": {
                "backlog": summary.backlog,
                "ready": summary.ready,
                "in_progress": summary.in_progress,
                "in_review": summary.in_review
            }
        }
        
        logger.info(f"Generated metrics for sprint '{sprint_name}'")
        return metrics
        
    except SprintNotFoundError as e:
        logger.error(f"Sprint not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting sprint metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")


# Compatibility endpoint for original API
@compat_router.get("/api/sprint-summary", response_model=SprintSummary)
async def get_sprint_summary_compat(
    sprint_name: str = Query(..., description="Name of the sprint to analyze")
):
    """
    Compatibility endpoint for the original /api/sprint-summary endpoint.
    
    This provides backward compatibility with the original API structure.
    
    Args:
        sprint_name: Name of the sprint view to analyze
    
    Returns:
        SprintSummary with all sprint information
    """
    # Just delegate to the main sprint summary function
    return await get_sprint_summary(sprint_name)
