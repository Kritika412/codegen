#!/usr/bin/env python3
"""
Improved Codex runner with enhanced error handling and debugging
"""
import subprocess
import tempfile
import os
import shutil
import sys
from github import Github
from dotenv import load_dotenv
from datetime import datetime
import json
import requests
import traceback

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Configuration from arguments with better debugging
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Create a simple HTML page"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex Task"
AUTO_MODE = sys.argv[4] if len(sys.argv) > 4 else "auto"

def log(message):
    """Print with flush for real-time output"""
    print(message, flush=True)

# Log the configuration immediately
log("=" * 60)
log("🚀 CODEX CONFIGURATION")
log("=" * 60)
log(f"📝 Prompt: {PROMPT}")
log(f"📦 Repository: {REPO_NAME}")
log(f"🏷️ Title: {TITLE}")
log(f"🤖 Mode: {AUTO_MODE}")
log(f"🔑 GitHub Token: {'✅ Set' if GITHUB_TOKEN else '❌ Missing'}")
log(f"🔑 OpenAI Key: {'✅ Set' if OPENAI_API_KEY else '❌ Missing'}")
log("=" * 60)

def verify_repository_access():
    """Verify that we can access the repository"""
    try:
        log(f"🔍 Verifying access to repository: {REPO_NAME}")
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Try to get basic repo info to verify access
        log(f"✅ Repository found: {repo.full_name}")
        log(f"   - Default branch: {repo.default_branch}")
        log(f"   - Private: {repo.private}")
        log(f"   - Permissions: Can push = {repo.permissions.push if hasattr(repo.permissions, 'push') else 'Unknown'}")
        
        # Check if we can list branches
        branches = list(repo.get_branches())
        log(f"   - Branches accessible: {len(branches)} branches found")
        
        return True, repo.default_branch
        
    except Exception as e:
        log(f"❌ Repository access verification failed!")
        log(f"   Error: {str(e)}")
        log(f"   Type: {type(e).__name__}")
        
        # Provide helpful error messages
        if "404" in str(e):
            log("   💡 Repository not found or no access. Check:")
            log("      - Repository name is correct (owner/repo format)")
            log("      - GitHub token has access to this repository")
            log("      - Repository exists and is not deleted")
        elif "401" in str(e):
            log("   💡 Authentication failed. Check:")
            log("      - GitHub token is valid and not expired")
            log("      - Token is correctly set in .env file")
        elif "403" in str(e):
            log("   💡 Permission denied. Check:")
            log("      - GitHub token has 'repo' scope")
            log("      - You have write access to the repository")
        
        return False, "main"

