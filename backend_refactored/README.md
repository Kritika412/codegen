# Harmonia Agile Agentic Framework - Backend (Refactored)

A clean, modular backend system for managing GitHub issues, sprints, and project workflows using FastAPI.

## 🏗️ Architecture Overview

This refactored version provides a well-structured, maintainable codebase that's optimized for agentic AI systems:

```
backend_refactored/
├── app/
│   ├── api/                    # API routes and endpoints
│   │   └── routes/            
│   │       ├── issues.py      # Issue management endpoints
│   │       ├── sprints.py     # Sprint management endpoints
│   │       ├── codex.py       # Codex AI integration endpoints
│   │       └── health.py      # Health check endpoints
│   ├── core/                  # Core functionality
│   │   ├── config.py          # Configuration management
│   │   └── exceptions.py      # Custom exception classes
│   ├── models/                # Data models and schemas
│   │   └── schemas.py         # Pydantic models
│   ├── services/              # Business logic layer
│   │   ├── github_service.py  # GitHub API integration
│   │   ├── sprint_service.py  # Sprint management logic
│   │   └── codex_service.py   # Codex AI workflow management
│   └── utils/                 # Utility functions
│       └── helpers.py         # Common helper functions
├── scripts/                   # Standalone scripts
│   └── run_codex_enhanced.py  # Enhanced Codex CLI script
├── main.py                    # FastAPI application entry point
└── requirements.txt           # Python dependencies
```

## 🚀 Key Improvements

### 1. **Modular Architecture**
- **Separation of Concerns**: Clear separation between API routes, business logic, and data models
- **Service Layer**: Dedicated service classes for GitHub API, Sprint management, and Codex operations
- **Dependency Injection**: Clean dependency management between services

### 2. **Enhanced Error Handling**
- **Custom Exceptions**: Domain-specific exception classes for clear error handling
- **Centralized Error Handling**: Global exception handlers in the FastAPI app
- **Detailed Error Messages**: Informative error responses for debugging

### 3. **Improved Configuration**
- **Environment-based Configuration**: Centralized config management with validation
- **Type Safety**: Strong typing throughout the application
- **Configuration Validation**: Startup validation of required configuration

### 4. **Better Logging**
- **Structured Logging**: Consistent logging format across all modules
- **Rotating File Logs**: Automatic log rotation to prevent disk space issues
- **Log Levels**: Configurable log levels for different environments

### 5. **API Documentation**
- **Comprehensive Documentation**: Detailed API documentation with examples
- **Type Safety**: Full Pydantic model validation for requests/responses
- **Health Checks**: Multiple health check endpoints for monitoring

## 📋 Prerequisites

- Python 3.11+
- Git
- GitHub Personal Access Token
- OpenAI API Key (for Codex features)
- Codex CLI (optional, for AI code generation)

## 🔧 Setup

1. **Clone and Navigate**
   ```bash
   cd backend_refactored
   ```

2. **Install Dependencies**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure Environment**
   Update the `.env` file with your credentials:
   ```env
   GITHUB_TOKEN=your_github_personal_access_token
   GITHUB_REPO=owner/repository_name
   GITHUB_ORG=your_github_organization
   GITHUB_PROJECT_NUMBER=5
   OPENAI_API_KEY=your_openai_api_key
   ```

4. **Run the Application**
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

## 📚 API Endpoints

### Issues Management
- `GET /api/issues` - Get issues filtered by sprint and status
- `PATCH /api/issues/{issue_number}` - Update issue description
- `GET /api/issues/{issue_number}` - Get specific issue details

### Sprint Management  
- `GET /api/sprints` - Get all sprint views
- `GET /api/sprints/summary` - Get comprehensive sprint summary
- `GET /api/sprints/{sprint_name}/issues` - Get issues from specific sprint
- `GET /api/sprints/{sprint_name}/metrics` - Get detailed sprint metrics

### Codex AI Integration
- `POST /api/codex/run` - Run Codex workflow (commit only)
- `POST /api/codex/run-and-push` - Run Codex workflow with auto-PR
- `POST /api/codex/run-async` - Run Codex workflow asynchronously
- `GET /api/codex/status` - Check Codex service status

