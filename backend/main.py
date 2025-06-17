from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from github import Github
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import subprocess
import os

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

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

class Sprint(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str

class PromptRequest(BaseModel):
    prompt: str

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
        repo = g.get_repo(GITHUB_REPO)
        issues = repo.get_issues(state='open')
        results = []
        if sprint_name:
            start, end = parse_sprint_dates(sprint_name)
            print(f"Filtering by sprint: {start} → {end}")
        for issue in issues:
            if issue.pull_request:
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
                labels=labels
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Issue fetch error: {str(e)}")

@app.get("/api/sprints", response_model=List[Sprint])
def get_sprints():
    return [
        Sprint(id="sprint34", name="Sprint 34: June 14 – June 17", start_date="2025-06-14", end_date="2025-06-17"),
        Sprint(id="sprint33", name="Sprint 33: June 10 – June 13", start_date="2025-06-10", end_date="2025-06-13"),
        Sprint(id="sprint32", name="Sprint 32: June 6 – June 9", start_date="2025-06-06", end_date="2025-06-09")
    ]

@app.post("/api/run-codex")
async def run_codex(prompt_req: PromptRequest):
    try:
        subprocess.Popen(["python", "run_codex_todo.py", prompt_req.prompt])
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
