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
import unicodedata

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

class Sprint(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str

class PromptRequest(BaseModel):
    prompt: str
    repo: str

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

def get_project_issues_by_sprint_and_status(token: str, org: str, project_number: int, 
                                          sprint_name: str, status_filter: str = "Ready") -> List[dict]:
    """
    Get issues from a specific sprint with a specific status from GitHub Projects (Organization).
    
    Args:
        token: GitHub personal access token
        org: GitHub organization name
        project_number: Project number
        sprint_name: Name of the sprint view (e.g., "Sprint 34: June 14 – June 17")
        status_filter: Status to filter by (default: "Ready")
    
    Returns:
        List of issue dictionaries
    """
    url = "https://api.github.com/graphql"
    
    print(f"DEBUG: Looking for sprint '{sprint_name}' in project {project_number} for org {org}")
    
    # Extract sprint number for iteration matching
    sprint_number = extract_sprint_number(sprint_name)
    if not sprint_number:
        raise Exception(f"Could not extract sprint number from '{sprint_name}'")
    
    expected_iteration = f"Iteration {sprint_number}"
    print(f"DEBUG: Looking for iteration '{expected_iteration}'")
    
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
        
        print(f"DEBUG: GraphQL response: {result}")
        
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
    
    print(f"DEBUG: Found sprint view: {sprint_name}")
    
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
        
        print(f"DEBUG: Items query response status: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error when fetching items: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing items response: {str(e)}")
    
    if 'errors' in items_result:
        raise Exception(f"GraphQL errors when fetching items: {items_result['errors']}")
    
    if 'data' not in items_result or not items_result['data']['node']:
        raise Exception(f"Failed to fetch project items. Response: {items_result}")
    
    # Filter items by iteration and status
    filtered_issues = []
    items = items_result['data']['node']['items']['nodes']

    def has_matching_iteration_and_status(field_values, expected_iteration, status_filter):
        iteration_match = False
        status_match = False
        
        print(f"DEBUG: Checking {len(field_values)} field values")
        
        for field_value in field_values:
            # Debug: Print all field values to understand structure
            if 'field' in field_value:
                field_name = field_value['field'].get('name', 'Unknown')
                print(f"DEBUG: Field '{field_name}': {field_value}")
            
            # Check iteration - look for "Iteration {num}" format
            if 'title' in field_value:
                iteration_title = normalize_text(field_value.get('title', ''))
                expected_iter_normalized = normalize_text(expected_iteration)
                print(f"DEBUG: Comparing iteration '{iteration_title}' with expected '{expected_iter_normalized}'")
                if iteration_title == expected_iter_normalized:
                    iteration_match = True
                    print(f"DEBUG: Found matching iteration: {iteration_title}")
            
            # Check status - look for "Ready" status
            if 'field' in field_value and field_value['field'].get('name'):
                field_name = field_value['field']['name'].lower()
                if field_name == 'status':
                    status_val = field_value.get('name') or field_value.get('text')
                    print(f"DEBUG: Found status field with value: '{status_val}'")
                    if status_val and status_val.lower() == status_filter.lower():
                        status_match = True
                        print(f"DEBUG: Found matching status: {status_val}")
        
        print(f"DEBUG: Iteration match: {iteration_match}, Status match: {status_match}")
        return iteration_match and status_match

    for item in items:
        if not item['content']:
            continue

        content = item['content']

        # Skip pull requests if you only want issues
        if 'url' in content and '/pull/' in content['url']:
            continue

        field_values = item['fieldValues']['nodes']
        if has_matching_iteration_and_status(field_values, expected_iteration, status_filter):
            filtered_issues.append({
                'item': item,
                'content': content,
                'status': status_filter,
                'issue_state': content.get('state', 'UNKNOWN')
            })
    
    print(f"DEBUG: Found {len(filtered_issues)} issues matching criteria")
    return filtered_issues

# Routes
@app.get("/")
def root():
    return {"message": "Harmonia Agile Agentic Framework API"}

@app.get("/api/issues", response_model=List[Issue])
def get_issues(sprint_name: Optional[str] = None):
    """
    Get issues from GitHub Projects filtered by sprint and status.
    
    Args:
        sprint_name: Name of the sprint view to filter by
    
    Returns:
        List of issues with "Ready" status from the specified sprint iteration
    """
    try:
        if not sprint_name:
            raise HTTPException(status_code=400, detail="sprint_name parameter is required")
        
        # Get issues from the specific sprint with "Ready" status
        filtered_issues = get_project_issues_by_sprint_and_status(
            token=token,
            org=org,
            project_number=project_number,
            sprint_name=sprint_name,
            status_filter="Ready"
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
                status="ready",  # We filtered for "Ready" status
                created_at=content.get('createdAt', ''),
                updated_at=content.get('updatedAt', ''),
                body=content.get('body', ''),
                labels=labels,
                repo=repo_name
            )
            
            results.append(issue)
        
        print(f"Found {len(results)} issues in sprint '{sprint_name}' with 'Ready' status")
        return results
        
    except Exception as e:
        print(f"Full error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Issue fetch error: {str(e)}")

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
        
        views = result['data']['organization']['projectV2']['views']['nodes']
        sprints = []
        
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
                
                # Create Sprint object with minimal date info (can be updated later if needed)
                sprint = Sprint(
                    id=f"sprint{sprint_number}",
                    name=view_name,
                    start_date="",  # No date parsing needed for simple format
                    end_date=""     # No date parsing needed for simple format
                )
                
                sprints.append(sprint)
        
        # Sort by sprint number (descending - newest first)
        sprints.sort(key=lambda s: int(s.id.replace("sprint", "")), reverse=True)
        
        return sprints
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        print(f"Error in get_sprints: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Sprint fetch error: {str(e)}")

@app.post("/api/run-codex")
async def run_codex(prompt_req: PromptRequest):
    """Run the codex with the provided prompt and repository"""
    try:
        subprocess.Popen(["python", "run_codex_todo.py", prompt_req.prompt, prompt_req.repo])
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