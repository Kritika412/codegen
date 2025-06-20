# Harmonia Agile Agentic Framework - Backend

GitHub Issues management backend using FastAPI and PyGitHub

## Setup

1. **Environment Variables Configuration**
   Modify the `.env` file to enter your GitHub token and repository information:

   ```
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_REPO=owner/repository_name
   ```

   How to create GitHub Personal Access Token:
   - GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)
   - Click "Generate new token (classic)"
   - Required permissions: `repo` (full repo access), `read:org` (read organization info)

2. **Install Dependencies**
   ```bash
   ./setup.sh
   ```

3. **Run Server**
   ```bash
   ./run.sh
   ```
   
   Or run directly:
   ```bash
   source venv/bin/activate
   python main.py
   ```

## API Endpoints

### GET `/api/issues`
Fetches open issues from the GitHub repository.

**Parameters:**
- `sprint_name` (optional): Sprint name (e.g., "Sprint 34: June 14 – June 17")

**Examples:**
```bash
# All issues
curl "http://localhost:8000/api/issues"

# Issues from specific Sprint period only
curl "http://localhost:8000/api/issues?sprint_name=Sprint%2034:%20June%2014%20–%20June%2017"
```

### GET `/api/sprints`
Returns the list of available Sprints.

## Features

### Sprint Period Filtering
Parses dates from Sprint names to filter only issues created or updated during that period.

Supported formats:
- "Sprint 34: June 14 – June 17"
- "Sprint 33: June 10 – June 13"

### Issue Status Classification
Automatically classifies issue status based on GitHub labels:
- `todo`: default status
- `in-progress`: "in progress", "in-progress", "working" labels
- `blocked`: "blocked", "on hold" labels  
- `completed`: "done", "completed", "resolved" labels

### CORS Configuration
CORS is configured for connection with frontend (Vite: port 5173, Create React App: port 3000).

## Development

The server auto-restarts in development mode. Code changes are automatically reflected.

API documentation is available at the following addresses after running the server:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
