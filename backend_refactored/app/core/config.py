"""
Configuration management for the Harmonia API.

This module handles all configuration settings including environment variables,
logging setup, and application constants.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """
    Application configuration class.
    
    Centralizes all configuration values and provides validation.
    """
    
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "")
    GITHUB_ORG: str = os.getenv("GITHUB_ORG", "harmoniaailabs")
    GITHUB_PROJECT_NUMBER: int = int(os.getenv("GITHUB_PROJECT_NUMBER", "5"))
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
    ]
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/harmonia_api.log")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration values.
        
        Raises:
            ValueError: If required configuration is missing
        """
        if not cls.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not cls.GITHUB_REPO:
            raise ValueError("GITHUB_REPO environment variable is required")


def setup_logging() -> logging.Logger:
    """
    Configure logging for the application.
    
    Returns:
        Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.dirname(Config.LOG_FILE)
    if logs_dir and not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create logger
    logger = logging.getLogger("harmonia_api")
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler for warnings and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Initialize logger
logger = setup_logging()
