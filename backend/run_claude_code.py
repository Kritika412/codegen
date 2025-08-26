"""Run Claude Code CLI with automation and git workflow."""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from dotenv import load_dotenv
from github import Github
import json
import signal

# === Environment ===
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === CLI arguments ===
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Help improve this codebase"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Claude Code improvements"

def get_default_branch(repo_name: str) -> str:
    """Get the default branch of the repository using GitHub API."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        return repo.default_branch
    except Exception as e:
        print(f"⚠️ Could not get default branch via API: {e}", flush=True)
        return "main"

def find_claude_code_cli() -> str:
    """Locate the claude_code CLI binary"""
    # Try different possible names
    possible_names = ["claude_code", "claude-code", "claudecode", "claude"]
    
    for cmd in possible_names:
        if platform.system() == "Windows":
            cmd += ".exe"
        path = shutil.which(cmd)
        if path:
            print(f"🔍 Claude Code CLI path: {path}", flush=True)
            return path
    
    # Try npm global installs
    try:
        result = subprocess.run(["npm", "list", "-g", "--depth=0"], 
                              capture_output=True, text=True)
        if "claude-code" in result.stdout or "@anthropic/claude-code" in result.stdout:
            return "claude-code"
    except:
        pass
    
    raise FileNotFoundError("Claude Code CLI not found. Install with: npm install -g @anthropic/claude-code")

def clone_repo_safely(repo_name: str, temp_dir: str, token: str) -> str:
    """Clone repository and return the actual default branch."""
    token_url = f"https://{token}@github.com/{repo_name}.git"
    
    try:
        subprocess.run(["git", "clone", token_url, temp_dir], check=True)
        
        result = subprocess.run(
            ["git", "branch", "--show-current"], 
            cwd=temp_dir, 
            capture_output=True, 
            text=True, 
            check=True
        )
        current_branch = result.stdout.strip()
        print(f"📍 Cloned on branch: {current_branch}", flush=True)
        return current_branch
        
    except subprocess.CalledProcessError:
        print("⚠️ Standard clone failed, trying to determine default branch...", flush=True)
        default_branch = get_default_branch(repo_name)
        
        try:
            subprocess.run(["git", "clone", "--branch", default_branch, token_url, temp_dir], check=True)
            return default_branch
        except subprocess.CalledProcessError:
            for branch in ["master", "develop", "dev"]:
                try:
                    subprocess.run(["git", "clone", "--branch", branch, token_url, temp_dir], check=True)
                    print(f"✅ Successfully cloned using branch: {branch}", flush=True)
                    return branch
                except subprocess.CalledProcessError:
                    continue
            
            raise Exception(f"Could not clone repository {repo_name} with any common branch names")

def create_claude_md_file(cwd: str, prompt: str):
    """Create a CLAUDE.md file with instructions for Claude."""
    claude_md_content = f"""# Claude Instructions

## Task
{prompt}

## Context
This is an automated run using Claude Code CLI. Please analyze the codebase and make improvements based on the task above.

## Guidelines
- Make practical, useful changes
- Follow best practices for the detected language/framework
- Add documentation where helpful
- Improve code quality and structure
- Fix any obvious issues you find