def generate_code_with_openai(prompt):
    """Use OpenAI API directly to generate code"""
    try:
        if not OPENAI_API_KEY:
            log("⚠️ OpenAI API key not found, using fallback generation")
            return None
            
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are a helpful coding assistant. Generate complete, working code based on the user's request. 
        Always include proper file extensions in your response. 
        For HTML requests, create a complete, valid HTML5 document.
        Respond with just the code, no explanations."""
        
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        log("🤖 Calling OpenAI API...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated = result['choices'][0]['message']['content']
            log(f"✅ Generated {len(generated)} characters of code")
            return generated
        else:
            log(f"⚠️ OpenAI API error: {response.status_code}")
            log(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        log(f"⚠️ Error calling OpenAI: {str(e)}")
        return None

def create_file_from_prompt(temp_dir, prompt):
    """Create a file based on the prompt"""
    log("🎨 Starting code generation...")
    
    # First try to use OpenAI API
    generated_code = generate_code_with_openai(prompt)
    
    if generated_code:
        # Determine file type and name based on content and prompt
        if "html" in prompt.lower() or "<html" in generated_code.lower():
            filename = "index.html"
        elif "python" in prompt.lower() or "def " in generated_code:
            filename = "script.py"
        elif "javascript" in prompt.lower() or "function" in generated_code:
            filename = "script.js"
        elif "css" in prompt.lower() or "{" in generated_code:
            filename = "style.css"
        else:
            filename = "generated_code.txt"
        
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        
        log(f"✅ Created file: {filename}")
        log(f"   Size: {len(generated_code)} bytes")
        return True
    
    # Fallback: Create a simple file based on the prompt
    log("📝 Using fallback file generation...")
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{TITLE}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .status {{
            color: #22c55e;
            font-weight: bold;
            margin: 20px 0;
        }}
        .prompt {{
            background: #f3f4f6;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .timestamp {{
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        .repo-info {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 10px 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 {TITLE}</h1>
        <div class="status">✅ Successfully Generated</div>
        
        <div class="repo-info">
            <strong>Repository:</strong> {REPO_NAME}
        </div>
        
        <div class="prompt">
            <strong>Original Prompt:</strong><br>
            {prompt}
        </div>
        
        <div class="timestamp">
            Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
    
    filepath = os.path.join(temp_dir, "index.html")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    log(f"✅ Created fallback file: index.html")
    return True

def clone_repository(temp_dir, default_branch="main"):
    """Clone the repository with better error handling"""
    log(f"📥 Attempting to clone repository: {REPO_NAME}")
    log(f"   Target directory: {temp_dir}")
    log(f"   Default branch: {default_branch}")
    
    # Try to clone with the default branch
    token_clone_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
    
    # First attempt with the default branch
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", default_branch, token_clone_url, temp_dir],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        log(f"⚠️ Clone with branch '{default_branch}' failed")
        log(f"   Error: {result.stderr}")
        
        # Try without specifying branch
        log("🔄 Retrying without branch specification...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", token_clone_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            log(f"❌ Clone failed completely")
            log(f"   Error: {result.stderr}")
            
            # Provide helpful error messages
            if "Repository not found" in result.stderr:
                log("   💡 Repository not found. Check the repository name.")
            elif "Authentication failed" in result.stderr:
                log("   💡 Authentication failed. Check your GitHub token.")
            elif "Could not resolve host" in result.stderr:
                log("   💡 Network issue. Check your internet connection.")
                
            return False
    
    log("✅ Repository cloned successfully")
    
    # List files in the cloned repo
    files = os.listdir(temp_dir)
    log(f"   Files in repository: {len(files)} files")
    if len(files) <= 10:
        for f in files[:10]:
            log(f"   - {f}")
    
    return True

def run():
    temp_dir = None
    try:
        # Step 1: Verify repository access first
        can_access, default_branch = verify_repository_access()
        if not can_access:
            log("⚠️ Continuing despite repository access issues...")
            log("   Will create files locally without pushing")
        
        # Step 2: Create temp directory
        temp_dir = tempfile.mkdtemp()
        log(f"📁 Created temp directory: {temp_dir}")
        
        # Step 3: Clone repository (if we have access)
        clone_success = False
        if can_access:
            clone_success = clone_repository(temp_dir, default_branch)
        
        if not clone_success:
            log("📝 Working in local directory without repository")
            # Initialize git repo locally
            subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
            subprocess.run(["git", "checkout", "-b", "main"], cwd=temp_dir, capture_output=True)
        
        # Step 4: Configure Git
        log("⚙️ Configuring Git...")
        subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Codex Bot"], cwd=temp_dir, capture_output=True)
        
        # Step 5: Create file based on prompt
        if create_file_from_prompt(temp_dir, PROMPT):
            # Step 6: Check for changes
            log("🔍 Checking for changes...")
            timestamp_branch = f"codex-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            subprocess.run(["git", "checkout", "-b", timestamp_branch], cwd=temp_dir, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
            
            # Check if there are changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=temp_dir,
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                log("📊 Changes detected:")
                for line in result.stdout.strip().split('\n'):
                    log(f"   {line}")
                
                # Commit changes
                commit_message = f"feat: {TITLE} - {PROMPT[:50]}"
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=temp_dir,
                    capture_output=True
                )
                log(f"✅ Changes committed: {commit_message}")
                
                # Only push if we have repository access and in auto mode
                if can_access and clone_success and AUTO_MODE == "auto":
                    log("🚀 Auto-pushing to GitHub...")
                    
                    # Set remote if not already set
                    subprocess.run(
                        ["git", "remote", "add", "origin", f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"],
                        cwd=temp_dir,
                        capture_output=True
                    )
                    
                    push_result = subprocess.run(
                        ["git", "push", "--set-upstream", "origin", timestamp_branch],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    if push_result.returncode == 0:
                        log("✅ Pushed successfully to GitHub")
                        
                        # Create PR
                        log("📝 Creating Pull Request...")
                        try:
                            g = Github(GITHUB_TOKEN)
                            repo = g.get_repo(REPO_NAME)
                            pr = repo.create_pull(
                                title=f"🤖 {TITLE}",
                                body=f"**Generated by Codex Terminal**\n\n**Prompt:** {PROMPT}\n\n---\n*Automated PR created by Harmonia Framework*",
                                head=timestamp_branch,
                                base=default_branch
                            )
                            log(f"✅ PR created successfully!")
                            log(f"   URL: {pr.html_url}")
                        except Exception as e:
                            log(f"⚠️ Could not create PR: {str(e)}")
                            if "pull request already exists" in str(e).lower():
                                log("   💡 A PR already exists for this branch")
                    else:
                        log(f"⚠️ Push failed: {push_result.stderr}")
                elif not can_access:
                    log("⚠️ Skipping push - no repository access")
                elif not clone_success:
                    log("⚠️ Skipping push - repository not cloned")
                else:
                    log("ℹ️ Interactive mode - not pushing automatically")
            else:
                log("ℹ️ No changes detected")
        
        log("=" * 60)
        log("✅ CODEX EXECUTION COMPLETED")
        log("=" * 60)
        return 0
        
    except Exception as e:
        log("=" * 60)
        log(f"❌ CODEX EXECUTION FAILED")
        log("=" * 60)
        log(f"Error: {str(e)}")
        log(f"Type: {type(e).__name__}")
        log("Stack trace:")
        for line in traceback.format_exc().split('\n'):
            log(f"  {line}")
        return 1
        
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                log("🧹 Cleaned up temp directory")
            except Exception as e:
                log(f"⚠️ Could not clean up temp directory: {str(e)}")

if __name__ == "__main__":
    sys.exit(run())