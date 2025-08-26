"""Run Codex CLI with complete automation - no user interaction required."""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import pty
import select
import signal
import time
from datetime import datetime
from dotenv import load_dotenv
from github import Github
import threading

# === Environment ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === CLI arguments ===
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Write helpful backend code"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex change"

def get_default_branch(repo_name: str) -> str:
    """Get the default branch of the repository using GitHub API."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_name)
        return repo.default_branch
    except Exception as e:
        print(f"⚠️ Could not get default branch via API: {e}", flush=True)
        return "master"  # fallback

def find_codex_cli() -> str:
    """Locate the codex CLI binary"""
    cmd = "codex.cmd" if platform.system() == "Windows" else "codex"
    path = shutil.which(cmd)
    if not path:
        raise FileNotFoundError("Codex CLI not found. Install with `npm install -g @openai/codex`.")
    print(f"🔍 Codex CLI path: {path}", flush=True)
    return path

def clone_repo_safely(repo_name: str, temp_dir: str, token: str) -> str:
    """Clone repository and return the actual default branch."""
    token_url = f"https://{token}@github.com/{repo_name}.git"
    
    # First, try to clone without specifying a branch (gets default branch)
    try:
        subprocess.run(["git", "clone", token_url, temp_dir], check=True)
        
        # Get the current branch name
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
        # If that fails, try to get default branch from API
        print("⚠️ Standard clone failed, trying to determine default branch...", flush=True)
        default_branch = get_default_branch(repo_name)
        
        try:
            subprocess.run(["git", "clone", "--branch", default_branch, token_url, temp_dir], check=True)
            return default_branch
        except subprocess.CalledProcessError:
            # Last resort: try common branch names
            for branch in ["master", "develop", "dev"]:
                try:
                    subprocess.run(["git", "clone", "--branch", branch, token_url, temp_dir], check=True)
                    print(f"✅ Successfully cloned using branch: {branch}", flush=True)
                    return branch
                except subprocess.CalledProcessError:
                    continue
            
            raise Exception(f"Could not clone repository {repo_name} with any common branch names")

def run_codex_fully_automated(codex_path: str, prompt: str, cwd: str, timeout: int = 300) -> tuple[bool, str]:
    """Execute Codex with complete automation - sends automatic responses."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = OPENAI_API_KEY or ""
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "120"
    env["LINES"] = "40"
    env["CI"] = "true"  # Some CLIs behave differently in CI mode
    
    cmd = [codex_path, "--approval-mode", "full-auto", prompt]
    print(f"🚀 Running Codex with full automation: {' '.join(cmd)}", flush=True)
    
    output_lines = []
    success = False
    process = None
    
    waiting_for_input = False
    last_output_time = time.time()
    
    def send_automatic_responses(master_fd, process):
        """Send automatic responses only when actually needed."""
        nonlocal waiting_for_input, last_output_time
        
        while process and process.poll() is None:
            try:
                # Only send responses if we're waiting for input and no recent output
                current_time = time.time()
                if waiting_for_input and (current_time - last_output_time) > 3:
                    print("📤 Detected Codex waiting for input - sending Ctrl+C to exit", flush=True)
                    os.write(master_fd, b'\x03')
                    waiting_for_input = False
                    time.sleep(1)  # Give it time to process
                
                time.sleep(1)  # Check every second
                
            except (OSError, BrokenPipeError):
                break
    
    def read_and_process_output(master_fd):
        """Read output and detect when Codex is waiting for input."""
        nonlocal output_lines, success, waiting_for_input, last_output_time
        
        buffer = ""  # Buffer to accumulate partial lines
        
        while True:
            try:
                # Check if data is available to read
                ready, _, _ = select.select([master_fd], [], [], 1.0)
                if ready:
                    data = os.read(master_fd, 1024)
                    if not data:
                        break
                    
                    text = data.decode('utf-8', errors='ignore')
                    buffer += text
                    last_output_time = time.time()
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        output_lines.append(line + '\n')
                        print(line, flush=True)
                        
                        # Check for completion indicators (more specific)
                        lower_line = line.lower()
                        
                        # Don't treat command output headers as success
                        if "command.stdout (code:" in lower_line:
                            continue
                            
                        if any(indicator in lower_line for indicator in [
                            "done!", "completed", "✅", "success", 
                            "applied", "finished", "created", 
                            "you can open", "verify", "file named", "added",
                            "new readme", "readme.md", "documentation added",
                            "i've added", "i've created", "here's what was done"
                        ]):
                            success = True
                            print(f"✅ SUCCESS DETECTED: {line}", flush=True)
                        
                        # Check if Codex is asking for clarification or has questions
                        if any(question_indicator in lower_line for question_indicator in [
                            "what would you like", "please specify", "can you clarify",
                            "which", "how should", "do you want", "would you prefer",
                            "unclear", "ambiguous", "need more information"
                        ]):
                            print(f"\n🤔 CODEX NEEDS CLARIFICATION: {line}", flush=True)
                            print("💡 Suggestion: Update your prompt to be more specific about:", flush=True)
                            print("   - File name and location", flush=True)
                            print("   - Exact content or structure needed", flush=True)
                            print("   - Any specific requirements", flush=True)
                        
                        # Detect interactive prompts that need termination
                        if any(prompt_text in lower_line for prompt_text in [
                            "ctrl+c to exit", "enter to send", "/ to see commands",
                            "press esc", "interrupt", "type your response"
                        ]):
                            waiting_for_input = True
                            print(f"\n⚠️ CODEX WAITING FOR INPUT: {line}", flush=True)
                            print("🛑 Will auto-exit in 3 seconds if no output...", flush=True)
                    
                    # Handle partial line at end of buffer
                    if buffer:
                        # Check if it looks like a prompt
                        if any(prompt_text in buffer.lower() for prompt_text in [
                            "ctrl+c to exit", "enter to send", "/ to see commands"
                        ]):
                            waiting_for_input = True
                            print(f"\n⚠️ CODEX PROMPT DETECTED: {buffer}", flush=True)
                            print("🛑 Will auto-exit in 5 seconds if no output...", flush=True)
                            output_lines.append(buffer)
                            print(buffer, end='', flush=True)
                            buffer = ""
                
            except (OSError, ValueError):
                break
    
    try:
        # Create PTY
        master_fd, slave_fd = pty.openpty()
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid if platform.system() != "Windows" else None
        )
        
        # Close slave fd in parent process
        os.close(slave_fd)
        
        # Start threads for reading output and sending responses
        read_thread = threading.Thread(target=read_and_process_output, args=(master_fd,))
        response_thread = threading.Thread(target=send_automatic_responses, args=(master_fd, process))
        
        read_thread.daemon = True
        response_thread.daemon = True
        
        read_thread.start()
        response_thread.start()
        
        # Wait for process with timeout, but exit early if we detect success
        start_time = time.time()
        idle_start = None
        
        while process.poll() is None and (time.time() - start_time) < timeout:
            current_time = time.time()
            
            # Track idle time (no output)
            if current_time - last_output_time > 3:
                if idle_start is None:
                    idle_start = current_time
                    
                # If we've been idle for a while and detected success, exit
                if success and (current_time - idle_start) > 5:
                    print("✅ Success detected with extended idle time - terminating", flush=True)
                    break
                    
                # If we've been idle for too long, assume we're stuck
                if (current_time - idle_start) > 15:
                    print("⚠️ Extended idle time detected - likely stuck, terminating", flush=True)
                    break
            else:
                idle_start = None
            
            time.sleep(1)
        
        # If still running, terminate it
        if process.poll() is None:
            print(f"\n⚠️ Terminating Codex after {timeout} seconds", flush=True)
            try:
                if platform.system() != "Windows":
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
                
                # Wait a bit for graceful termination
                time.sleep(2)
                
                if process.poll() is None:
                    if platform.system() != "Windows":
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
            except ProcessLookupError:
                pass
        
        # Wait for threads to finish
        read_thread.join(timeout=5)
        response_thread.join(timeout=5)
        
        # Close master fd
        os.close(master_fd)
        
        exit_code = process.returncode if process.returncode is not None else 1
        output_text = ''.join(output_lines)
        
        print(f"\n✅ Codex finished with exit code: {exit_code}", flush=True)
        
        # Consider it successful even if exit code isn't 0, as long as we saw success indicators
        return success or exit_code == 0, output_text
        
    except Exception as e:
        print(f"❌ Error running Codex: {e}", flush=True)
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
        
        # Run Codex with full automation
        codex_path = find_codex_cli()
        success, output = run_codex_fully_automated(codex_path, PROMPT, temp_dir)
        
        print("🔍 Checking for changes...", flush=True)
        
        # Configure git
        subprocess.run(["git", "config", "user.email", "codex@harmoniaai.com"], cwd=temp_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Codex Agent"], cwd=temp_dir, check=True)
        
        # Stage all changes
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
        branch = f"codex-auto-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
            
            pr_body = f"""**Automated Codex Changes**

**Prompt:** {PROMPT}

This PR was created automatically by the Codex agent.

**Execution Summary:**
- Success: {success}
- Changes committed and pushed automatically
"""
            
            pr = repo.create_pull(
                title=f"🤖 {TITLE}",
                body=pr_body,
                head=branch,
                base=default_branch,
            )
            
            print(f"✅ PR created: {pr.html_url}", flush=True)
            
        except Exception as e:
            print(f"⚠️ PR creation failed: {e}", flush=True)
            print(f"But changes were pushed to branch: {branch}", flush=True)
        
        print("🎉 Fully automated Codex execution completed!", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        sys.exit(1)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()