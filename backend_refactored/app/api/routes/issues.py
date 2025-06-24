"""
Issues API routes for managing GitHub issues.

This module provides endpoints for retrieving, creating, and updating issues
within GitHub projects and repositories.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.schemas import Issue, IssueUpdateRequest, ApiResponse
from app.services.github_service import GitHubService
from app.core.config import logger
from app.core.exceptions import (
    GitHubAPIError,
    SprintNotFoundError,
    IssueNotFoundError
)

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("/ready", response_model=List[Issue])
async def get_ready_issues(
    sprint_name: Optional[str] = Query(None, description="Sprint name to filter by")
):
    """
    Get issues that are in 'Ready' status for Codex processing.
    
    This endpoint specifically returns issues that are ready for AI assistance,
    filtering to only show 'Ready' status issues.
    
    Args:
        sprint_name: Optional sprint name to filter by
        
    Returns:
        List of issues with 'Ready' status
        
    Raises:
        HTTPException: If sprint is not found or other errors occur
    """
    try:
        if not sprint_name:
            # If no sprint specified, could get ready issues from current/latest sprint
            # For now, require sprint_name
            raise HTTPException(
                status_code=400, 
                detail="sprint_name parameter is required"
            )
        
        github_service = GitHubService()
        
        # Get issues from the specific sprint filtered by 'Ready' status
        filtered_issues = github_service.get_project_items_by_iteration(
            sprint_name=sprint_name,
            status_filter="Ready"  # Filter for Ready status specifically
        )
        
        # Convert to Issue objects
        issues = []
        for issue_data in filtered_issues:
            content = issue_data['content']
            
            # Extract assignee
            assignee = None
            if 'assignees' in content and content['assignees']['nodes']:
                assignee = content['assignees']['nodes'][0]['login']
            
            # Extract labels
            labels = []
            if 'labels' in content and content['labels']['nodes']:
                labels = [label['name'] for label in content['labels']['nodes']]
            
            # Extract repository name
            repo_name = "Unknown"
            if 'repository' in content:
                repo_name = content['repository']['nameWithOwner']
            elif 'title' in content and not content.get('url'):
                repo_name = "Draft Issue"
            
            # Create Issue object
            issue = Issue(
                id=content['id'],
                number=content.get('number', 0),
                title=content['title'],
                assignee=assignee,
                status=issue_data['status'].lower() if issue_data['status'] else 'unknown',
                created_at=content.get('createdAt', ''),
                updated_at=content.get('updatedAt', ''),
                body=content.get('body', ''),
                labels=labels,
                repo=repo_name,
                url=content.get('url', '')
            )
            
            issues.append(issue)
        
        logger.info(f"Successfully returned {len(issues)} ready issues for sprint '{sprint_name}'")
        return issues
        
    except SprintNotFoundError as e:
        logger.error(f"Sprint not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_ready_issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/", response_model=List[Issue])
async def get_issues(
    sprint_name: Optional[str] = Query(None, description="Sprint name to filter by"),
    status: Optional[str] = Query(None, description="Status to filter by")
):
    """
    Retrieve issues from GitHub Projects filtered by sprint and optionally by status.
    
    Args:
        sprint_name: Name of the sprint view to filter by (required)
        status: Optional status filter (Ready, In Progress, etc.)
    
    Returns:
        List of issues from the specified sprint iteration
        
    Raises:
        HTTPException: If sprint_name is missing or other errors occur
    """
    try:
        if not sprint_name:
            raise HTTPException(
                status_code=400, 
                detail="sprint_name parameter is required"
            )
        
        github_service = GitHubService()
        
        # Get issues from the specific sprint with optional status filter
        filtered_issues = github_service.get_project_items_by_iteration(
            sprint_name=sprint_name,
            status_filter=status
        )
        
        # Convert to Issue objects
        issues = []
        for issue_data in filtered_issues:
            content = issue_data['content']
            
            # Extract assignee
            assignee = None
            if 'assignees' in content and content['assignees']['nodes']:
                assignee = content['assignees']['nodes'][0]['login']
            
            # Extract labels
            labels = []
            if 'labels' in content and content['labels']['nodes']:
                labels = [label['name'] for label in content['labels']['nodes']]
            
            # Extract repository name
            repo_name = "Unknown"
            if 'repository' in content:
                repo_name = content['repository']['nameWithOwner']
            elif 'title' in content and not content.get('url'):
                repo_name = "Draft Issue"
            
            # Create Issue object
            issue = Issue(
                id=content['id'],
                number=content.get('number', 0),
                title=content['title'],
                assignee=assignee,
                status=issue_data['status'].lower() if issue_data['status'] else 'unknown',
                created_at=content.get('createdAt', ''),
                updated_at=content.get('updatedAt', ''),
                body=content.get('body', ''),
                labels=labels,
                repo=repo_name,
                url=content.get('url', '')
            )
            
            issues.append(issue)
        
        logger.info(f"Successfully returned {len(issues)} issues for sprint '{sprint_name}'")
        return issues
        
    except SprintNotFoundError as e:
        logger.error(f"Sprint not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch("/{issue_number}")
async def update_issue(
    issue_number: int,
    repo_name: str = Query(..., description="Repository name (e.g., 'owner/repo')"),
    update_request: IssueUpdateRequest = ...
):
    """
    Update an issue's description.
    
    Args:
        issue_number: GitHub issue number
        repo_name: Repository name (e.g., "owner/repo")
        update_request: Request body containing the new description
    
    Returns:
        Success message or error
        
    Raises:
        HTTPException: If update fails
    """
    try:
        github_service = GitHubService()
        
        success = github_service.update_issue_description(
            issue_number=issue_number,
            repo_name=repo_name,
            new_body=update_request.body
        )
        
        if success:
            logger.info(f"Successfully updated issue #{issue_number} in {repo_name}")
            return JSONResponse(
                content={"message": f"Issue #{issue_number} updated successfully"},
                status_code=200
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update issue")
            
    except IssueNotFoundError as e:
        logger.error(f"Issue not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubAPIError as e:
        logger.error(f"GitHub API error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating issue #{issue_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Issue update error: {str(e)}")


@router.get("/{issue_number}")
async def get_issue(
    issue_number: int,
    repo_name: str = Query(..., description="Repository name (e.g., 'owner/repo')")
):
    """
    Get details for a specific issue.
    
    Args:
        issue_number: GitHub issue number
        repo_name: Repository name
        
    Returns:
        Issue details
        
    Raises:
        HTTPException: If issue is not found
    """
    try:
        github_service = GitHubService()
        
        # This would need to be implemented in GitHubService
        # For now, return a placeholder response
        return JSONResponse(
            content={
                "message": f"Issue #{issue_number} details from {repo_name}",
                "note": "This endpoint needs implementation in GitHubService"
            },
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error getting issue #{issue_number}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving issue: {str(e)}")
