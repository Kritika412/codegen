"""
Codex API routes for AI-powered code generation and repository management.

This module provides endpoints for running Codex workflows, managing
code generation tasks, and checking Codex service status.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import CodexRequest, CodexResponse
from app.services.codex_service import CodexService
from app.core.config import logger
from app.core.exceptions import CodexExecutionError

router = APIRouter(prefix="/codex", tags=["codex"])


@router.post("/run", response_model=CodexResponse)
async def run_codex(codex_request: CodexRequest):
    """
    Run Codex CLI with the provided prompt and repository.
    
    This endpoint executes the complete Codex workflow:
    1. Clone the repository
    2. Run Codex CLI with the prompt
    3. Commit changes to a new branch
    4. Return the results
    
    Args:
        codex_request: Request containing prompt and repository information
        
    Returns:
        CodexResponse with operation results
        
    Raises:
        HTTPException: If Codex execution fails
    """
    try:
        codex_service = CodexService()
        
        # Run the Codex workflow (without auto-push for safety)
        result = codex_service.run_codex_workflow(
            prompt=codex_request.prompt,
            repo_name=codex_request.repo,
            auto_push=False  # Don't auto-push for manual approval
        )
        
        response = CodexResponse(
            message=result["message"],
            branch_name=result["branch_name"],
            pr_url=result["pr_url"]
        )
        
        logger.info(f"Codex workflow completed for repo: {codex_request.repo}")
        return response
        
    except CodexExecutionError as e:
        logger.error(f"Codex execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Codex execution error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in run_codex: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/run-async")
async def run_codex_async(codex_request: CodexRequest, background_tasks: BackgroundTasks):
    """
    Run Codex CLI asynchronously in the background.
    
    This endpoint starts the Codex workflow in the background and returns immediately.
    Useful for long-running code generation tasks.
    
    Args:
        codex_request: Request containing prompt and repository information
        background_tasks: FastAPI background tasks
        
    Returns:
        Immediate response indicating the task has started
    """
    try:
        codex_service = CodexService()
        
        # Add the Codex workflow to background tasks
        background_tasks.add_task(
            codex_service.run_codex_workflow,
            codex_request.prompt,
            codex_request.repo,
            "main",  # branch
            False    # auto_push
        )
        
        logger.info(f"Started async Codex workflow for repo: {codex_request.repo}")
        return JSONResponse(
            content={
                "message": "Codex workflow started in background",
                "prompt": codex_request.prompt,
                "repo": codex_request.repo
            },
            status_code=202  # Accepted
        )
        
    except Exception as e:
        logger.error(f"Error starting async Codex workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@router.post("/run-and-push", response_model=CodexResponse)
async def run_codex_and_push(codex_request: CodexRequest):
    """
    Run Codex CLI and automatically push changes with PR creation.
    
    This endpoint executes the complete Codex workflow including:
    1. Clone the repository
    2. Run Codex CLI with the prompt
    3. Commit changes to a new branch
    4. Push the branch and create a pull request
    
    Args:
        codex_request: Request containing prompt and repository information
        
    Returns:
        CodexResponse with operation results including PR URL
        
    Raises:
        HTTPException: If Codex execution fails
    """
    try:
        codex_service = CodexService()
        
        # Run the Codex workflow with auto-push enabled
        result = codex_service.run_codex_workflow(
            prompt=codex_request.prompt,
            repo_name=codex_request.repo,
            auto_push=True  # Auto-push and create PR
        )
        
        response = CodexResponse(
            message=result["message"],
            branch_name=result["branch_name"],
            pr_url=result["pr_url"]
        )
        
        logger.info(f"Codex workflow with PR creation completed for repo: {codex_request.repo}")
        return response
        
    except CodexExecutionError as e:
        logger.error(f"Codex execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Codex execution error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in run_codex_and_push: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