## Auto-commit
After making changes, the system will automatically commit and create a PR.
"""
    
    claude_md_path = os.path.join(cwd, "CLAUDE.md")
    with open(claude_md_path, "w") as f:
        f.write(claude_md_content)
    
    print(f"📝 Created CLAUDE.md with task instructions", flush=True)
    return claude_md_path

def run_claude_code_automated(claude_path: str, prompt: str, cwd: str, timeout: int = 600) -> tuple[bool, str]:
    """Execute Claude Code with automation."""
    env = os.environ.copy()
    if ANTHROPIC_API_KEY:
        env["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    # Create CLAUDE.md file for context
    create_claude_md_file(cwd, prompt)
    
    # Try different command variations
    commands_to_try = [
        [claude_path, "--non-interactive", prompt],
        [claude_path, "--batch", prompt],
        [claude_path, "--auto", prompt],
        [claude_path, prompt, "--yes"],
        [claude_path, prompt]
    ]
    
    for cmd in commands_to_try:
        print(f"🚀 Trying Claude Code command: {' '.join(cmd)}", flush=True)
        
        try:
            # Run with timeout
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout + result.stderr
            print(f"📤 Claude Code output:\n{output}", flush=True)
            
            if result.returncode == 0:
                print("✅ Claude Code completed successfully", flush=True)
                return True, output
            else:
                print(f"⚠️ Command failed with code {result.returncode}, trying next...", flush=True)
                continue
                
        except subprocess.TimeoutExpired:
            print(f"⚠️ Command timed out after {timeout} seconds", flush=True)
            continue
        except FileNotFoundError:
            print(f"⚠️ Command not found: {cmd[0]}", flush=True)
            continue
        except Exception as e:
            print(f"⚠️ Error running command: {e}", flush=True)
            continue
    
    # If all commands failed, try interactive mode with input simulation
    print("🔄 Trying interactive mode with automated responses...", flush=True)
    return run_claude_interactive(claude_path, prompt, cwd, timeout)

def run_claude_interactive(claude_path: str, prompt: str, cwd: str, timeout: int) -> tuple[bool, str]:
    """Run Claude Code in interactive mode with automated responses."""
    env = os.environ.copy()
    if ANTHROPIC_API_KEY:
        env["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    try:
        # Start interactive session
        process = subprocess.Popen(
            [claude_path],
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Send the prompt and commands
        commands = [
            prompt,  # The main prompt
            "/status",  # Check status
            "/help",   # Get help if needed
            "exit",    # Exit when done
            "\n",      # Final newline
        ]
        
        all_output = []
        
        for i, command in enumerate(commands):
            if process.poll() is not None:
                break
                
            print(f"📤 Sending: {command}", flush=True)
            try:
                process.stdin.write(command + "\n")
                process.stdin.flush()
            except BrokenPipeError:
                break
            
            # Give time for processing
            time.sleep(2)
            
            # Try to read output
            try:
                output = process.stdout.read(1024)
                if output:
                    all_output.append(output)
                    print(f"📥 Received: {output[:200]}...", flush=True)
            except:
                pass
        
        # Wait for completion
        try:
            stdout, stderr = process.communicate(timeout=30)
            all_output.extend([stdout, stderr])
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            all_output.extend([stdout, stderr])
        
        full_output = "\n".join(filter(None, all_output))
        success = process.returncode == 0 or len(full_output) > 100  # Assume success if we got substantial output
        
        return success, full_output
        
    except Exception as e:
        print(f"❌ Error in interactive mode: {e}", flush=True)
        return False, str(e)

def main() -> None:
    temp_dir = tempfile.mkdtemp()
    try:
        print("📥 Cloning repo...", flush=True)
        
        # Clone repo and get the actual default branch
        default_branch = clone_repo_safely(REPO_NAME, temp_dir, GITHUB_TOKEN)
        
        # Set up git remote
        token_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
        subprocess.run(["git", "remote", "set-url", "origin", token_url], cwd=temp_dir, check=True)
        
        # Run Claude Code
        claude_path = find_claude_code_cli()
        success, output = run_claude_code_automated(claude_path, PROMPT, temp_dir)
        
        print("🔍 Checking for changes...", flush=True)
        
        # Configure git
        subprocess.run(["git", "config", "user.email", "claude@anthropic.com"], cwd=temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Claude Code Agent"], cwd=temp_dir, check=True)
        
        # Stage all changes (including CLAUDE.md)
        subprocess.run(["git", "add", "-A"], cwd=temp_dir, check=True)
        
        # Check if there are changes to commit
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=temp_dir)
        if diff.returncode == 0:
            print("⚠️ No changes to commit.", flush=True)
            return
        
        # Show what changed
        try:
            diff_output = subprocess.run(
                ["git", "diff", "--cached", "--name-status"], 
                cwd=temp_dir, 
                capture_output=True, 
                text=True,
                check=True
            )
            print(f"📝 Changes detected:\n{diff_output.stdout}", flush=True)
        except:
            print("📝 Changes detected (could not show details)", flush=True)
        
        # Create new branch for changes
        branch = f"claude-code-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_dir, check=True)
        
        # Commit changes
        commit_msg = f"feat: {PROMPT[:50]}{'...' if len(PROMPT) > 50 else ''}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=temp_dir, check=True)
        
        print("🚀 Pushing changes...", flush=True)
        
        # Push to new branch
        push = subprocess.run([
            "git", "push", "--set-upstream", "origin", branch
        ], cwd=temp_dir, capture_output=True, text=True)
        
        if push.returncode != 0:
            print(f"❌ Push failed: {push.stderr}", flush=True)
            return
        
        print("✅ Pushed successfully!", flush=True)
        
        # Create Pull Request
        try:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            
            pr_body = f"""**Automated Claude Code Changes**

**Prompt:** {PROMPT}

**Execution Summary:**
- Success: {success}
- Changes committed and pushed automatically
- Generated using Claude Code CLI

**Output:**
```
{output[:1000]}{'...' if len(output) > 1000 else ''}
```

This PR was created automatically by the Claude Code agent.
"""
            
            pr = repo.create_pull(
                title=f"🤖 Claude Code: {TITLE}",
                body=pr_body,
                head=branch,
                base=default_branch,
            )
            
            print(f"✅ PR created: {pr.html_url}", flush=True)
            
        except Exception as e:
            print(f"⚠️ PR creation failed: {e}", flush=True)
            print(f"But changes were pushed to branch: {branch}", flush=True)
        
        print("🎉 Claude Code automation completed!", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        sys.exit(1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()