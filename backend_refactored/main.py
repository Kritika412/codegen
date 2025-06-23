"""
Main FastAPI application for the Harmonia Agile Agentic Framework.

This module sets up the FastAPI application with all routes, middleware,
and configuration for the Harmonia API backend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import Config, logger
from app.core.exceptions import (
    HarmoniaException,
    GitHubAPIError,
    ProjectNotFoundError,
    SprintNotFoundError,
    IssueNotFoundError,
    CodexExecutionError
)
from app.api import api_router


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Validate configuration on startup
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise
    
    # Create FastAPI app
    app = FastAPI(
        title="Harmonia Agile Agentic Framework API",
        description="A modular backend system for managing GitHub issues, sprints, and project workflows",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router)
    
    # Include compatibility routes at root level
    from app.api.routes.sprints import compat_router as sprints_compat_router
    app.include_router(sprints_compat_router)
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with basic API information."""
        return {
            "message": "Harmonia Agile Agentic Framework API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/api/health"
        }
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Add startup and shutdown events
    setup_event_handlers(app)
    
    logger.info("FastAPI application created and configured")
    return app


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup custom exception handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.exception_handler(GitHubAPIError)
    async def github_api_error_handler(request, exc: GitHubAPIError):
        logger.error(f"GitHub API error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "GitHub API Error",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_error_handler(request, exc: ProjectNotFoundError):
        logger.error(f"Project not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Project Not Found",
                "message": exc.message
            }
        )
    
    @app.exception_handler(SprintNotFoundError)
    async def sprint_not_found_error_handler(request, exc: SprintNotFoundError):
        logger.error(f"Sprint not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Sprint Not Found",
                "message": exc.message
            }
        )
    
    @app.exception_handler(IssueNotFoundError)
    async def issue_not_found_error_handler(request, exc: IssueNotFoundError):
        logger.error(f"Issue not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Issue Not Found",
                "message": exc.message
            }
        )
    
    @app.exception_handler(CodexExecutionError)
    async def codex_execution_error_handler(request, exc: CodexExecutionError):
        logger.error(f"Codex execution error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Codex Execution Error",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(HarmoniaException)
    async def harmonia_exception_handler(request, exc: HarmoniaException):
        logger.error(f"Harmonia error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Harmonia Error",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )


def setup_event_handlers(app: FastAPI) -> None:
    """
    Setup startup and shutdown event handlers.
    
    Args:
        app: FastAPI application instance
    """
    
    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks."""
        logger.info("Starting Harmonia API...")
        logger.info(f"GitHub Organization: {Config.GITHUB_ORG}")
        logger.info(f"GitHub Project Number: {Config.GITHUB_PROJECT_NUMBER}")
        logger.info(f"Debug Mode: {Config.DEBUG}")
        logger.info("Harmonia API started successfully")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks."""
        logger.info("Shutting down Harmonia API...")
        logger.info("Harmonia API shutdown completed")


# Create the application instance
app = create_app()


def main():
    """
    Main entry point for running the application.
    """
    logger.info("Starting Harmonia API server...")
    
    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