### Health & Monitoring
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Comprehensive health status
- `GET /api/health/ready` - Readiness check for deployments
- `GET /api/health/live` - Liveness check for deployments

## 🔍 Usage Examples

### Get Sprint Summary
```bash
curl "http://localhost:8000/api/sprints/summary?sprint_name=Sprint%2034"
```

### Get Issues from Sprint
```bash
curl "http://localhost:8000/api/issues?sprint_name=Sprint%2034&status=in%20progress"
```

### Run Codex AI Code Generation
```bash
curl -X POST "http://localhost:8000/api/codex/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Add error handling to the API", "repo": "owner/repo"}'
```

### Check System Health
```bash
curl "http://localhost:8000/api/health/detailed"
```

## 🐳 Docker Support

```bash
# Build the image
docker build -t harmonia-api .

# Run the container
docker run -p 8000:8000 --env-file .env harmonia-api
```

## 🧪 Testing

Run the enhanced Codex script:
```bash
python scripts/run_codex_enhanced.py "Add logging to all API endpoints" "owner/repo"
```

## 📊 Monitoring

The application includes comprehensive monitoring capabilities:

- **Health Checks**: Multiple endpoints for different health check scenarios
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Metrics**: Basic performance and usage metrics
- **Error Tracking**: Detailed error logging with stack traces

## 🔧 Configuration Options

All configuration is managed through environment variables:

```env
# GitHub Configuration
GITHUB_TOKEN=              # GitHub Personal Access Token
GITHUB_REPO=               # Default repository  
GITHUB_ORG=                # GitHub organization
GITHUB_PROJECT_NUMBER=     # Project board number

# OpenAI Configuration
OPENAI_API_KEY=            # OpenAI API key for Codex

# API Configuration  
API_HOST=0.0.0.0           # Server bind address
API_PORT=8000              # Server port
DEBUG=True                 # Debug mode

# Logging Configuration
LOG_LEVEL=INFO             # Logging level
LOG_FILE=logs/api.log      # Log file path
LOG_MAX_BYTES=10485760     # Max log file size
LOG_BACKUP_COUNT=5         # Number of backup log files
```

## 🤖 Agentic AI Optimizations

This refactored version is specifically optimized for agentic AI systems:

### **Clear Module Boundaries**
- Each module has a single responsibility
- Clean interfaces between components
- Minimal coupling between services

### **Comprehensive Documentation**
- Detailed docstrings for all functions and classes
- Type hints throughout the codebase
- Clear error messages and handling

### **Consistent Patterns**
- Standardized error handling patterns
- Consistent naming conventions
- Predictable code structure

### **Easy Extension**
- Plugin-style architecture for new services
- Clear extension points for new functionality
- Modular design for easy modification

## 🚀 Production Deployment

For production deployment:

1. Set `DEBUG=False` in environment variables
2. Use a production WSGI server like Gunicorn
3. Set up proper log aggregation
4. Configure health check monitoring
5. Use Docker for containerized deployment

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 🆘 Troubleshooting

### Common Issues

1. **GitHub Token Issues**
   - Ensure token has `repo` and `read:org` permissions
   - Check token is not expired

2. **Project Not Found**
   - Verify `GITHUB_ORG` and `GITHUB_PROJECT_NUMBER` are correct
   - Ensure you have access to the organization project

3. **Codex CLI Issues**
   - Install Codex CLI: `npm install -g @github/copilot-cli`
   - Ensure `OPENAI_API_KEY` is configured

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your `.env` file.

## 🤝 Contributing

This refactored architecture makes contributions easier:

1. **Add New Services**: Create new service classes in `app/services/`
2. **Add New Routes**: Create new route modules in `app/api/routes/`
3. **Add New Models**: Define new Pydantic models in `app/models/schemas.py`
4. **Add Utilities**: Create helper functions in `app/utils/helpers.py`

Each component is well-isolated and testable, making the codebase much more maintainable for both human developers and AI agents.
