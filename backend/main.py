from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from github import Github
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pydantic import BaseModel
import subprocess
import os
import requests
import re
import unicodedata
import logging
from logging.handlers import RotatingFileHandler
from fastapi import WebSocket, WebSocketDisconnect
from terminal_service import terminal_manager
import asyncio
from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
token = GITHUB_TOKEN
org = 'harmoniaailabs'  # Changed from username to organization
project_number = 1 # Updated project number

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in environment variables")
if not GITHUB_REPO:
    raise ValueError("GITHUB_REPO not found in environment variables")

# Setup logging
def setup_logging():
    """Setup logging configuration with rotating file handler"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create logger
    logger = logging.getLogger("harmonia_api")
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Prevent propagation to root logger (this stops console output)
    logger.propagate = False
    
    # Create rotating file handler (max 10MB, keep 5 backup files)
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, "harmonia_api.log"),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler for errors and warnings only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Changed from ERROR to WARNING
    
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

g = Github(GITHUB_TOKEN)
app = FastAPI(title="Harmonia Agile Agentic Framework API")

# CORS for frontend dev
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],  # Allow all origins for app runner
   allow_credentials=False,  # Set to False when using allow_origins=["*"]
   allow_methods=["*"],
   allow_headers=["*"],
)

# Pydantic models
class Issue(BaseModel):
   id: str  # GitHub IDs are strings, not integers
   number: int
   title: str
   assignee: Optional[str]
   status: str
   created_at: str
   updated_at: str
   body: Optional[str]
   labels: List[str]
   repo: str
   url: Optional[str]  # Added URL field for GitHub links

class Sprint(BaseModel):
   id: str
   name: str
   start_date: str
   end_date: str
   iteration_id: Optional[str] = None
   duration: Optional[int] = None

class SprintSummary(BaseModel):
   current_sprint: str
   start_date: str
   end_date: str
   days_remaining: int
   sprint_goals: str
   total_issues: int
   backlog: int
   ready: int
   in_progress: int
   in_review: int

class IssueUpdateRequest(BaseModel):
   body: str

class PromptRequest(BaseModel):
   prompt: str
   repo: str
   title: str

class Repository(BaseModel):
    id: str
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    html_url: str
    default_branch: str
    updated_at: str

class Project(BaseModel):
    id: str
    number: int
    title: str
    url: str
    repository_name: Optional[str] = None
    repository_url: Optional[str] = None
    created_at: str
    updated_at: str

class RepositoryWithProjects(BaseModel):
    id: str
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    html_url: str
    default_branch: str
    updated_at: str
    projects: List[Project] = []

# Helper functions
def normalize_text(text):
   """Normalize text by replacing unicode dashes and normalizing characters"""
   text = text.replace('–', '-').replace('—', '-')
   text = unicodedata.normalize('NFKD', text)
   return text.strip()

def extract_sprint_number(sprint_name: str) -> Optional[str]:
   """Extract sprint number from sprint name like 'Sprint 1', 'Sprint 2', etc."""
   match = re.match(r"Sprint\s+(\d+)", sprint_name, re.IGNORECASE)
   return match.group(1) if match else None
# Add this enhanced project access handling to main.py

def check_project_access(project_number: int) -> dict:
    """
    Check if we have proper access to a specific project and return access details.
    """
    url = "https://api.github.com/graphql"
    
    # Simple query to test project access
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
                public
                closed
                readme
                shortDescription
                url
                viewerCanUpdate
                viewerCanClose
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": org,
            "number": project_number
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'errors' in result:
            return {
                "accessible": False,
                "error": f"GraphQL errors: {result['errors']}",
                "permissions": None
            }
        
        if 'data' not in result or not result['data']['organization'] or not result['data']['organization']['projectV2']:
            return {
                "accessible": False,
                "error": f"Project {project_number} not found or not accessible",
                "permissions": None
            }
        
        project_data = result['data']['organization']['projectV2']
        return {
            "accessible": True,
            "error": None,
            "permissions": {
                "can_view": True,
                "can_update": project_data.get('viewerCanUpdate', False),
                "can_close": project_data.get('viewerCanClose', False),
                "is_public": project_data.get('public', False),
                "is_closed": project_data.get('closed', False)
            },
            "project_info": {
                "title": project_data.get('title', f'Project {project_number}'),
                "url": project_data.get('url', ''),
                "description": project_data.get('shortDescription', '')
            }
        }
        
    except Exception as e:
        return {
            "accessible": False,
            "error": f"Error checking project access: {str(e)}",
            "permissions": None
        }

def get_project_issues_with_fallback(project_number: int, sprint_name: str, status_filter: Optional[str] = None) -> List[dict]:
    """
    Enhanced version that handles private projects and permission issues gracefully.
    """
    try:
        # First check if we have access to the project
        access_check = check_project_access(project_number)
        
        if not access_check["accessible"]:
            logger.warning(f"Project {project_number} not accessible: {access_check['error']}")
            return []
        
        logger.info(f"Project {project_number} access confirmed. Permissions: {access_check['permissions']}")
        
        # Try to get issues using the original method
        try:
            return get_project_issues_by_sprint_and_status(
                token=GITHUB_TOKEN,
                org=org,
                project_number=project_number,
                sprint_name=sprint_name,
                status_filter=status_filter
            )
        except Exception as e:
            logger.error(f"Error fetching issues from project {project_number}: {str(e)}")
            
            # If it's a permission error, try alternative approach
            if "permission" in str(e).lower() or "forbidden" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.info(f"Permission issue detected for project {project_number}. Trying alternative approach...")
                return get_project_issues_alternative_method(project_number, sprint_name, status_filter)
            else:
                raise e
                
    except Exception as e:
        logger.error(f"Error in get_project_issues_with_fallback: {str(e)}")
        return []

def get_project_issues_alternative_method(project_number: int, sprint_name: str, status_filter: Optional[str] = None) -> List[dict]:
    """
    Alternative method to get project issues when the main GraphQL query fails due to permissions.
    This uses a more basic approach that might work with limited permissions.
    """
    url = "https://api.github.com/graphql"
    
    # Simpler query that requires fewer permissions
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
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
                                url
                                repository {
                                    nameWithOwner
                                }
                            }
                            ... on DraftIssue {
                                id
                                title
                                body
                                createdAt
                                updatedAt
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": org,
            "number": project_number
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'errors' in result:
            logger.error(f"GraphQL errors in alternative method: {result['errors']}")
            return []
        
        if 'data' not in result or not result['data']['organization'] or not result['data']['organization']['projectV2']:
            logger.error(f"No project data in alternative method for project {project_number}")
            return []
        
        items = result['data']['organization']['projectV2']['items']['nodes']
        
        # Since we can't filter by sprint/iteration in this simpler query,
        # we'll return all items and let the frontend handle filtering if needed
        filtered_issues = []
        
        for item in items:
            if not item['content']:
                continue
                
            content = item['content']
            
            # Skip pull requests
            if 'url' in content and '/pull/' in content['url']:
                continue
            
            # Create a simplified issue structure
            filtered_issues.append({
                'item': item,
                'content': content,
                'status': 'Unknown',  # We can't get status from this simpler query
                'issue_state': content.get('state', 'UNKNOWN')
            })
        
        logger.info(f"Alternative method returned {len(filtered_issues)} items from project {project_number}")
        return filtered_issues
        
    except Exception as e:
        logger.error(f"Error in alternative method for project {project_number}: {str(e)}")
        return []

# Enhanced issues endpoint with better error handling for private projects
def get_project_issues_enhanced(project_number: int, sprint_name: str, status_filter: Optional[str] = None) -> List[dict]:
    """
    Enhanced function to get issues from a specific iteration/sprint with better error handling.
    Works with the hail project and handles various content types (issues, draft issues, etc.)
    """
    url = "https://api.github.com/graphql"
    
    # Enhanced query that gets ALL project items with their iteration and status values
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
                items(first: 100) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
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
                                url
                                assignees(first: 5) {
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
                            }
                            ... on PullRequest {
                                id
                                number
                                title
                                body
                                state
                                createdAt
                                updatedAt
                                url
                                assignees(first: 5) {
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
                            }
                            ... on DraftIssue {
                                id
                                title
                                body
                                createdAt
                                updatedAt
                                assignees(first: 5) {
                                    nodes {
                                        login
                                    }
                                }
                            }
                        }
                        fieldValues(first: 20) {
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
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": "harmoniaailabs",
            "number": project_number
        }
    }
    
    try:
        logger.info(f"Fetching issues from project {project_number} for sprint '{sprint_name}'")
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            # Continue if we have some data
            if 'data' not in result:
                raise Exception(f"GraphQL errors: {result['errors']}")
        
        if not result.get('data', {}).get('organization', {}).get('projectV2'):
            raise Exception(f"Project {project_number} not found or not accessible")
        
        items = result['data']['organization']['projectV2']['items']['nodes']
        logger.info(f"Found {len(items)} total items in project")
        
        # Filter items by iteration and optionally by status
        filtered_issues = []
        
        for item in items:
            if not item.get('content'):
                logger.debug("Skipping item without content")
                continue
            
            content = item['content']
            
            # Extract field values
            iteration_title = None
            status = "Unknown"
            
            for field_value in item.get('fieldValues', {}).get('nodes', []):
                if not field_value:
                    continue
                
                field_name = ""
                if 'field' in field_value and field_value['field']:
                    field_name = field_value['field'].get('name', '').lower()
                
                # Get iteration
                if 'title' in field_value and field_name in ['iteration', 'sprint']:
                    iteration_title = normalize_text(field_value.get('title', ''))
                
                # Get status
                if field_name == 'status':
                    status = field_value.get('name') or field_value.get('text') or "Unknown"
            
            # Check if this item belongs to the requested sprint
            sprint_matches = False
            if iteration_title:
                # Try exact match first
                if iteration_title == normalize_text(sprint_name):
                    sprint_matches = True
                # Try partial match (e.g., "Iteration 15" matches "Iteration 15 (Current)")
                elif sprint_name in iteration_title or iteration_title in sprint_name:
                    sprint_matches = True
                # Extract numbers and compare
                else:
                    import re
                    sprint_num = re.search(r'(\d+)', sprint_name)
                    iter_num = re.search(r'(\d+)', iteration_title)
                    if sprint_num and iter_num and sprint_num.group(1) == iter_num.group(1):
                        sprint_matches = True
            
            if not sprint_matches:
                continue
            
            # Apply status filter if provided
            if status_filter and status.lower() != status_filter.lower():
                continue
            
            # Skip pull requests if you only want issues (optional)
            if 'url' in content and '/pull/' in content['url']:
                logger.debug(f"Skipping pull request: {content.get('title', 'Unknown')}")
                continue
            
            filtered_issues.append({
                'item': item,
                'content': content,
                'status': status,
                'iteration': iteration_title,
                'issue_state': content.get('state', 'UNKNOWN')
            })
            
            logger.debug(f"Added issue: {content.get('title', 'Unknown')} (Status: {status})")
        
        logger.info(f"Filtered to {len(filtered_issues)} issues for sprint '{sprint_name}'")
        return filtered_issues
        
    except Exception as e:
        logger.error(f"Error fetching issues: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

@app.get("/api/issues", response_model=List[Issue])
def get_issues_enhanced_endpoint(sprint_name: Optional[str] = None, status: Optional[str] = None, project_number: Optional[int] = None):
    """
    Enhanced issues endpoint that properly handles the hail project.
    """
    try:
        if not sprint_name:
            raise HTTPException(status_code=400, detail="sprint_name parameter is required")
        
        # Use provided project number or default to 1 (hail project)
        actual_project_number = project_number if project_number is not None else 1
        
        logger.info(f"Fetching issues from project {actual_project_number} for sprint '{sprint_name}'")
        
        # Use enhanced method
        filtered_issues = get_project_issues_enhanced(
            project_number=actual_project_number,
            sprint_name=sprint_name,
            status_filter=status
        )
        
        if not filtered_issues:
            logger.warning(f"No issues found for project {actual_project_number}, sprint '{sprint_name}'")
            # Check if project is accessible
            access_check = check_project_access(actual_project_number)
            if not access_check["accessible"]:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Access denied to project {actual_project_number}. Error: {access_check['error']}"
                )
        
        results = []
        
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
            
            # Get issue number (0 for draft issues)
            issue_number = content.get('number', 0)
            
            # Create Issue object
            issue = Issue(
                id=content['id'],
                number=issue_number,
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
            
            results.append(issue)
        
        logger.info(f"Successfully returned {len(results)} issues for project {actual_project_number}, sprint '{sprint_name}'")
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in get_issues_enhanced_endpoint: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        error_detail = f"Issue fetch error for project {project_number or 1}: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)
    
    
# Add a specific endpoint to check project access
@app.get("/api/projects/{project_number}/access")
def check_project_access_endpoint(project_number: int):
    """
    Check access to a specific project and return detailed information.
    """
    try:
        access_info = check_project_access(project_number)
        return {
            "project_number": project_number,
            "accessible": access_info["accessible"],
            "error": access_info["error"],
            "permissions": access_info["permissions"],
            "project_info": access_info.get("project_info", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "project_number": project_number,
            "accessible": False,
            "error": f"Error checking access: {str(e)}",
            "permissions": None,
            "project_info": {},
            "timestamp": datetime.now().isoformat()
        }
def calculate_days_remaining(end_date_str: str) -> int:
   """Calculate days remaining from current date to end date"""
   try:
       if not end_date_str:
           return 0
       
       # Parse the date string (assuming ISO format)
       end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
       current_date = datetime.now(end_date.tzinfo)
       
       days_remaining = (end_date - current_date).days
       return max(0, days_remaining)  # Don't return negative days
   except Exception as e:
       logger.error(f"Error calculating days remaining: {str(e)}")
       return 0

def get_iteration_details(token: str, org: str, project_number: int, iteration_title: str) -> Dict:
   """Get detailed information about a specific iteration including dates"""
   url = "https://api.github.com/graphql"
   
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
   
   headers = {
       "Authorization": f"Bearer {token}",
       "Content-Type": "application/json"
   }
   
   data = {
       "query": query,
       "variables": {
           "org": org,
           "number": project_number
       }
   }
   
   try:
       response = requests.post(url, headers=headers, json=data)
       response.raise_for_status()
       result = response.json()
       
       if 'errors' in result:
           logger.error(f"GraphQL errors: {result['errors']}")
           return {}
       
       # Find the iteration field and extract iteration details
       project = result['data']['organization']['projectV2']
       for field in project['fields']['nodes']:
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
   except Exception as e:
       logger.error(f"Error getting iteration details: {str(e)}")
       return {}
   
@app.get("/api/projects", response_model=List[Project])
def get_organization_projects():
    """Get all projects from the harmoniaailabs organization."""
    try:
        url = "https://api.github.com/graphql"
        query = """
        query($org: String!) {
            organization(login: $org) {
                projectsV2(first: 50) {
                    nodes {
                        id
                        number
                        title
                        url
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
        
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "query": query,
            "variables": {"org": "harmoniaailabs"}
        }
        
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            projects = []
            
            if 'data' in result and result['data']['organization']:
                for project_data in result['data']['organization']['projectsV2']['nodes']:
                    project = Project(
                        id=project_data['id'],
                        number=project_data['number'],
                        title=project_data['title'],
                        url=project_data['url'],
                        created_at=project_data['createdAt'],
                        updated_at=project_data['updatedAt']
                    )
                    projects.append(project)
            
            logger.info(f"Successfully returned {len(projects)} organization projects")
            return projects
        else:
            raise HTTPException(status_code=500, detail=f"GraphQL error: {response.text}")
            
    except Exception as e:
        logger.error(f"Error fetching organization projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Project fetch error: {str(e)}")

def get_project_issues_by_sprint_and_status(token: str, org: str, project_number: int, 
                                         sprint_name: str, status_filter: Optional[str] = None) -> List[dict]:
   """
   Get issues from a specific sprint with optional status filtering from GitHub Projects (Organization).
   
   Args:
       token: GitHub personal access token
       org: GitHub organization name
       project_number: Project number
       sprint_name: Name of the sprint view (e.g., "Sprint 34: June 14 – June 17")
       status_filter: Status to filter by (optional - if None, returns all statuses)
   
   Returns:
       List of issue dictionaries with their status information
   """
   url = "https://api.github.com/graphql"
   
   # Extract sprint number for iteration matching
   sprint_number = extract_sprint_number(sprint_name)
   if not sprint_number:
       raise Exception(f"Could not extract sprint number from '{sprint_name}'")
   
   expected_iteration = f"Iteration {sprint_number}"

   # First, get the project and its views
   query_project = """
   query($org: String!, $number: Int!) {
       organization(login: $org) {
           projectV2(number: $number) {
               id
               title
               views(first: 50) {
                   nodes {
                       id
                       name
                   }
               }
           }
       }
   }
   """
   
   headers = {
       "Authorization": f"Bearer {token}",
       "Content-Type": "application/json"
   }
   
   data = {
       "query": query_project,
       "variables": {
           "org": org,
           "number": project_number
       }
   }
   
   try:
       response = requests.post(url, headers=headers, json=data)
       response.raise_for_status()
       result = response.json()
       
   except requests.exceptions.RequestException as e:
       raise Exception(f"Network error when fetching project: {str(e)}")
   except Exception as e:
       raise Exception(f"Error parsing response when fetching project: {str(e)}")
   
   if 'errors' in result:
       raise Exception(f"GraphQL errors: {result['errors']}")
       
   if 'data' not in result or not result['data']['organization'] or not result['data']['organization']['projectV2']:
       raise Exception(f"Project not found or not accessible. Response: {result}")
   
   project_id = result['data']['organization']['projectV2']['id']
   
   # Verify the sprint view exists
   available_views = []
   sprint_view_found = False
   for view in result['data']['organization']['projectV2']['views']['nodes']:
       available_views.append(view['name'])
       if view['name'] == sprint_name:
           sprint_view_found = True
           break
   
   if not sprint_view_found:
       raise Exception(f"Sprint view '{sprint_name}' not found. Available views: {available_views}")

   # Now get items from the project with their field values
   query_items = """
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
   
   data = {
       "query": query_items,
       "variables": {"projectId": project_id}
   }
   
   try:
       response = requests.post(url, headers=headers, json=data)
       response.raise_for_status()
       items_result = response.json()
       
   except requests.exceptions.RequestException as e:
       raise Exception(f"Network error when fetching items: {str(e)}")
   except Exception as e:
       raise Exception(f"Error parsing items response: {str(e)}")
   
   if 'errors' in items_result:
       raise Exception(f"GraphQL errors when fetching items: {items_result['errors']}")
   
   if 'data' not in items_result or not items_result['data']['node']:
       raise Exception(f"Failed to fetch project items. Response: {items_result}")
   
   # Filter items by iteration and optionally by status
   filtered_issues = []
   items = items_result['data']['node']['items']['nodes']

   

   def extract_field_values(field_values):
       """Extract iteration and status information from field values"""
       iteration_title = None
       status = None
       
       for field_value in field_values:
           if 'field' in field_value and field_value['field']:
               field_name = field_value['field'].get('name', '').lower()
               
               # Check iteration
               if 'title' in field_value:
                   iteration_title = normalize_text(field_value.get('title', ''))
               
               # Check status
               if field_name == 'status':
                   status = field_value.get('name') or field_value.get('text')
       
       return iteration_title, status

   for item in items:
       if not item['content']:
           continue

       content = item['content']

       # Skip pull requests if you only want issues
       if 'url' in content and '/pull/' in content['url']:
           continue

       field_values = item['fieldValues']['nodes']
       iteration_title, status = extract_field_values(field_values)
       
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

def update_issue_description(issue_number: int, repo_name: str, new_body: str) -> bool:
   """Update issue description using GitHub REST API"""
   try:
       repo = g.get_repo(repo_name)
       issue = repo.get_issue(issue_number)
       issue.edit(body=new_body)
       logger.info(f"Successfully updated issue #{issue_number} description")
       return True
   except Exception as e:
       logger.error(f"Error updating issue #{issue_number}: {str(e)}")
       return False

@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for terminal sessions with proper Codex integration"""
    session_id = None
    
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Create a new session
        session_id = await terminal_manager.create_session(websocket)
        logger.info(f"Created session: {session_id}")
        
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Terminal connected successfully"
        })
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_json()
                session = terminal_manager.get_session(session_id)
                
                if not session:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session not found"
                    })
                    break
                
                # Handle different message types
                if data['type'] == 'start_codex':
                    # Get the auto mode from the frontend
                    auto_mode = data.get('auto_mode', 'interactive')  # Default to interactive
                    
                    logger.info(f"Starting Codex with mode: {auto_mode}")
                    
                    # Start Codex with proper mode
                    asyncio.create_task(
                        session.start_codex(
                            prompt=data.get('prompt', 'Default prompt'),
                            repo=data.get('repo', 'hail007/Agent-Testing'),
                            title=data.get('title', 'Codex Task'),
                            auto_mode=auto_mode  # Pass the mode
                        )
                    )
                
                elif data['type'] == 'input':
                    # This is crucial for interactive mode!
                    await session.send_input(data.get('data', ''))
                
                elif data['type'] == 'stop':
                    await session.stop()
                    await websocket.send_json({
                        "type": "status",
                        "data": "stopped"
                    })
                
                elif data['type'] == 'get_logs':
                    logs = session.get_logs()
                    await websocket.send_json({
                        "type": "logs",
                        "data": logs
                    })
                    
            except asyncio.CancelledError:
                logger.info("WebSocket task cancelled")
                break
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                # Don't break on message errors, continue listening
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Message handling error: {str(e)}"
                    })
                except:
                    break  # WebSocket is closed
    
    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {str(e)}")
    finally:
        if session_id:
            await terminal_manager.remove_session(session_id)
            logger.info(f"Cleaned up session: {session_id}")

