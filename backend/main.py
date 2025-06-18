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

@app.get("/api/issues", response_model=List[Issue])
def get_issues(sprint_name: Optional[str] = None):
    try:
        user = g.get_user()
        results = []
        if sprint_name:
            start, end = parse_sprint_dates(sprint_name)
            print(f"Filtering by sprint: {start} → {end}")
        for repo in user.get_repos():
            issues = repo.get_issues(state='open')
            for issue in issues:
                if hasattr(issue, "pull_request") and issue.pull_request:
                    continue
                if sprint_name and not issue_in_sprint_period(issue, start, end):
                    continue
                labels = [l.name for l in issue.labels]
                status = "todo"
                lnames = [l.lower() for l in labels]
                if any(l in lnames for l in ["in progress", "in-progress", "working"]):
                    status = "in-progress"
                elif any(l in lnames for l in ["blocked", "on hold"]):
                    status = "blocked"
                elif any(l in lnames for l in ["done", "completed", "resolved"]):
                    status = "completed"
                results.append(Issue(
                    id=issue.id,
                    number=issue.number,
                    title=issue.title,
                    assignee=issue.assignee.login if issue.assignee else None,
                    status=status,
                    created_at=issue.created_at.isoformat(),
                    updated_at=issue.updated_at.isoformat(),
                    body=issue.body,
                    labels=labels,
                    repo=issue.repository.full_name  # Add repo name here
                ))
        return results
    except Exception as e:
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
