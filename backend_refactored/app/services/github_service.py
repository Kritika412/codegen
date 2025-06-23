"""
GitHub API service for interacting with GitHub repositories, issues, and projects.

This service encapsulates all GitHub API interactions and provides a clean interface
for the rest of the application.
"""

import requests
from typing import List, Dict, Optional, Any
from github import Github
from github.GithubException import GithubException

from app.core.config import Config, logger
from app.core.exceptions import (
    GitHubAPIError,
    ProjectNotFoundError,
    SprintNotFoundError,
    IssueNotFoundError
)
from app.utils.helpers import (
    normalize_text,
    extract_sprint_number,
    calculate_end_date
)


class GitHubService:
    """
    Service class for GitHub API operations.
    
    Handles authentication, API calls, and data processing for GitHub
    repositories, issues, projects, and iterations.
    """
    
    def __init__(self):
        """Initialize GitHub service with authentication."""
        if not Config.GITHUB_TOKEN:
            raise GitHubAPIError("GitHub token not configured")
            
        self.token = Config.GITHUB_TOKEN
        self.org = Config.GITHUB_ORG
        self.project_number = Config.GITHUB_PROJECT_NUMBER
        self.github_client = Github(self.token)
        
        # Headers for GraphQL requests
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _make_graphql_request(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a GraphQL request to GitHub API.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Response data dictionary
            
        Raises:
            GitHubAPIError: If the request fails
        """
        url = "https://api.github.com/graphql"
        data = {"query": query, "variables": variables}
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            result = response.json()
            
            if 'errors' in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                raise GitHubAPIError(f"GraphQL errors: {result['errors']}")
                
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in GraphQL request: {str(e)}")
            raise GitHubAPIError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in GraphQL request: {str(e)}")
            raise GitHubAPIError(f"Request error: {str(e)}")
    
    def get_project_views(self) -> List[Dict[str, str]]:
        """
        Get all views from the GitHub project.
        
        Returns:
            List of view dictionaries with id and name
            
        Raises:
            ProjectNotFoundError: If project is not found
        """
        query = """
        query($org: String!, $number: Int!) {
            organization(login: $org) {
                projectV2(number: $number) {
                    id
                    title
                    views(first: 50) {
                        nodes {
                            id
                            name
                            layout
                        }
                    }
                }
            }
        }
        """
        
        variables = {"org": self.org, "number": self.project_number}
        result = self._make_graphql_request(query, variables)
        
        if not result.get('data', {}).get('organization', {}).get('projectV2'):
            raise ProjectNotFoundError(f"Project {self.project_number} not found in organization {self.org}")
        
        project = result['data']['organization']['projectV2']
        return project['views']['nodes']
    
    def get_iteration_details(self, iteration_title: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific iteration.
        
        Args:
            iteration_title: Title of the iteration to find
            
        Returns:
            Dictionary with iteration details
        """
        query = """
        query($org: String!, $number: Int!) {
            organization(login: $org) {
                projectV2(number: $number) {
                    id
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2IterationField {
                                id
                                name
                                configuration {
                                    iterations {
                                        id
                                        title
                                        startDate
                                        duration
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {"org": self.org, "number": self.project_number}
        result = self._make_graphql_request(query, variables)
        
        project = result.get('data', {}).get('organization', {}).get('projectV2', {})
        
        for field in project.get('fields', {}).get('nodes', []):
            if 'configuration' in field and 'iterations' in field['configuration']:
                for iteration in field['configuration']['iterations']:
                    if iteration['title'] == iteration_title:
                        return {
                            'id': iteration['id'],
                            'title': iteration['title'],
                            'start_date': iteration['startDate'],
                            'duration': iteration['duration']
                        }
        
        return {}
    
    def get_project_items_by_iteration(self, sprint_name: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get issues from a specific sprint iteration with optional status filtering.
        
        Args:
            sprint_name: Name of the sprint view
            status_filter: Optional status to filter by
            
        Returns:
            List of issue dictionaries with status information
            
        Raises:
            SprintNotFoundError: If sprint view is not found
        """
        # Extract sprint number and validate
        sprint_number = extract_sprint_number(sprint_name)
        if not sprint_number:
            raise SprintNotFoundError(f"Could not extract sprint number from '{sprint_name}'")
        
        expected_iteration = f"Iteration {sprint_number}"
        
        # Verify sprint view exists
        views = self.get_project_views()
        sprint_view_found = any(view['name'] == sprint_name for view in views)
        
        if not sprint_view_found:
            available_views = [view['name'] for view in views]
            raise SprintNotFoundError(f"Sprint view '{sprint_name}' not found. Available views: {available_views}")
        
        # Get project ID
        project_id = self._get_project_id()
        
        # Get project items with field values
        items = self._get_project_items(project_id)
        
        # Filter items by iteration and status
        return self._filter_items_by_iteration_and_status(items, expected_iteration, status_filter)
    
    def _get_project_id(self) -> str:
        """Get the project ID."""
        query = """
        query($org: String!, $number: Int!) {
            organization(login: $org) {
                projectV2(number: $number) {
                    id
                }
            }
        }
        """
        
        variables = {"org": self.org, "number": self.project_number}
        result = self._make_graphql_request(query, variables)
        
        project = result.get('data', {}).get('organization', {}).get('projectV2')
        if not project:
            raise ProjectNotFoundError(f"Project {self.project_number} not found")
            
        return project['id']
    
    def _get_project_items(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all items from the project."""
        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 100) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    id
                                    number
                                    title
                                    body
                                    state
                                    createdAt
                                    updatedAt
                                    assignees(first: 1) {
                                        nodes {
                                            login
                                        }
                                    }
                                    labels(first: 10) {
                                        nodes {
                                            name
                                        }
                                    }
                                    repository {
                                        nameWithOwner
                                    }
                                    url
                                }
                                ... on PullRequest {
                                    id
                                    number
                                    title
                                    body
                                    state
                                    createdAt
                                    updatedAt
                                    assignees(first: 1) {
                                        nodes {
                                            login
                                        }
                                    }
                                    labels(first: 10) {
                                        nodes {
                                            name
                                        }
                                    }
                                    repository {
                                        nameWithOwner
                                    }
                                    url
                                }
                                ... on DraftIssue {
                                    id
                                    title
                                    body
                                    createdAt
                                    updatedAt
                                    assignees(first: 1) {
                                        nodes {
                                            login
                                        }
                                    }
                                }
                            }
                            fieldValues(first: 10) {
                                nodes {
                                    ... on ProjectV2ItemFieldTextValue {
                                        text
                                        field {
                                            ... on ProjectV2Field {
                                                name
                                            }
                                        }
                                    }
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                        field {
                                            ... on ProjectV2SingleSelectField {
                                                name
                                            }
                                        }
                                    }
                                    ... on ProjectV2ItemFieldIterationValue {
                                        title
                                        startDate
                                        duration
                                        iterationId
                                        field {
                                            ... on ProjectV2IterationField {
                                                name
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {"projectId": project_id}
        result = self._make_graphql_request(query, variables)
        
        items = result.get('data', {}).get('node', {}).get('items', {}).get('nodes', [])
        return items
    
    def _filter_items_by_iteration_and_status(self, items: List[Dict[str, Any]], 
                                            expected_iteration: str, 
                                            status_filter: Optional[str]) -> List[Dict[str, Any]]:
        """Filter items by iteration and optionally by status."""
        filtered_issues = []
        
        for item in items:
            if not item.get('content'):
                continue
            
            content = item['content']
            
            # Skip pull requests if you only want issues
            if 'url' in content and '/pull/' in content['url']:
                continue
            
            field_values = item.get('fieldValues', {}).get('nodes', [])
            iteration_title, status = self._extract_field_values(field_values)
            
            # Check if item belongs to the expected iteration
            if iteration_title == normalize_text(expected_iteration):
                # Apply status filter if provided
                if status_filter is None or (status and status.lower() == status_filter.lower()):
                    filtered_issues.append({
                        'item': item,
                        'content': content,
                        'status': status or 'Unknown',
                        'issue_state': content.get('state', 'UNKNOWN')
                    })
        
        return filtered_issues
    
    def _extract_field_values(self, field_values: List[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
        """Extract iteration and status information from field values."""
        iteration_title = None
        status = None
        
        logger.debug(f"Extracting field values from {len(field_values)} field values")
        
        for field_value in field_values:
            if 'field' in field_value and field_value['field']:
                field_name = field_value['field'].get('name', '').lower()
                logger.debug(f"Processing field: '{field_name}'")
                
                # Check iteration
                if 'title' in field_value:
                    iteration_title = normalize_text(field_value.get('title', ''))
                    logger.debug(f"Found iteration title: '{iteration_title}'")
                
                # Check status
                if field_name == 'status':
                    status = field_value.get('name') or field_value.get('text')
                    logger.debug(f"Found status: '{status}'")
        
        logger.debug(f"Final extracted values - iteration: '{iteration_title}', status: '{status}'")
        return iteration_title, status
    
    def get_sprint_views(self) -> List[Dict[str, Any]]:
        """
        Get all sprint views from the project.
        
        Returns:
            List of sprint view dictionaries
        """
        views = self.get_project_views()
        sprint_views = []
        
        for view in views:
            view_name = view['name']
            if view_name.startswith("Sprint"):
                sprint_views.append(view)
        
        return sprint_views
    
    def update_issue_description(self, issue_number: int, repo_name: str, new_body: str) -> bool:
        """
        Update an issue's description using GitHub REST API.
        
        Args:
            issue_number: GitHub issue number
            repo_name: Repository name (e.g., "owner/repo")
            new_body: New issue description
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            IssueNotFoundError: If issue is not found
        """
        try:
            repo = self.github_client.get_repo(repo_name)
            issue = repo.get_issue(issue_number)
            issue.edit(body=new_body)
            logger.info(f"Successfully updated issue #{issue_number} description")
            return True
            
        except GithubException as e:
            if e.status == 404:
                raise IssueNotFoundError(f"Issue #{issue_number} not found in repository {repo_name}")
            else:
                logger.error(f"GitHub API error updating issue #{issue_number}: {str(e)}")
                raise GitHubAPIError(f"Failed to update issue: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating issue #{issue_number}: {str(e)}")
            return False
    
    def get_pull_requests(self, repo_name: str, state: str = "open") -> List[Dict[str, Any]]:
        """
        Get pull requests from a repository.
        
        Args:
            repo_name: Repository name
            state: Pull request state (open, closed, all)
            
        Returns:
            List of pull request dictionaries
        """
        try:
            repo = self.github_client.get_repo(repo_name)
            prs = repo.get_pulls(state=state, sort="created")
            
            pr_list = []
            for pr in prs:
                pr_data = {
                    "id": pr.number,
                    "number": pr.number,
                    "title": pr.title,
                    "author": pr.user.login,
                    "branch": pr.head.ref,
                    "status": "ci-passed" if pr.mergeable_state == "clean" else "needs-review",
                    "url": pr.html_url,
                    "created_at": pr.created_at.isoformat() if pr.created_at else ""
                }
                pr_list.append(pr_data)
            
            return pr_list
            
        except GithubException as e:
            logger.error(f"GitHub API error getting pull requests: {str(e)}")
            raise GitHubAPIError(f"Failed to get pull requests: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting pull requests: {str(e)}")
            raise GitHubAPIError(f"Error getting pull requests: {str(e)}")
    
    def create_issue(self, repo_name: str, title: str, body: str = "", 
                    assignee: Optional[str] = None, labels: List[str] = None) -> Dict[str, Any]:
        """
        Create a new issue in a repository.
        
        Args:
            repo_name: Repository name
            title: Issue title
            body: Issue description
            assignee: Assignee username
            labels: List of label names
            
        Returns:
            Dictionary with created issue information
        """
        try:
            repo = self.github_client.get_repo(repo_name)
            
            # Create the issue
            issue = repo.create_issue(
                title=title,
                body=body or "",
                assignee=assignee,
                labels=labels or []
            )
            
            logger.info(f"Successfully created issue #{issue.number} in {repo_name}")
            
            return {
                "id": str(issue.id),
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "url": issue.html_url,
                "created_at": issue.created_at.isoformat() if issue.created_at else ""
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error creating issue: {str(e)}")
            raise GitHubAPIError(f"Failed to create issue: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating issue: {str(e)}")
            raise GitHubAPIError(f"Error creating issue: {str(e)}")
