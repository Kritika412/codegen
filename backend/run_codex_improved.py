#!/usr/bin/env python3
"""
Improved Codex runner that works without TTY and creates actual files
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

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Configuration from arguments
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Create a simple HTML page"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex Task"
AUTO_MODE = sys.argv[4] if len(sys.argv) > 4 else "auto"

def log(message):
    """Print with flush for real-time output"""
    print(message, flush=True)

def generate_code_with_openai(prompt):
    """Use OpenAI API directly to generate code"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare the prompt for code generation
        system_prompt = """You are a helpful coding assistant. Generate complete, working code based on the user's request. 
        Always include proper file extensions in your response. 
        For HTML requests, create a complete, valid HTML5 document.
        Respond with just the code, no explanations."""
        
        data = {
            "model": "gpt-4o-mini",  # Use a model that works
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            log(f"⚠️ OpenAI API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        log(f"⚠️ Error calling OpenAI: {str(e)}")
        return None

def create_file_from_prompt(temp_dir, prompt):
    """Create a file based on the prompt"""
    log("🤖 Generating code with AI...")
    
    # First try to use OpenAI API
    generated_code = generate_code_with_openai(prompt)
    
    if generated_code:
        # Determine file type and name
        if "html" in prompt.lower():
            filename = "index.html"
        elif "python" in prompt.lower() or ".py" in prompt.lower():
            filename = "generated_script.py"
        elif "javascript" in prompt.lower() or ".js" in prompt.lower():
            filename = "script.js"
        else:
            filename = "generated_file.txt"
        
        filepath = os.path.join(temp_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(generated_code)
        
        log(f"✅ Created file: {filename}")
        log(f"📄 File content preview (first 500 chars):")
        log("-" * 40)
        log(generated_code[:500])
        if len(generated_code) > 500:
            log("... (truncated)")
        log("-" * 40)
        
        return True
    
    else:
        # Fallback: Create a simple HTML file based on the prompt
        log("📝 Creating fallback HTML file...")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Codex Generated Page</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 3rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 25px 45px rgba(0, 0, 0, 0.2);
            max-width: 600px;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        .prompt {{
            font-size: 1rem;
            opacity: 0.9;
            margin-top: 2rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }}
        .timestamp {{
            margin-top: 2rem;
            font-size: 0.8rem;
            opacity: 0.7;
        }}
        .status {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background: rgba(0, 255, 0, 0.2);
            border: 1px solid rgba(0, 255, 0, 0.5);
            border-radius: 20px;
            margin-top: 1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Hello! We are testing Codex on Terminal</h1>
        <div class="status">✅ Successfully Generated</div>
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
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        log(f"✅ Created fallback file: index.html")
        return True

def run():
    temp_dir = None
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        log(f"📁 Created temp directory: {temp_dir}")
        
        # Clone repository
        log(f"📥 Cloning repository: {REPO_NAME}...")
        token_clone_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
        
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", "main", token_clone_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            log(f"⚠️ Clone failed: {result.stderr}")
            log("📁 Using temp directory without cloning...")
        else:
            log("✅ Repository cloned successfully")
        
        # Configure Git
        log("🔐 Configuring Git...")
        subprocess.run(["git", "config", "user.email", "codex@example.com"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Codex Bot"], cwd=temp_dir, capture_output=True)
        
        # Create file based on prompt
        if create_file_from_prompt(temp_dir, PROMPT):
            # Check for changes
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
                log(result.stdout)
                
                # Commit changes
                subprocess.run(
                    ["git", "commit", "-m", f"feat: {TITLE} - {PROMPT[:50]}"],
                    cwd=temp_dir,
                    capture_output=True
                )
                log("✅ Changes committed")
                
                if AUTO_MODE == "auto":
                    log("🚀 Auto-pushing to GitHub...")
                    push_result = subprocess.run(
                        ["git", "push", "--set-upstream", "origin", timestamp_branch],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    if push_result.returncode == 0:
                        log("✅ Pushed successfully")
                        
                        # Create PR
                        log("📝 Creating Pull Request...")
                        try:
                            g = Github(GITHUB_TOKEN)
                            repo = g.get_repo(REPO_NAME)
                            pr = repo.create_pull(
                                title=f"🤖 {TITLE}",
                                body=f"**Generated by Codex Terminal**\n\n**Prompt:** {PROMPT}\n\n---\n*Automated PR created by Harmonia Framework*",
                                head=timestamp_branch,
                                base="main"
                            )
                            log(f"✅ PR created: {pr.html_url}")
                        except Exception as e:
                            log(f"⚠️ Could not create PR: {str(e)}")
                    else:
                        log(f"⚠️ Push failed: {push_result.stderr}")
                else:
                    log("ℹ️ Interactive mode - not pushing automatically")
            else:
                log("ℹ️ No changes detected")
        
        return 0
        
    except Exception as e:
        log(f"❌ Error: {str(e)}")
        import traceback
        log(traceback.format_exc())
        return 1
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                log("🧹 Cleaned up temp directory")
            except:
                log("⚠️ Could not clean up temp directory")

if __name__ == "__main__":
    sys.exit(run())