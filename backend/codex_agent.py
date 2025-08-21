#!/usr/bin/env python3
"""
Real Codex Agent Script - This is your actual AI coding agent
This script should be separate from your API server (main.py)
"""
import argparse
import sys
import os
import subprocess
import tempfile
import shutil
from github import Github
from dotenv import load_dotenv
from datetime import datetime
import requests
import json

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def log(message):
    """Print with flush for real-time output"""
    print(message, flush=True)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Codex AI Agent')
    parser.add_argument('--prompt', required=True, help='The coding task prompt')
    parser.add_argument('--repo', required=True, help='Target repository (owner/repo)')
    parser.add_argument('--title', required=True, help='Task title')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    return parser.parse_args()

def verify_repository_access(repo_name):
    """Verify that we can access the repository"""
    try:
        log(f"🔍 Verifying access to repository: {repo_name}")
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        
        log(f"✅ Repository found: {repo.full_name}")
        log(f"   - Default branch: {repo.default_branch}")
        log(f"   - Private: {repo.private}")
        
        return True, repo.default_branch
        
    except Exception as e:
        log(f"❌ Repository access verification failed!")
        log(f"   Error: {str(e)}")
        return False, "main"

def ask_user(question, default=None):
    """Ask user for input in interactive mode"""
    if default:
        prompt = f"{question} (default: {default}): "
    else:
        prompt = f"{question}: "
    
    try:
        response = input(prompt).strip()
        return response if response else default
    except KeyboardInterrupt:
        log("\n\n❌ Task cancelled by user")
        sys.exit(1)