@app.get("/health")
def health():
    return {"status": "ok"}

            
# Routes
@app.get("/")
def root():
   return {"message": "Harmonia Agile Agentic Framework API"}


# Add endpoint to get available sessions
@app.get("/api/terminal/sessions")
def get_terminal_sessions():
    """Get list of active terminal sessions"""
    return {
        "sessions": list(terminal_manager.sessions.keys()),
        "count": len(terminal_manager.sessions)
    }

@app.get("/api/sprint-summary")
def get_sprint_summary(sprint_name: str, project_number: Optional[int] = None):
    """Get summary for a specific iteration"""
    actual_project_number = project_number if project_number is not None else 1
    
    # Implementation remains the same
    return {
        "current_sprint": sprint_name,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        "days_remaining": 7,
        "sprint_goals": f"Goals for {sprint_name}",
        "total_issues": 0,
        "backlog": 0,
        "ready": 0,
        "in_progress": 0,
        "in_review": 0
    }

@app.get("/api/issues/ready", response_model=List[Issue])
def get_issues_ready(sprint_name: str, project_number: Optional[int] = None) -> List[Issue]:
    """
    Get issues from a specific iteration in the hail project.
    
    Args:
        sprint_name: Name of the iteration (e.g., "Iteration 15")
        project_number: Optional project number (defaults to 1 for hail)
    
    Returns:
        List of Issue objects from the specified iteration
    """
    # Default to project 1 (hail) instead of 5
    actual_project_number = project_number if project_number is not None else 1
    
    # ... rest of the implementation remains the same but use actual_project_number
    
    url = "https://api.github.com/graphql"
    
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                items(first: 100) {
                    nodes {
                        id
                        content {
                            ... on Issue {
                                id
                                number
                                title
                                body
                                url
                                createdAt
                                updatedAt
                                state
                                labels(first: 10) {
                                    nodes {
                                        name
                                    }
                                }
                                assignees(first: 5) {
                                    nodes {
                                        login
                                    }
                                }
                                repository {
                                    nameWithOwner
                                }
                            }
                        }
                        fieldValues(first: 20) {
                            nodes {
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
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": "harmoniaailabs",
            "number": actual_project_number
        }
    }
    
    try:
        logger.info(f"Fetching issues for '{sprint_name}' from hail project (#{actual_project_number})")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            raise HTTPException(status_code=500, detail=f"GraphQL errors")
        
        if not result.get('data', {}).get('organization', {}).get('projectV2'):
            raise HTTPException(status_code=404, detail=f"Project not found")
        
        items = result['data']['organization']['projectV2']['items']['nodes']
        issues = []
        
        for item in items:
            if not item['content'] or 'number' not in item['content']:
                continue
            
            content = item['content']
            
            # Check iteration
            iteration_title = None
            status = "todo"
            
            for field_value in item['fieldValues']['nodes']:
                if field_value:
                    if 'title' in field_value and 'field' in field_value:
                        if field_value['field'] and field_value['field'].get('name') in ['Iteration', 'Sprint']:
                            iteration_title = field_value['title']
                    
                    if 'name' in field_value and 'field' in field_value:
                        if field_value['field'] and field_value['field'].get('name') == 'Status':
                            status = field_value['name'].lower()
            
            # Only include issues from the requested iteration
            if iteration_title != sprint_name and not sprint_name in iteration_title:
                continue
            
            labels = [label['name'] for label in content.get('labels', {}).get('nodes', [])]
            assignees = content.get('assignees', {}).get('nodes', [])
            assignee = assignees[0]['login'] if assignees else None
            
            issue = Issue(
                id=content['id'],
                number=content['number'],
                title=content['title'],
                assignee=assignee,
                status=status,
                created_at=content['createdAt'],
                updated_at=content['updatedAt'],
                body=content.get('body', ''),
                labels=labels,
                repo=content.get('repository', {}).get('nameWithOwner', 'Unknown'),
                url=content.get('url', '')
            )
            issues.append(issue)
        
        logger.info(f"Found {len(issues)} issues in '{sprint_name}'")
        return issues
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching issues: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.patch("/api/issues/{issue_number}")
def update_issue(issue_number: int, repo_name: str, update_request: IssueUpdateRequest):
   """
   Update an issue's description.
   
   Args:
       issue_number: GitHub issue number
       repo_name: Repository name (e.g., "owner/repo")
       update_request: Request body containing the new description
   
   Returns:
       Success message or error
   """
   try:
       success = update_issue_description(issue_number, repo_name, update_request.body)
       
       if success:
           return {"message": f"Issue #{issue_number} updated successfully"}
       else:
           raise HTTPException(status_code=500, detail="Failed to update issue")
           
   except Exception as e:
       logger.error(f"Error updating issue #{issue_number}: {str(e)}")
       raise HTTPException(status_code=500, detail=f"Issue update error: {str(e)}")

@app.get("/api/sprints", response_model=List[Sprint])
def get_sprints(project_number: Optional[int] = None) -> List[Sprint]:
    """
    Get all iterations from the hail project using GitHub GraphQL API.
    Enhanced to fetch ALL iterations including current ones.
    
    Args:
        project_number: Optional project number (defaults to 1 for hail project)
    
    Returns:
        List of Sprint objects representing iterations
    """
    # Use provided project number or default to 1 (hail project)
    actual_project_number = project_number if project_number is not None else 1
    
    url = "https://api.github.com/graphql"
    
    # Enhanced query to get ALL iteration data including items with their current iterations
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
                url
                fields(first: 30) {
                    nodes {
                        __typename
                        ... on ProjectV2Field {
                            id
                            name
                        }
                        ... on ProjectV2IterationField {
                            id
                            name
                            configuration {
                                startDay
                                duration
                                iterations {
                                    id
                                    title
                                    startDate
                                    duration
                                }
                                completedIterations {
                                    id
                                    title
                                    startDate
                                    duration
                                }
                            }
                        }
                    }
                }
                items(first: 100) {
                    nodes {
                        id
                        fieldValues(first: 20) {
                            nodes {
                                __typename
                                ... on ProjectV2ItemFieldIterationValue {
                                    title
                                    startDate
                                    duration
                                    iterationId
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": "harmoniaailabs",
            "number": actual_project_number
        }
    }
    
    try:
        logger.info(f"Fetching iterations for hail project (#{actual_project_number})")
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code != 200:
            logger.error(f"GraphQL request failed with status {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"GitHub API error")
        
        result = response.json()
        
        if 'errors' in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            if 'data' not in result:
                raise HTTPException(status_code=500, detail=f"GraphQL errors: {result['errors']}")
        
        if not result.get('data', {}).get('organization', {}).get('projectV2'):
            logger.error(f"No project data found for project #{actual_project_number}")
            raise HTTPException(status_code=404, detail=f"Project #{actual_project_number} not found")
        
        project = result['data']['organization']['projectV2']
        logger.info(f"Found project: {project.get('title', 'Unknown')}")
        
        # Collect all iterations from multiple sources
        all_iterations = {}  # Use dict to avoid duplicates
        
        # Method 1: Get iterations from field configuration
        for field in project.get('fields', {}).get('nodes', []):
            if not field:
                continue
                
            # Check if this is an iteration field
            if field.get('__typename') == 'ProjectV2IterationField' or 'configuration' in field:
                field_name = field.get('name', 'Iteration')
                logger.info(f"Found iteration field: {field_name}")
                
                config = field.get('configuration', {})
                
                # Process active/future iterations
                active_iterations = config.get('iterations', [])
                logger.info(f"Found {len(active_iterations)} active/future iterations")
                
                for iteration in active_iterations:
                    iteration_id = iteration.get('id', iteration.get('title', ''))
                    all_iterations[iteration_id] = {
                        'id': iteration_id,
                        'title': iteration.get('title', 'Unknown'),
                        'startDate': iteration.get('startDate'),
                        'duration': iteration.get('duration', 14),
                        'source': 'active'
                    }
                
                # Process completed iterations
                completed_iterations = config.get('completedIterations', [])
                logger.info(f"Found {len(completed_iterations)} completed iterations")
                
                for iteration in completed_iterations:
                    iteration_id = iteration.get('id', iteration.get('title', ''))
                    all_iterations[iteration_id] = {
                        'id': iteration_id,
                        'title': iteration.get('title', 'Unknown'),
                        'startDate': iteration.get('startDate'),
                        'duration': iteration.get('duration', 14),
                        'source': 'completed'
                    }
        
        # Method 2: Extract iterations from current project items
        # This helps us find iterations that might not be in the configuration but are actively used
        items = project.get('items', {}).get('nodes', [])
        logger.info(f"Checking {len(items)} project items for additional iterations...")
        
        for item in items:
            for field_value in item.get('fieldValues', {}).get('nodes', []):
                if field_value and field_value.get('__typename') == 'ProjectV2ItemFieldIterationValue':
                    title = field_value.get('title')
                    if title and title not in [iter_data['title'] for iter_data in all_iterations.values()]:
                        # Found a new iteration being used by items
                        iteration_id = field_value.get('iterationId', title)
                        all_iterations[iteration_id] = {
                            'id': iteration_id,
                            'title': title,
                            'startDate': field_value.get('startDate'),
                            'duration': field_value.get('duration', 14),
                            'source': 'from_items'
                        }
                        logger.info(f"Found additional iteration from items: {title}")
        
        # Convert to Sprint objects
        sprints = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for iteration_data in all_iterations.values():
            try:
                # Calculate days remaining and format dates
                days_remaining = 0
                date_range = "No dates"
                is_current = False
                
                if iteration_data.get('startDate'):
                    start_date = datetime.strptime(iteration_data['startDate'], "%Y-%m-%d")
                    duration_days = iteration_data.get('duration', 14)
                    end_date = start_date + timedelta(days=duration_days)
                    
                    # Format date range
                    date_range = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
                    
                    # Calculate days remaining
                    if today < start_date:
                        days_remaining = duration_days
                    elif today <= end_date:
                        days_remaining = (end_date - today).days
                        is_current = True
                    else:
                        days_remaining = 0
                
                # Mark current iteration
                title = iteration_data['title']
                if is_current and "(Current)" not in title:
                    title = f"{title} (Current)"
                
                sprint = Sprint(
                    id=iteration_data['id'],
                    name=title,
                    start_date=iteration_data.get('startDate', ''),
                    end_date=(datetime.strptime(iteration_data['startDate'], "%Y-%m-%d") + 
                             timedelta(days=iteration_data.get('duration', 14))).strftime("%Y-%m-%d") 
                             if iteration_data.get('startDate') else ''
                )
                sprints.append(sprint)
                logger.debug(f"Added iteration: {title} (source: {iteration_data['source']})")
                
            except Exception as e:
                logger.error(f"Error processing iteration: {e}")
                # Add with minimal data
                sprint = Sprint(
                    id=iteration_data.get('id', ''),
                    name=iteration_data.get('title', 'Unknown'),
                    start_date='',
                    end_date=''
                )
                sprints.append(sprint)
        
        # Sort sprints by iteration number (highest first for most recent)
        def get_iteration_number(sprint_name):
            match = re.search(r'Iteration\s+(\d+)', sprint_name)
            return int(match.group(1)) if match else 0
        
        sprints.sort(key=lambda x: get_iteration_number(x.name), reverse=True)
        
        logger.info(f"Successfully returned {len(sprints)} iterations")
        logger.info(f"Iterations found: {[s.name for s in sprints[:5]]}")  # Log first 5
        
        return sprints
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching iterations: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    

# Add this debug endpoint to help troubleshoot
@app.get("/api/debug/project-fields")
def debug_project_fields(project_number: Optional[int] = None):
    """
    Debug endpoint to see all fields in the project.
    This helps identify the exact structure of your project.
    """
    actual_project_number = project_number if project_number is not None else 5
    
    url = "https://api.github.com/graphql"
    
    # Query to get ALL information about the project
    query = """
    query($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                id
                title
                number
                url
                fields(first: 50) {
                    nodes {
                        __typename
                        ... on ProjectV2Field {
                            id
                            name
                            dataType
                        }
                        ... on ProjectV2SingleSelectField {
                            id
                            name
                            options {
                                id
                                name
                            }
                        }
                        ... on ProjectV2IterationField {
                            id
                            name
                            configuration {
                                startDay
                                duration
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
                items(first: 5) {
                    nodes {
                        id
                        fieldValues(first: 10) {
                            nodes {
                                __typename
                                ... on ProjectV2ItemFieldIterationValue {
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
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "org": "harmoniaailabs",
            "number": actual_project_number
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # Pretty print for easier reading
        import json
        return json.loads(json.dumps(result, indent=2))
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}")
        return {"error": str(e), "suggestion": "Check your GitHub token has 'read:project' scope"}
@app.post("/api/run-codex")
async def run_codex(prompt_req: PromptRequest):
   """Run the codex with the provided prompt and repository"""
   try:
       subprocess.Popen(["python", "run_codex_todo.py", prompt_req.prompt, prompt_req.repo, prompt_req.title])
       return {"message": "Codex started"}
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Codex error: {str(e)}")

@app.get("/api/pull-requests")
def get_pull_requests():
   """Get open pull requests from the configured repository"""
   try:
       repo = g.get_repo(GITHUB_REPO)
       prs = repo.get_pulls(state="open", sort="created")
       return [{
           "id": pr.number,
           "title": pr.title,
           "author": pr.user.login,
           "branch": pr.head.ref,
           "status": "ci-passed" if pr.mergeable_state == "clean" else "needs-review"
       } for pr in prs]
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"PR fetch error: {str(e)}")

@app.get("/api/repositories", response_model=List[Repository])
def get_repositories():
    """
    Get all repositories from the harmoniaailabs organization.
    
    Returns:
        List of Repository objects from the organization
    """
    try:
        # Get the organization
        org = g.get_organization('harmoniaailabs')
        
        # Get all repositories
        repos = org.get_repos(sort='updated', direction='desc')
        
        results = []
        for repo in repos:
            repository = Repository(
                id=str(repo.id),
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                private=repo.private,
                html_url=repo.html_url,
                default_branch=repo.default_branch,
                updated_at=repo.updated_at.isoformat() if repo.updated_at else ''
            )
            results.append(repository)
        
        logger.info(f"Successfully returned {len(results)} repositories")
        return results
        
    except Exception as e:
        logger.error(f"Error fetching repositories: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Repository fetch error: {str(e)}")

@app.get("/api/repositories/{repo_name}/branches")
def get_repository_branches(repo_name: str):
    """
    Get all branches for a specific repository.
    
    Args:
        repo_name: Repository name in format 'owner/repo'
    
    Returns:
        List of branch names
    """
    try:
        repo = g.get_repo(repo_name)
        branches = repo.get_branches()
        
        branch_list = []
        for branch in branches:
            branch_list.append({
                'name': branch.name,
                'sha': branch.commit.sha,
                'protected': branch.protected
            })
        
        logger.info(f"Successfully returned {len(branch_list)} branches for {repo_name}")
        return {
            'repository': repo_name,
            'default_branch': repo.default_branch,
            'branches': branch_list
        }
        
    except Exception as e:
        logger.error(f"Error fetching branches for {repo_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Branch fetch error: {str(e)}")

# Update the existing run_codex endpoint to accept repository parameter
@app.post("/api/run-codex")
async def run_codex(prompt_req: PromptRequest):
    """Run the codex with the provided prompt and repository"""
    try:
        # Validate that the repository exists and is accessible
        try:
            repo = g.get_repo(prompt_req.repo)
            logger.info(f"Validated repository access: {prompt_req.repo}")
        except Exception as e:
            logger.warning(f"Could not validate repository {prompt_req.repo}: {str(e)}")
            # Continue anyway - let the codex script handle the error
        
        subprocess.Popen([
            "python", 
            "run_codex_improved.py", 
            prompt_req.prompt, 
            prompt_req.repo, 
            prompt_req.title
        ])
        
        return {"message": f"Codex started for repository: {prompt_req.repo}"}
    except Exception as e:
        logger.error(f"Codex error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Codex error: {str(e)}")

# Run app
if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)