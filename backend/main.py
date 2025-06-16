from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from github import Github
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI(title="Harmonia Agile Agentic Framework API")

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GitHub setup
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in environment variables")
if not GITHUB_REPO:
    raise ValueError("GITHUB_REPO not found in environment variables")

g = Github(GITHUB_TOKEN)

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
    
def parse_sprint_dates(sprint_name: str) -> tuple[datetime, datetime]:
    """
    Sprint name에서 날짜를 파싱합니다.
    예: "Sprint 34: June 14 – June 17" -> (2025-06-14, 2025-06-17)
    """
    try:
        # ":" 뒤의 날짜 부분만 추출
        date_part = sprint_name.split(":")[1].strip()
        
        # "–" 또는 "-"로 날짜 분할
        if "–" in date_part:
            start_str, end_str = date_part.split("–")
        elif "-" in date_part:
            start_str, end_str = date_part.split("-")
        else:
            raise ValueError("Invalid date format")
            
        start_str = start_str.strip()
        end_str = end_str.strip()
        
        # 현재 년도 사용 (나중에 더 정교하게 만들 수 있음)
        current_year = datetime.now().year
        
        # 월 이름을 숫자로 변환
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        
        # Start date 파싱
        start_parts = start_str.split()
        start_month_name = start_parts[0]
        start_day = int(start_parts[1])
        start_month = month_map[start_month_name]
        start_date = datetime(current_year, start_month, start_day)
        
        # End date 파싱 (월이 생략된 경우 start month 사용)
        end_parts = end_str.split()
        if len(end_parts) == 1:  # 일만 있는 경우
            end_day = int(end_parts[0])
            end_month = start_month
        else:  # 월과 일이 모두 있는 경우
            end_month_name = end_parts[0]
            end_day = int(end_parts[1])
            end_month = month_map[end_month_name]
            
        end_date = datetime(current_year, end_month, end_day)
        
        return start_date, end_date
        
    except Exception as e:
        print(f"Error parsing sprint dates from '{sprint_name}': {e}")
        # 파싱 실패시 현재 날짜 기준으로 임시 설정
        now = datetime.now()
        return now, now + timedelta(days=7)

def issue_in_sprint_period(issue, start_date: datetime, end_date: datetime) -> bool:
    """
    Issue가 sprint 기간에 해당하는지 확인합니다.
    이슈의 생성일, 업데이트일, 또는 milestone이 sprint 기간에 포함되는지 체크합니다.
    """
    issue_created = issue.created_at.replace(tzinfo=None)
    issue_updated = issue.updated_at.replace(tzinfo=None)
    
    # Issue가 sprint 기간에 생성되었거나 업데이트된 경우
    if (start_date <= issue_created <= end_date) or \
       (start_date <= issue_updated <= end_date):
        return True
    
    # Milestone이 있는 경우 milestone의 due_date 확인
    if issue.milestone and issue.milestone.due_on:
        milestone_due = issue.milestone.due_on.replace(tzinfo=None)
        if start_date <= milestone_due <= end_date:
            return True
    
    return False

@app.get("/")
async def root():
    return {"message": "Harmonia Agile Agentic Framework API"}

@app.get("/api/issues", response_model=List[Issue])
async def get_issues(sprint_name: Optional[str] = None):
    """
    GitHub 이슈들을 가져옵니다. sprint_name이 제공되면 해당 기간의 이슈만 필터링합니다.
    """
    try:
        repo = g.get_repo(GITHUB_REPO)
        issues = repo.get_issues(state='open')
        
        result_issues = []
        
        # Sprint 기간 설정
        if sprint_name:
            start_date, end_date = parse_sprint_dates(sprint_name)
            print(f"Filtering issues for sprint period: {start_date} to {end_date}")
        
        for issue in issues:
            # Pull Request는 제외 (GitHub API에서 PR도 issue로 반환됨)
            if issue.pull_request:
                continue
                
            # Sprint 필터링
            if sprint_name and not issue_in_sprint_period(issue, start_date, end_date):
                continue
            
            # Assignee 정보 처리
            assignee_name = issue.assignee.login if issue.assignee else None
            
            # 상태 결정 (라벨 기반)
            status = "todo"
            label_names = [label.name.lower() for label in issue.labels]
            
            if any(label in label_names for label in ["in progress", "in-progress", "working"]):
                status = "in-progress"
            elif any(label in label_names for label in ["blocked", "on hold"]):
                status = "blocked"
            elif any(label in label_names for label in ["done", "completed", "resolved"]):
                status = "completed"
            
            issue_data = Issue(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                assignee=assignee_name,
                status=status,
                created_at=issue.created_at.isoformat(),
                updated_at=issue.updated_at.isoformat(),
                body=issue.body,
                labels=[label.name for label in issue.labels]
            )
            
            result_issues.append(issue_data)
        
        return result_issues
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching issues: {str(e)}")

@app.get("/api/sprints", response_model=List[Sprint])
async def get_sprints():
    """
    사용 가능한 sprint 목록을 반환합니다.
    """
    # 임시로 하드코딩된 sprint 목록 (나중에 GitHub milestone에서 가져올 수 있음)
    sprints = [
        Sprint(
            id="sprint34",
            name="Sprint 34: June 14 – June 17",
            start_date="2025-06-14",
            end_date="2025-06-17"
        ),
        Sprint(
            id="sprint33",
            name="Sprint 33: June 10 – June 13",
            start_date="2025-06-10",
            end_date="2025-06-13"
        ),
        Sprint(
            id="sprint32",
            name="Sprint 32: June 6 – June 9",
            start_date="2025-06-06",
            end_date="2025-06-09"
        )
    ]
    return sprints

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