def call_openai_api(prompt, system_prompt=None):
    """Call OpenAI API for code generation"""
    if not OPENAI_API_KEY:
        log("❌ OpenAI API key not found")
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 3000
    }
    
    try:
        log("🤖 Calling OpenAI API for code generation...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            generated = result['choices'][0]['message']['content']
            log(f"✅ Generated {len(generated)} characters of code")
            return generated
        else:
            log(f"❌ OpenAI API error: {response.status_code}")
            log(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        log(f"❌ Error calling OpenAI: {str(e)}")
        return None

def interactive_refinement(initial_code, prompt):
    """Allow user to refine the generated code"""
    current_code = initial_code
    
    while True:
        log("\n" + "="*60)
        log("📝 Generated Code Preview:")
        log("="*60)
        
        # Show preview (first 500 chars)
        preview = current_code[:500] + "..." if len(current_code) > 500 else current_code
        print(preview)
        
        log("="*60)
        log("Available actions:")
        log("  [c] continue - Use this code and proceed")
        log("  [r] refine - Make changes to the code") 
        log("  [v] view - See the full code")
        log("  [n] new - Generate completely new code")
        log("  [q] quit - Cancel the task")
        log("="*60)
        
        action = ask_user("What would you like to do?", "continue").lower()
        
        if action in ['continue', 'c', '']:
            return current_code
            
        elif action in ['view', 'v']:
            log("\n" + "="*60)
            log("📄 FULL CODE:")
            log("="*60)
            print(current_code)
            log("="*60)
            
        elif action in ['refine', 'r']:
            refinement = ask_user("What changes would you like me to make?")
            if refinement:
                log("🔄 Refining code...")
                refined_prompt = f"Please modify this code based on the following request:\n\nOriginal request: {prompt}\n\nCode to modify:\n{current_code}\n\nModification request: {refinement}"
                
                system_prompt = "You are a helpful coding assistant. Please modify the provided code according to the user's request. Return only the updated code."
                
                refined_code = call_openai_api(refined_prompt, system_prompt)
                if refined_code:
                    current_code = refined_code
                    log("✅ Code refined successfully!")
                else:
                    log("❌ Failed to refine code, keeping original")
                    
        elif action in ['new', 'n']:
            new_prompt = ask_user("Enter new prompt")
            if new_prompt:
                log("🆕 Generating new code...")
                new_code = call_openai_api(new_prompt)
                if new_code:
                    current_code = new_code
                    log("✅ New code generated!")
                    
        elif action in ['quit', 'q']:
            log("❌ Task cancelled by user")
            sys.exit(0)
        else:
            log("❌ Invalid action. Please choose: c, r, v, n, or q")

def create_files_from_code(temp_dir, generated_code, prompt):
    """Create appropriate files from generated code"""
    log("📁 Creating files from generated code...")
    
    # Determine file types based on content
    files_created = []
    
    # Check for different file types in the generated code
    if "from fastapi import" in generated_code or "app = FastAPI" in generated_code:
        # FastAPI application
        filepath = os.path.join(temp_dir, "app.py")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        files_created.append("app.py")
        
    elif "<!DOCTYPE html" in generated_code or "<html" in generated_code:
        # HTML file
        filepath = os.path.join(temp_dir, "index.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        files_created.append("index.html")
        
    elif "```" in generated_code:
        # Multiple code blocks - extract them
        blocks = generated_code.split("```")
        for i, block in enumerate(blocks):
            if i % 2 == 1:  # Odd indices are code blocks
                lines = block.strip().split('\n')
                if lines:
                    # Try to determine language and filename
                    first_line = lines[0].lower()
                    code_content = '\n'.join(lines[1:]) if len(lines) > 1 else block.strip()
                    
                    if 'python' in first_line or 'py' in first_line:
                        filename = f"script_{i//2 + 1}.py"
                    elif 'html' in first_line:
                        filename = f"page_{i//2 + 1}.html"
                    elif 'javascript' in first_line or 'js' in first_line:
                        filename = f"script_{i//2 + 1}.js"
                    elif 'css' in first_line:
                        filename = f"style_{i//2 + 1}.css"
                    else:
                        filename = f"file_{i//2 + 1}.txt"
                    
                    filepath = os.path.join(temp_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    files_created.append(filename)
    else:
        # Single file - determine type
        if "def " in generated_code or "import " in generated_code:
            filename = "main.py"
        elif "{" in generated_code and "}" in generated_code:
            filename = "script.js"
        else:
            filename = "generated_code.txt"
            
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(generated_code)
        files_created.append(filename)
    
    log(f"✅ Created {len(files_created)} files: {', '.join(files_created)}")
    return files_created

def main():
    """Main function"""
    args = parse_arguments()
    
    log("="*60)
    log("🚀 CODEX AI AGENT STARTED")
    log("="*60)
    log(f"📝 Prompt: {args.prompt[:100]}...")
    log(f"📦 Repository: {args.repo}")
    log(f"🏷️ Title: {args.title}")
    log(f"🎮 Mode: {'Interactive' if args.interactive else 'Auto'}")
    log("="*60)
    
    # Verify repository access
    can_access, default_branch = verify_repository_access(args.repo)
    if not can_access:
        log("⚠️ Continuing without repository access...")
    
    # Generate initial code
    system_prompt = """You are an expert software developer. Generate complete, working code based on the user's requirements. 

    Guidelines:
    - Write production-ready code with proper error handling
    - Include necessary imports and dependencies
    - Add helpful comments
    - Follow best practices for the chosen technology
    - If creating an API, include proper request/response models
    - If creating a web app, make it functional and user-friendly
    
    Respond with clean, well-structured code that can be immediately used."""
    
    generated_code = call_openai_api(args.prompt, system_prompt)
    
    if not generated_code:
        log("❌ Failed to generate code")
        sys.exit(1)
    
    # Interactive refinement if requested
    if args.interactive:
        log("\n🎮 Entering Interactive Mode...")
        final_code = interactive_refinement(generated_code, args.prompt)
    else:
        final_code = generated_code
    
    # Create temporary directory for files
    temp_dir = tempfile.mkdtemp()
    log(f"📁 Working in: {temp_dir}")
    
    try:
        # Clone repository if accessible
        if can_access:
            log("📥 Cloning repository...")
            clone_url = f"https://{GITHUB_TOKEN}@github.com/{args.repo}.git"
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, temp_dir],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                log(f"⚠️ Clone failed: {result.stderr}")
                # Continue with empty directory
        
        # Create files from generated code
        files_created = create_files_from_code(temp_dir, final_code, args.prompt)
        
        # Configure git
        subprocess.run(["git", "config", "user.email", "codex@harmoniaai.com"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Codex AI Agent"], cwd=temp_dir, capture_output=True)
        
        # Create branch and commit
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        branch_name = f"codex-{timestamp}"
        
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
        
        commit_message = f"feat: {args.title}\n\n{args.prompt[:200]}..."
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log("✅ Changes committed successfully")
            
            # Ask about pushing in interactive mode
            should_push = True
            if args.interactive:
                push_response = ask_user("Push to GitHub and create PR? (y/n)", "y")
                should_push = push_response.lower() in ['y', 'yes', '']
            
            if should_push and can_access:
                log("🚀 Pushing to GitHub...")
                push_result = subprocess.run(
                    ["git", "push", "--set-upstream", "origin", branch_name],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True
                )
                
                if push_result.returncode == 0:
                    log("✅ Pushed successfully!")
                    
                    # Create PR
                    try:
                        g = Github(GITHUB_TOKEN)
                        repo = g.get_repo(args.repo)
                        pr = repo.create_pull(
                            title=f"🤖 {args.title}",
                            body=f"**Generated by Codex AI Agent**\n\n**Prompt:** {args.prompt}\n\n**Files Created:** {', '.join(files_created)}\n\n---\n*Automated PR created by Harmonia Codex Framework*",
                            head=branch_name,
                            base=default_branch
                        )
                        log(f"✅ Pull Request created!")
                        log(f"🔗 URL: {pr.html_url}")
                    except Exception as e:
                        log(f"⚠️ Could not create PR: {str(e)}")
                else:
                    log(f"❌ Push failed: {push_result.stderr}")
            else:
                log("ℹ️ Skipping push (user choice or no access)")
        else:
            log("ℹ️ No changes to commit")
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            log("🧹 Cleaned up temporary files")
        except Exception as e:
            log(f"⚠️ Cleanup warning: {str(e)}")
    
    log("="*60)
    log("✅ CODEX AI AGENT COMPLETED")
    log("="*60)

if __name__ == "__main__":
    main()