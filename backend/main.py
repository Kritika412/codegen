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

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
token = GITHUB_TOKEN
org = 'harmoniaailabs'  # Changed from username to organization
project_number = 5  # Updated project number

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
   allow_origins=["http://localhost:5173", "http://localhost:3000"],
   allow_credentials=True,
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

# Routes
@app.get("/")
def root():
   return {"message": "Harmonia Agile Agentic Framework API"}

@app.get("/api/issues", response_model=List[Issue])
def get_issues(sprint_name: Optional[str] = None, status: Optional[str] = None):
   """
   Get issues from GitHub Projects filtered by sprint and optionally by status.
   
   Args:
       sprint_name: Name of the sprint view to filter by
       status: Optional status filter (Ready, In Progress, etc.)
   
   Returns:
       List of issues from the specified sprint iteration
   """
   try:
       if not sprint_name:
           raise HTTPException(status_code=400, detail="sprint_name parameter is required")
       
       # Get issues from the specific sprint with optional status filter
       filtered_issues = get_project_issues_by_sprint_and_status(
           token=token,
           org=org,
           project_number=project_number,
           sprint_name=sprint_name,
           status_filter=status
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
           
           # Create Issue object
           issue = Issue(
               id=content['id'],
               number=content.get('number', 0),  # Draft issues might not have numbers
               title=content['title'],
               assignee=assignee,
               status=issue_data['status'].lower() if issue_data['status'] else 'unknown',
               created_at=content.get('createdAt', ''),
               updated_at=content.get('updatedAt', ''),
               body=content.get('body', ''),
               labels=labels,
               repo=repo_name,
               url=content.get('url', '')  # Include GitHub URL
           )
           
           results.append(issue)
       
       logger.info(f"Successfully returned {len(results)} issues for sprint '{sprint_name}'")
       return results
       
   except Exception as e:
       logger.error(f"Full error details: {str(e)}")
       logger.error(f"Error type: {type(e).__name__}")
       import traceback
       logger.error(f"Traceback: {traceback.format_exc()}")
       raise HTTPException(status_code=500, detail=f"Issue fetch error: {str(e)}")

@app.get("/api/sprint-summary", response_model=SprintSummary)
def get_sprint_summary(sprint_name: str):
   """
   Get comprehensive sprint summary including status counts and dates.
   
   Args:
       sprint_name: Name of the sprint view to analyze
   
   Returns:
       SprintSummary with all sprint information
   """
   try:
       # Get all issues from the sprint (no status filter)
       all_issues = get_project_issues_by_sprint_and_status(
           token=token,
           org=org,
           project_number=project_number,
           sprint_name=sprint_name,
           status_filter=None
       )
       
       # Count issues by status
       status_counts = {
           'backlog': 0,
           'ready': 0,
           'in progress': 0,
           'in review': 0,
           'total': len(all_issues)
       }
       
       for issue in all_issues:
           status = issue['status'].lower() if issue['status'] else 'unknown'
           if status in status_counts:
               status_counts[status] += 1
       
       # Get iteration details for dates
       sprint_number = extract_sprint_number(sprint_name)
       iteration_title = f"Iteration {sprint_number}" if sprint_number else ""
       iteration_details = get_iteration_details(token, org, project_number, iteration_title)
       
       start_date = iteration_details.get('start_date', '')
       duration = iteration_details.get('duration', 0)
       
       # Calculate end date
       end_date = ''
       if start_date and duration:
           try:
               start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
               end_dt = start_dt + timedelta(days=duration)
               end_date = end_dt.isoformat()
           except Exception as e:
               logger.error(f"Error calculating end date: {str(e)}")
       
       days_remaining = calculate_days_remaining(end_date)
       
       return SprintSummary(
           current_sprint=sprint_name,
           start_date=start_date,
           end_date=end_date,
           days_remaining=days_remaining,
           sprint_goals="Sprint goals from API",  # Can be enhanced to get actual goals
           total_issues=status_counts['total'],
           backlog=status_counts['backlog'],
           ready=status_counts['ready'],
           in_progress=status_counts['in progress'],
           in_review=status_counts['in review']
       )
       
   except Exception as e:
       logger.error(f"Error in get_sprint_summary: {str(e)}")
       import traceback
       logger.error(f"Traceback: {traceback.format_exc()}")
       raise HTTPException(status_code=500, detail=f"Sprint summary error: {str(e)}")

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
def get_sprints() -> List[Sprint]:
   """
   Get all sprint views from a GitHub organization project and parse them into Sprint objects.
   Only returns views that start with "Sprint".
   
   Returns:
       List of Sprint objects sorted by sprint number (descending)
   """
   url = "https://api.github.com/graphql"
   
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
           raise HTTPException(status_code=500, detail=f"GraphQL errors: {result['errors']}")
           
       if 'data' not in result or not result['data']['organization'] or not result['data']['organization']['projectV2']:
           raise HTTPException(status_code=404, detail="Project not found or not accessible")
       
       project = result['data']['organization']['projectV2']
       views = project['views']['nodes']
       sprints = []
       
       # Create a mapping of iteration titles to their details
       iteration_details = {}
       for field in project['fields']['nodes']:
           if 'configuration' in field and 'iterations' in field['configuration']:
               for iteration in field['configuration']['iterations']:
                   iteration_details[iteration['title']] = iteration
       
       # Simple pattern to match "Sprint 1", "Sprint 2", etc.
       sprint_pattern = r"Sprint\s+(\d+)$"
       
       for view in views:
           view_name = view['name']
           
           # Only process views that start with "Sprint"
           if not view_name.startswith("Sprint"):
               continue
               
           match = re.match(sprint_pattern, view_name, re.IGNORECASE)
           
           if match:
               sprint_number = match.group(1)
               iteration_title = f"Iteration {sprint_number}"
               
               # Get iteration details if available
               iteration_info = iteration_details.get(iteration_title, {})
               start_date = iteration_info.get('startDate', '')
               duration = iteration_info.get('duration', 0)
               
               # Calculate end date
               end_date = ''
               if start_date and duration:
                   try:
                       start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                       end_dt = start_dt + timedelta(days=duration)
                       end_date = end_dt.isoformat()
                   except Exception as e:
                       logger.error(f"Error calculating end date for sprint {sprint_number}: {str(e)}")
               
               # Create Sprint object
               sprint = Sprint(
                   id=f"sprint{sprint_number}",
                   name=view_name,
                   start_date=start_date,
                   end_date=end_date,
                   iteration_id=iteration_info.get('id', ''),
                   duration=duration
               )
               
               sprints.append(sprint)
       
       # Sort by sprint number (descending - newest first)
       sprints.sort(key=lambda s: int(s.id.replace("sprint", "")), reverse=True)
       
       return sprints
       
   except requests.exceptions.RequestException as e:
       raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
   except Exception as e:
       logger.error(f"Error in get_sprints: {str(e)}")
       import traceback
       logger.error(f"Traceback: {traceback.format_exc()}")
       raise HTTPException(status_code=500, detail=f"Sprint fetch error: {str(e)}")

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

# Run app
if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)