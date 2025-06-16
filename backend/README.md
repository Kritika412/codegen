# Harmonia Agile Agentic Framework - Backend

FastAPI와 PyGitHub를 사용한 GitHub Issues 관리 백엔드

## 설정

1. **환경 변수 설정**
   `.env` 파일을 수정하여 GitHub 토큰과 리포지토리 정보를 입력하세요:

   ```
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_REPO=owner/repository_name
   ```

   GitHub Personal Access Token 생성 방법:
   - GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)
   - "Generate new token (classic)" 클릭
   - 필요한 권한: `repo` (전체 repo 접근), `read:org` (조직 정보 읽기)

2. **의존성 설치**
   ```bash
   ./setup.sh
   ```

3. **서버 실행**
   ```bash
   ./run.sh
   ```
   
   또는 직접 실행:
   ```bash
   source venv/bin/activate
   python main.py
   ```

## API 엔드포인트

### GET `/api/issues`
GitHub 리포지토리의 열린 이슈들을 가져옵니다.

**파라미터:**
- `sprint_name` (선택): Sprint 이름 (예: "Sprint 34: June 14 – June 17")

**예시:**
```bash
# 모든 이슈
curl "http://localhost:8000/api/issues"

# 특정 Sprint 기간의 이슈만
curl "http://localhost:8000/api/issues?sprint_name=Sprint%2034:%20June%2014%20–%20June%2017"
```

### GET `/api/sprints`
사용 가능한 Sprint 목록을 반환합니다.

## 기능

### Sprint 기간 필터링
Sprint 이름에서 날짜를 파싱하여 해당 기간에 생성되거나 업데이트된 이슈만 필터링합니다.

지원하는 형식:
- "Sprint 34: June 14 – June 17"
- "Sprint 33: June 10 – June 13"

### 이슈 상태 분류
GitHub 라벨을 기반으로 이슈 상태를 자동으로 분류합니다:
- `todo`: 기본 상태
- `in-progress`: "in progress", "in-progress", "working" 라벨
- `blocked`: "blocked", "on hold" 라벨  
- `completed`: "done", "completed", "resolved" 라벨

### CORS 설정
프론트엔드(Vite: port 5173, Create React App: port 3000)와의 연결을 위한 CORS가 설정되어 있습니다.

## 개발

서버는 개발 모드에서 자동 재시작됩니다. 코드를 수정하면 자동으로 반영됩니다.

API 문서는 서버 실행 후 다음 주소에서 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
