from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from github import Github
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import subprocess
import os
import requests
import re

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
token = GITHUB_TOKEN
username =  'hail007' 
project_number = 2

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in environment variables")
if not GITHUB_REPO:
    raise ValueError("GITHUB_REPO not found in environment variables")

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
    id: int
    number: int
    title: str
    assignee: Optional[str]
    status: str
    created_at: str
    updated_at: str
    body: Optional[str]
    labels: List[str]
    repo: str

class Sprint(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str

class PromptRequest(BaseModel):
    prompt: str
    repo: str  # Add this field

# Sprint helpers
def parse_sprint_dates(sprint_name: str) -> tuple[datetime, datetime]:
    try:
        date_part = sprint_name.split(":")[1].strip()
        if "–" in date_part:
            start_str, end_str = date_part.split("–")
        elif "-" in date_part:
            start_str, end_str = date_part.split("-")
        else:
            raise ValueError("Invalid date format")
        start_str = start_str.strip()
        end_str = end_str.strip()
        current_year = datetime.now().year
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        start_parts = start_str.split()
        start_month = month_map[start_parts[0]]
        start_day = int(start_parts[1])
        end_parts = end_str.split()
        if len(end_parts) == 1:
            end_month = start_month
            end_day = int(end_parts[0])
        else:
            end_month = month_map[end_parts[0]]
            end_day = int(end_parts[1])
        return datetime(current_year, start_month, start_day), datetime(current_year, end_month, end_day)
    except Exception as e:
        print(f"Error parsing sprint dates from '{sprint_name}': {e}")
        now = datetime.now()
        return now, now + timedelta(days=7)

def issue_in_sprint_period(issue, start: datetime, end: datetime) -> bool:
    created = issue.created_at.replace(tzinfo=None)
    updated = issue.updated_at.replace(tzinfo=None)
    if start <= created <= end or start <= updated <= end:
        return True
    if issue.milestone and issue.milestone.due_on:
        due = issue.milestone.due_on.replace(tzinfo=None)
        return start <= due <= end
    return False

# Routes
@app.get("/")
def root():
    return {"message": "Harmonia Agile Agentic Framework API"}

import requests
from typing import List, Optional
from fastapi import HTTPException
from dataclasses import dataclass

@dataclass
class Issue:
    id: str
    number: int
    title: str
    assignee: Optional[str]
    status: str
    created_at: str
    updated_at: str
    body: Optional[str]
    labels: List[str]
    repo: str

def get_project_issues_by_sprint_and_status(token: str, username: str, project_number: int, 
                                          sprint_name: str, status_filter: str = "Todo") -> List[dict]:
    """
    Get issues from a specific sprint view with a specific status from GitHub Projects.
    
    Args:
        token: GitHub personal access token
        username: GitHub username  
        project_number: Project number
        sprint_name: Name of the sprint view (e.g., "Sprint 34: June 14 – June 17")
        status_filter: Status to filter by (default: "Todo")
    
    Returns:
        List of issue dictionaries
    """
    url = "https://api.github.com/graphql"
    
    print(f"DEBUG: Looking for sprint '{sprint_name}' in project {project_number} for user {username}")
    
    # First, find the view ID for the sprint
    query_views = """
    query($login: String!, $number: Int!) {
        user(login: $login) {
            projectV2(number: $number) {
                id
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
        "query": query_views,
        "variables": {
            "login": username,
            "number": project_number
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raises exception for bad status codes
        result = response.json()
        
        print(f"DEBUG: GraphQL response: {result}")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error when fetching views: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing response when fetching views: {str(e)}")
    
    if 'errors' in result:
        raise Exception(f"GraphQL errors: {result['errors']}")
        
    if 'data' not in result or not result['data']['user'] or not result['data']['user']['projectV2']:
        raise Exception(f"Project not found or not accessible. Response: {result}")
    
    # Find the sprint view
    sprint_view_id = None
    available_views = []
    for view in result['data']['user']['projectV2']['views']['nodes']:
        available_views.append(view['name'])
        if view['name'] == sprint_name:
            sprint_view_id = view['id']
            break
    
    if not sprint_view_id:
        raise Exception(f"Sprint view '{sprint_name}' not found. Available views: {available_views}")
    
    print(f"DEBUG: Found sprint view ID: {sprint_view_id}")
    
    # Now get items from the specific view with their field values
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
        "variables": {"projectId": result['data']['user']['projectV2']['id']}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        items_result = response.json()
        
        print(f"DEBUG: Items query response status: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error when fetching items: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing items response: {str(e)}")
    
    if 'errors' in items_result:
        raise Exception(f"GraphQL errors when fetching items: {items_result['errors']}")
    
    if 'data' not in items_result or not items_result['data']['node']:
        raise Exception(f"Failed to fetch project items. Response: {items_result}")
    
    # Filter items by status
    filtered_issues = []
    items = items_result['data']['node']['items']['nodes']
    
    for item in items:
        if not item['content']:
            continue
            
        content = item['content']
        
        # Skip pull requests if you only want issues
        if 'url' in content and '/pull/' in content['url']:
            continue
        
        # Find the status field value
        item_status = None
        for field_value in item['fieldValues']['nodes']:
            if field_value and 'field' in field_value:
                field_name = field_value['field']['name'].lower()
                if 'status' in field_name:
                    if 'name' in field_value:  # SingleSelect field
                        item_status = field_value['name']
                    elif 'text' in field_value:  # Text field
                        item_status = field_value['text']
                    break
        
        # Filter by status (project status field)
        if item_status and item_status.lower() == status_filter.lower():
            filtered_issues.append({
                'item': item,
                'content': content,
                'status': item_status,
                'issue_state': content.get('state', 'UNKNOWN')
            })
    
    return filtered_issues

@app.get("/api/issues", response_model=List[Issue])
def get_issues(sprint_name: Optional[str] = None):
    """
    Get issues from GitHub Projects filtered by sprint and status.
    
    Args:
        sprint_name: Name of the sprint view to filter by
    
    Returns:
        List of issues with "Todo" status from the specified sprint
    """
    try:
        # GitHub Projects configuration
        #token = "your_github_token"  # Replace with your token
        username = "hail007"  # Replace with your username
        project_number = 2  # Replace with your project number
        
        if not sprint_name:
            raise HTTPException(status_code=400, detail="sprint_name parameter is required")
        
        # Get issues from the specific sprint with "Todo" status
        filtered_issues = get_project_issues_by_sprint_and_status(
            token=token,
            username=username,
            project_number=project_number,
            sprint_name=sprint_name,
            status_filter="Todo"
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
                status="todo",  # We filtered for "Todo" status
                created_at=content.get('createdAt', ''),
                updated_at=content.get('updatedAt', ''),
                body=content.get('body', ''),
                labels=labels,
                repo=repo_name
            )
            
            results.append(issue)
        
        print(f"Found {len(results)} issues in sprint '{sprint_name}' with 'Todo' status")
        return results
        
    except Exception as e:
        print(f"Full error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Issue fetch error: {str(e)}")


#@app.get("/api/sprints", response_model=List[Sprint])
def get_sprints():
    return [
        Sprint(id="sprint34", name="Sprint 34: June 14 – June 17", start_date="2025-06-14", end_date="2025-06-17"),
        Sprint(id="sprint33", name="Sprint 33: June 10 – June 13", start_date="2025-06-10", end_date="2025-06-13"),
        Sprint(id="sprint32", name="Sprint 32: June 6 – June 9", start_date="2025-06-06", end_date="2025-06-09")
    ]

@app.get("/api/sprints", response_model=List[Sprint])
def get_sprints_() -> List[Sprint]:
    """
    Get all sprint views from a GitHub project and parse them into Sprint objects.
    
    Args:
        token: GitHub personal access token
        username: GitHub username
        project_number: Project number (e.g., 2 for /projects/2)
    
    Returns:
        List of Sprint objects sorted by sprint number (descending)
    """
    url = "https://api.github.com/graphql"
    
    query = """
    query($login: String!, $number: Int!) {
        user(login: $login) {
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
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "query": query,
        "variables": {
            "login": username,
            "number": project_number
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if 'data' not in result or not result['data']['user'] or not result['data']['user']['projectV2']:
        print("Project not found or not accessible")
        return []
    
    views = result['data']['user']['projectV2']['views']['nodes']
    sprints = []
    
    # Regex pattern to match "Sprint 34: June 14 – June 17" format
    sprint_pattern = r"Sprint\s+(\d+):\s+(\w+\s+\d+)\s+[–-]\s+(\w+\s+\d+)"
    
    for view in views:
        view_name = view['name']
        match = re.match(sprint_pattern, view_name, re.IGNORECASE)
        
        if match:
            sprint_number = match.group(1)
            start_date_str = match.group(2)  # "June 14"
            end_date_str = match.group(3)    # "June 17"
            
            # Parse dates - assuming current year (2025)
            current_year = 2025
            
            try:
                # Parse start date
                start_date_obj = datetime.strptime(f"{start_date_str} {current_year}", "%B %d %Y")
                start_date = start_date_obj.strftime("%Y-%m-%d")
                
                # Parse end date
                end_date_obj = datetime.strptime(f"{end_date_str} {current_year}", "%B %d %Y")
                end_date = end_date_obj.strftime("%Y-%m-%d")
                
                # Create Sprint object
                sprint = Sprint(
                    id=f"sprint{sprint_number}",
                    name=view_name,
                    start_date=start_date,
                    end_date=end_date
                )
                
                sprints.append(sprint)
                
            except ValueError as e:
                print(f"Error parsing dates for sprint '{view_name}': {e}")
                continue
    
    # Sort by sprint number (descending - newest first)
    sprints.sort(key=lambda s: int(s.id.replace("sprint", "")), reverse=True)
    
    return sprints

@app.post("/api/run-codex")
async def run_codex(prompt_req: PromptRequest):
    try:
        # Now you can use prompt_req.repo
        subprocess.Popen(["python", "run_codex_todo.py", prompt_req.prompt, prompt_req.repo])
        return {"message": "Codex started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Codex error: {str(e)}")

@app.get("/api/pull-requests")
def get_pull_requests():
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
