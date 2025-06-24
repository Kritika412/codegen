"""
Utility functions for text processing, date handling, and common operations.

This module provides helper functions that are used across the application
for data processing and formatting.
"""

import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("harmonia_api")


def normalize_text(text: str) -> str:
    """
    Normalize text by replacing unicode dashes and normalizing characters.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Replace unicode dashes with standard hyphens
    text = text.replace('–', '-').replace('—', '-')
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    return text.strip()


def extract_sprint_number(sprint_name: str) -> Optional[str]:
    """
    Extract sprint number from sprint name like 'Sprint 1', 'Sprint 2', etc.
    
    Args:
        sprint_name: Sprint name string
        
    Returns:
        Sprint number as string or None if not found
    """
    if not sprint_name:
        return None
        
    match = re.match(r"Sprint\s+(\d+)", sprint_name, re.IGNORECASE)
    return match.group(1) if match else None


def calculate_days_remaining(end_date_str: str) -> int:
    """
    Calculate days remaining from current date to end date (inclusive).
    
    For inclusive sprint dates, if today is the end date, there's still 1 day remaining.
    
    Args:
        end_date_str: End date in ISO format
        
    Returns:
        Number of days remaining (0 if past due, inclusive of end date)
    """
    try:
        if not end_date_str:
            return 0
        
        # Parse the date string (assuming ISO format)
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        current_date = datetime.now(end_date.tzinfo)
        
        # Add 1 day to make the calculation inclusive of the end date
        days_remaining = (end_date - current_date).days + 1
        return max(0, days_remaining)  # Don't return negative days
        
    except Exception as e:
        logger.error(f"Error calculating days remaining: {str(e)}")
        return 0


def calculate_end_date(start_date_str: str, duration_days: int) -> str:
    """
    Calculate end date from start date and duration.
    Note: End date is calculated as start_date + (duration_days - 1) 
    to make sprints inclusive of both start and end dates.
    
    Args:
        start_date_str: Start date in ISO format
        duration_days: Duration in days from GitHub iteration
        
    Returns:
        End date in ISO format (start_date + duration_days - 1)
    """
    try:
        if not start_date_str or not duration_days:
            return ""
            
        start_dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        # Subtract 1 day to make the sprint inclusive (Jun 23 - Jun 27 instead of Jun 23 - Jun 28)
        end_dt = start_dt + timedelta(days=duration_days - 1)
        return end_dt.isoformat()
        
    except Exception as e:
        logger.error(f"Error calculating end date: {str(e)}")
        return ""


def validate_sprint_name_format(sprint_name: str) -> bool:
    """
    Validate if sprint name follows expected format.
    
    Args:
        sprint_name: Sprint name to validate
        
    Returns:
        True if format is valid
    """
    if not sprint_name:
        return False
        
    # Check for basic "Sprint X" pattern
    return bool(re.match(r"Sprint\s+\d+", sprint_name, re.IGNORECASE))


def parse_github_repo_url(repo_url: str) -> Dict[str, str]:
    """
    Parse GitHub repository URL into owner and repo name.
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Dictionary with 'owner' and 'repo' keys
    """
    try:
        # Handle both HTTPS and SSH URLs
        if repo_url.startswith('git@github.com:'):
            # SSH format: git@github.com:owner/repo.git
            match = re.match(r'git@github\.com:([^/]+)/(.+?)(?:\.git)?$', repo_url)
        else:
            # HTTPS format: https://github.com/owner/repo or owner/repo
            repo_url = repo_url.replace('https://github.com/', '')
            match = re.match(r'([^/]+)/(.+?)(?:\.git)?$', repo_url)
        
        if match:
            owner, repo = match.groups()
            return {'owner': owner, 'repo': repo}
        else:
            raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
            
    except Exception as e:
        logger.error(f"Error parsing GitHub repo URL: {str(e)}")
        return {'owner': '', 'repo': ''}


def format_timestamp(timestamp_str: str) -> str:
    """
    Format timestamp string for display.
    
    Args:
        timestamp_str: ISO timestamp string
        
    Returns:
        Formatted timestamp string
    """
    try:
        if not timestamp_str:
            return ""
            
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        
    except Exception as e:
        logger.error(f"Error formatting timestamp: {str(e)}")
        return timestamp_str


def safe_int_conversion(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer with default fallback.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
        
    return text[:max_length - len(suffix)] + suffix
