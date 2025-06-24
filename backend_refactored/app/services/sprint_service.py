"""
Sprint management service for handling sprint-related operations.

This service provides high-level operations for managing sprints, calculating
metrics, and generating sprint summaries.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.services.github_service import GitHubService
from app.models.schemas import Sprint, SprintSummary
from app.utils.helpers import (
    extract_sprint_number,
    calculate_end_date,
    calculate_days_remaining
)
from app.core.config import logger
from app.core.exceptions import SprintNotFoundError


class SprintService:
    """
    Service class for sprint-related operations.
    
    Handles sprint data processing, metrics calculation, and summary generation.
    """
    
    def __init__(self):
        """Initialize sprint service with GitHub service dependency."""
        self.github_service = GitHubService()
    
    def get_all_sprints(self) -> List[Sprint]:
        """
        Get all sprint views from GitHub project and convert to Sprint objects.
        
        Returns:
            List of Sprint objects sorted by sprint number (descending)
        """
        try:
            # Get sprint views from GitHub
            sprint_views = self.github_service.get_sprint_views()
            sprints = []
            
            # Get iteration details for date information
            iteration_details = self._get_all_iteration_details()
            
            for view in sprint_views:
                sprint = self._convert_view_to_sprint(view, iteration_details)
                if sprint:
                    sprints.append(sprint)
            
            # Sort by sprint number (descending - newest first)
            sprints.sort(key=lambda s: int(s.id.replace("sprint", "")), reverse=True)
            
            logger.info(f"Retrieved {len(sprints)} sprints")
            return sprints
            
        except Exception as e:
            logger.error(f"Error getting sprints: {str(e)}")
            raise
    
    def get_sprint_summary(self, sprint_name: str) -> SprintSummary:
        """
        Generate comprehensive sprint summary with metrics.
        
        Args:
            sprint_name: Name of the sprint to analyze
            
        Returns:
            SprintSummary with all metrics and information
        """
        try:
            # Get all issues from the sprint
            all_issues = self.github_service.get_project_items_by_iteration(
                sprint_name=sprint_name,
                status_filter=None
            )
            
            # Calculate status counts
            status_counts = self._calculate_status_counts(all_issues)
            
            # Get iteration details for dates
            sprint_number = extract_sprint_number(sprint_name)
            iteration_title = f"Iteration {sprint_number}" if sprint_number else ""
            iteration_details = self.github_service.get_iteration_details(iteration_title)
            
            # Calculate dates
            start_date = iteration_details.get('start_date', '')
            duration = iteration_details.get('duration', 0)
            end_date = calculate_end_date(start_date, duration) if start_date and duration else ''
            days_remaining = calculate_days_remaining(end_date)
            
            # TODO: Implement actual sprint goals retrieval
            sprint_goals = "Sprint goals from API"
            
            summary = SprintSummary(
                current_sprint=sprint_name,
                start_date=start_date,
                end_date=end_date,
                days_remaining=days_remaining,
                sprint_goals=sprint_goals,
                total_issues=status_counts['total'],
                backlog=status_counts['backlog'],
                ready=status_counts['ready'],
                in_progress=status_counts['in progress'],  # Use space, not underscore
                in_review=status_counts['in review']        # Use space, not underscore
            )
            
            logger.info(f"Generated summary for sprint '{sprint_name}' with {status_counts['total']} issues")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating sprint summary for '{sprint_name}': {str(e)}")
            raise
    
    def _get_all_iteration_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get details for all iterations to map sprint numbers to dates.
        
        Returns:
            Dictionary mapping iteration titles to their details
        """
        # This could be optimized by caching iteration details
        # For now, we'll get them as needed in convert_view_to_sprint
        return {}
    
    def _convert_view_to_sprint(self, view: Dict[str, str], 
                              iteration_details: Dict[str, Dict[str, Any]]) -> Sprint:
        """
        Convert a GitHub project view to a Sprint object.
        
        Args:
            view: GitHub project view dictionary
            iteration_details: Cached iteration details
            
        Returns:
            Sprint object or None if conversion fails
        """
        try:
            view_name = view['name']
            
            # Extract sprint number
            sprint_number = extract_sprint_number(view_name)
            if not sprint_number:
                logger.warning(f"Could not extract sprint number from view: {view_name}")
                return None
            
            # Get iteration details
            iteration_title = f"Iteration {sprint_number}"
            iteration_info = self.github_service.get_iteration_details(iteration_title)
            
            start_date = iteration_info.get('start_date', '')
            duration = iteration_info.get('duration', 0)
            end_date = calculate_end_date(start_date, duration) if start_date and duration else ''
            
            # Format the sprint name with dates
            if start_date and end_date:
                from datetime import datetime
                try:
                    start_dt = datetime.fromisoformat(start_date)
                    end_dt = datetime.fromisoformat(end_date.replace('T00:00:00', ''))
                    date_range = f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d')}"
                    
                    # Check if this is the current sprint
                    current_date = datetime.now().date()
                    is_current = start_dt.date() <= current_date <= end_dt.date()
                    
                    if is_current:
                        display_name = f"{view_name}: {date_range} (current)"
                    else:
                        display_name = f"{view_name}: {date_range}"
                        
                except Exception as e:
                    logger.warning(f"Error formatting dates for sprint {view_name}: {e}")
                    display_name = view_name
                    is_current = False
            else:
                display_name = view_name
                is_current = False
            
            return Sprint(
                id=f"sprint{sprint_number}",
                name=display_name,  # Display name with dates
                original_name=view_name,  # Original name for API calls
                start_date=start_date,
                end_date=end_date,
                iteration_id=iteration_info.get('id', ''),
                duration=duration,
                is_current=is_current
            )
            
        except Exception as e:
            logger.error(f"Error converting view to sprint: {str(e)}")
            return None
    
    def _calculate_status_counts(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Calculate issue counts by status using exact matching like the original code.
        
        This matches the original logic exactly: direct status name matching
        without complex mappings. Uses dynamic status discovery.
        
        Args:
            issues: List of issue dictionaries
            
        Returns:
            Dictionary with status counts
        """
        # First, discover all unique statuses in the data
        unique_statuses = set()
        for issue in issues:
            status = issue.get('status', '').lower() if issue.get('status') else 'unknown'
            if status and status != 'unknown':
                unique_statuses.add(status)
        
        logger.info(f"Discovered statuses in project: {sorted(unique_statuses)}")
        
        # Initialize counts with the standard expected statuses plus any discovered ones
        status_counts = {
            'backlog': 0,
            'ready': 0,
            'in progress': 0,  # May not exist in project yet
            'in review': 0,    # May not exist in project yet
            'total': len(issues)
        }
        
        # Add any additional statuses found in the project
        for status in unique_statuses:
            if status not in status_counts:
                status_counts[status] = 0
                logger.info(f"Added discovered status '{status}' to counts")
        
        logger.debug(f"Calculating status counts for {len(issues)} issues")
        
        for issue in issues:
            status = issue.get('status', '').lower() if issue.get('status') else 'unknown'
            logger.debug(f"Issue status: '{status}'")
            
            # Use exact matching like the original code
            if status in status_counts:
                status_counts[status] += 1
                logger.debug(f"Incremented {status} count to {status_counts[status]}")
            else:
                logger.debug(f"Status '{status}' not found in expected statuses: {list(status_counts.keys())}")
        
        logger.info(f"Final status counts: {status_counts}")
        return status_counts
    
    def get_sprint_issues_by_status(self, sprint_name: str, status: str) -> List[Dict[str, Any]]:
        """
        Get issues from a sprint filtered by specific status.
        
        Args:
            sprint_name: Name of the sprint
            status: Status to filter by
            
        Returns:
            List of filtered issue dictionaries
        """
        try:
            issues = self.github_service.get_project_items_by_iteration(
                sprint_name=sprint_name,
                status_filter=status
            )
            
            logger.info(f"Retrieved {len(issues)} issues with status '{status}' from sprint '{sprint_name}'")
            return issues
            
        except Exception as e:
            logger.error(f"Error getting issues by status: {str(e)}")
            raise
    
    def validate_sprint_exists(self, sprint_name: str) -> bool:
        """
        Validate that a sprint view exists.
        
        Args:
            sprint_name: Name of the sprint to validate
            
        Returns:
            True if sprint exists, False otherwise
        """
        try:
            views = self.github_service.get_project_views()
            return any(view['name'] == sprint_name for view in views)
            
        except Exception as e:
            logger.error(f"Error validating sprint existence: {str(e)}")
            return False
