"""
Health check and system status API routes.

This module provides endpoints for monitoring system health,
checking service status, and validating configuration.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import Config, logger
from app.services.github_service import GitHubService
from app.services.codex_service import CodexService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "message": "Harmonia API is running",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check including all service dependencies.
    
    Returns:
        Comprehensive health status for all services
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "timestamp": "",
            "services": {}
        }
        
        # Check GitHub service
        try:
            github_service = GitHubService()
            # Try a simple API call
            views = github_service.get_project_views()
            health_status["services"]["github"] = {
                "status": "healthy",
                "message": f"Connected to GitHub project with {len(views)} views"
            }
        except Exception as e:
            health_status["services"]["github"] = {
                "status": "unhealthy",
                "message": f"GitHub service error: {str(e)}"
            }
            health_status["overall_status"] = "degraded"
        
        # Check Codex service
        try:
            codex_service = CodexService()
            codex_status = codex_service.get_codex_status()
            all_ready = all(codex_status.values())
            
            health_status["services"]["codex"] = {
                "status": "healthy" if all_ready else "unhealthy",
                "message": "Codex service ready" if all_ready else "Codex service has issues",
                "details": codex_status
            }
            
            if not all_ready:
                health_status["overall_status"] = "degraded"
                
        except Exception as e:
            health_status["services"]["codex"] = {
                "status": "unhealthy",
                "message": f"Codex service error: {str(e)}"
            }
            health_status["overall_status"] = "degraded"
        
        # Check configuration
        try:
            Config.validate()
            health_status["services"]["configuration"] = {
                "status": "healthy",
                "message": "All required configuration present"
            }
        except Exception as e:
            health_status["services"]["configuration"] = {
                "status": "unhealthy",
                "message": f"Configuration error: {str(e)}"
            }
            health_status["overall_status"] = "unhealthy"
        
        # Set timestamp
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        status_code = 200 if health_status["overall_status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "overall_status": "unhealthy",
                "message": f"Health check failed: {str(e)}"
            },
            status_code=503
        )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for deployment environments.
    
    Returns:
        Readiness status for the service
    """
    try:
        # Check essential services are ready
        github_service = GitHubService()
        
        # Simple validation that we can connect to GitHub
        try:
            github_service.get_project_views()
            return {"ready": True, "message": "Service is ready to handle requests"}
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return JSONResponse(
                content={
                    "ready": False,
                    "message": f"Service not ready: {str(e)}"
                },
                status_code=503
            )
            
    except Exception as e:
        logger.error(f"Readiness check error: {str(e)}")
        return JSONResponse(
            content={
                "ready": False,
                "message": f"Readiness check error: {str(e)}"
            },
            status_code=503
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check for deployment environments.
    
    Returns:
        Basic liveness status
    """
    return {"alive": True, "message": "Service is alive"}


@router.get("/config")
async def config_status():
    """
    Check configuration status (without exposing sensitive values).
    
    Returns:
        Configuration validation status
    """
    try:
        config_status = {
            "github_token_configured": bool(Config.GITHUB_TOKEN),
            "github_repo_configured": bool(Config.GITHUB_REPO),
            "github_org_configured": bool(Config.GITHUB_ORG),
            "openai_api_key_configured": bool(Config.OPENAI_API_KEY),
            "project_number": Config.GITHUB_PROJECT_NUMBER,
            "debug_mode": Config.DEBUG
        }
        
        # Validate configuration
        try:
            Config.validate()
            config_status["valid"] = True
            config_status["message"] = "Configuration is valid"
        except Exception as e:
            config_status["valid"] = False
            config_status["message"] = f"Configuration error: {str(e)}"
        
        return config_status
        
    except Exception as e:
        logger.error(f"Config status check failed: {str(e)}")
        return JSONResponse(
            content={
                "valid": False,
                "message": f"Config check failed: {str(e)}"
            },
            status_code=500
        )
