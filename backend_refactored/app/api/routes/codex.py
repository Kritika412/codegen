"""
Codex API routes for AI-powered code generation and repository management.

This module provides endpoints for running Codex workflows, managing
code generation tasks, and checking Codex service status.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import (
    CodexRequest, CodexResponse, CodexCommitResponse, 
    CodexPushRequest, CodexPushResponse
)
from app.services.codex_service import CodexService
from app.core.config import logger
from app.core.exceptions import CodexExecutionError

router = APIRouter(prefix="/codex", tags=["codex"])


@router.post("/run", response_model=CodexCommitResponse)
async def run_codex(codex_request: CodexRequest):
    """
    Run Codex CLI and commit changes (first step).
    
    This endpoint executes the first part of the Codex workflow:
    1. Clone the repository
    2. Run Codex CLI with the prompt
    3. Commit changes to a new branch
    4. Return results for user confirmation
    
    The user can then decide whether to push and create a PR using /push endpoint.
    
    Args:
        codex_request: Request containing prompt and repository information
        
    Returns:
        CodexCommitResponse with operation results
        
    Raises:
        HTTPException: If Codex execution fails
    """
    try:
        codex_service = CodexService()
        
        # Run the Codex workflow up to commit stage
        result = codex_service.run_codex_and_commit(
            prompt=codex_request.prompt,
            repo_name=codex_request.repo
        )
        
        response = CodexCommitResponse(
            status=result["status"],
            message=result["message"],
            branch_name=result["branch_name"],
            temp_dir=result["temp_dir"],
            repo_name=result["repo_name"],
            base_branch=result["base_branch"]
        )
        
        logger.info(f"Codex commit phase completed for repo: {codex_request.repo}")
        return response
        
    except CodexExecutionError as e:
        logger.error(f"Codex execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Codex execution error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in run_codex: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/push", response_model=CodexPushResponse)
async def push_codex(push_request: CodexPushRequest):
    """
    Push committed changes and create pull request (second step).
    
    This endpoint handles the second part of the Codex workflow:
    1. Push the committed branch to GitHub
    2. Create a pull request
    3. Clean up temporary directory
    
    Args:
        push_request: Request containing branch info and temp directory
        
    Returns:
        CodexPushResponse with PR URL and results
        
    Raises:
        HTTPException: If push or PR creation fails
    """
    try:
        codex_service = CodexService()
        
        # Push the branch and create PR
        result = codex_service.push_branch_and_create_pr(
            prompt=push_request.prompt,
            repo_name=push_request.repo_name,
            branch_name=push_request.branch_name,
            base_branch=push_request.base_branch,
            temp_dir=push_request.temp_dir
        )
        
        response = CodexPushResponse(
            status=result["status"],
            message=result["message"],
            branch_name=result["branch_name"],
            pr_url=result["pr_url"]
        )
        
        logger.info(f"Codex push phase completed for branch: {push_request.branch_name}")
        return response
        
    except CodexExecutionError as e:
        logger.error(f"Codex push failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Codex push error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in push_codex: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/cleanup")
async def cleanup_codex(temp_dir: str):
    """
    Clean up temporary directory (used when user chooses not to create PR).
    
    Args:
        temp_dir: Temporary directory path to clean up
        
    Returns:
        Success message
    """
    try:
        codex_service = CodexService()
        codex_service.cleanup_temp_directory(temp_dir)
        
        logger.info(f"Cleaned up temporary directory: {temp_dir}")
        return JSONResponse(
            content={"message": "Temporary directory cleaned up successfully"},
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up temporary directory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")


@router.get("/status")
async def get_codex_status():
    """
    Get the status of Codex CLI and its dependencies.
    
    Checks if Codex CLI is installed and properly configured,
    and verifies that required API keys are available.
    
    Returns:
        Status information for Codex service
    """
    try:
        codex_service = CodexService()
        status = codex_service.get_codex_status()
        
        # Determine overall status
        all_ready = all(status.values())
        overall_status = "ready" if all_ready else "not_ready"
        
        response = {
            "overall_status": overall_status,
            "details": status,
            "message": "Codex service is ready" if all_ready else "Codex service has issues"
        }
        
        logger.info(f"Codex status check: {overall_status}")
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Error checking Codex status: {str(e)}")
        return JSONResponse(
            content={
                "overall_status": "error",
                "details": {"error": str(e)},
                "message": "Failed to check Codex status"
            },
            status_code=500
        )


@router.get("/health")
async def codex_health_check():
    """
    Simple health check for Codex service.
    
    Returns:
        Basic health status
    """
    try:
        codex_service = CodexService()
        
        # Basic validation
        has_openai_key = bool(codex_service.openai_api_key)
        has_github_token = bool(codex_service.github_token)
        
        if has_openai_key and has_github_token:
            return {"status": "healthy", "message": "Codex service is operational"}
        else:
            missing = []
            if not has_openai_key:
                missing.append("OpenAI API key")
            if not has_github_token:
                missing.append("GitHub token")
            
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "message": f"Missing configuration: {', '.join(missing)}"
                },
                status_code=503
            )
            
    except Exception as e:
        logger.error(f"Codex health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            },
            status_code=503
        )


@router.post("/validate-repo")
async def validate_repository(repo_name: str):
    """
    Validate that a repository is accessible for Codex operations.
    
    Args:
        repo_name: Repository name to validate
        
    Returns:
        Validation result
    """
    try:
        codex_service = CodexService()
        
        # Try to access the repository
        repo = codex_service.github_client.get_repo(repo_name)
        
        # Check if repository is accessible
        repo_info = {
            "name": repo.full_name,
            "private": repo.private,
            "default_branch": repo.default_branch,
            "permissions": {
                "admin": repo.permissions.admin,
                "push": repo.permissions.push,
                "pull": repo.permissions.pull
            }
        }
        
        if not repo.permissions.push:
            return JSONResponse(
                content={
                    "valid": False,
                    "message": "No push permissions to repository",
                    "repo_info": repo_info
                },
                status_code=403
            )
        
        return {
            "valid": True,
            "message": "Repository is accessible for Codex operations",
            "repo_info": repo_info
        }
        
    except Exception as e:
        logger.error(f"Repository validation failed: {str(e)}")
        return JSONResponse(
            content={
                "valid": False,
                "message": f"Repository validation failed: {str(e)}"
            },
            status_code=400
        )
