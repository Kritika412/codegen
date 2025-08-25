import subprocess
import tempfile
import os
import shutil
import sys
import platform
import shutil as sh
import threading
from github import Github
from dotenv import load_dotenv
from datetime import datetime
import pexpect
import time

# === Load environment variables ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === Configuration ===
BRANCH = "main"
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Write helpful backend code"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
REPO_URL = f"https://github.com/{REPO_NAME}.git"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex Todo"

# Enable interactive mode by default. Pass "auto" as the fourth argument
# to enable automatic prompt responses.
AUTO_MODE = len(sys.argv) > 4 and sys.argv[4] == "auto"

print(f'📝 Prompt: {PROMPT}', flush=True)
print(f'📦 Repository: {REPO_NAME}', flush=True)
print(f'🏷️ Title: {TITLE}', flush=True)
print(f'🤖 Auto Mode: {AUTO_MODE}', flush=True)
print('=' * 60, flush=True)

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

def find_codex_cli():
    """Find the codex CLI path based on platform"""
    is_windows = platform.system() == "Windows"
    cmd_name = "codex.cmd" if is_windows else "codex"
    codex_path = sh.which(cmd_name)
    print(f"🔍 Codex CLI path: {codex_path}", flush=True)
    
    if not codex_path:
        raise FileNotFoundError(
            f"❌ Codex CLI not found. Make sure it's installed globally with:\n\n"
            f"npm install -g @openai/codex\n"
            f"And that it's on your PATH."
        )
    return codex_path

def run_codex_with_pty(codex_path, prompt, temp_dir):
    """Run Codex CLI using PTY to handle raw mode properly"""
    print("🚀 Starting Codex with PTY...", flush=True)
    print("-" * 60, flush=True)
    
    try:
        # Set up environment for Codex
        codex_env = os.environ.copy()
        codex_env.update({
            'OPENAI_API_KEY': OPENAI_API_KEY,
            'TERM': 'xterm-256color',
            'COLUMNS': '120',
            'LINES': '30'
        })
        
        # Create the command
        cmd = f'{codex_path} --approval-mode full-auto "{prompt}"'
        
        print(f"🔧 Running: {cmd}", flush=True)
        print("🎯 Using PTY for proper terminal emulation", flush=True)
        
        # Spawn the process with PTY
        child = pexpect.spawn(
            cmd,
            cwd=temp_dir,
            env=codex_env,
            timeout=300,  # 5 minute timeout
            encoding='utf-8',
            dimensions=(30, 120)  # rows, cols
        )

        # Forward user input to Codex in interactive mode
        if not AUTO_MODE:
            def forward_input():
                while True:
                    try:
                        data = sys.stdin.read(1)
                        if not data:
                            break
                        if data == '\x03':
                            child.sendcontrol('c')
                        else:
                            child.send(data)
                    except Exception:
                        break

            threading.Thread(target=forward_input, daemon=True).start()
        
        # Set up real-time output streaming
        output_buffer = []
        
        def print_and_store(data):
            if data:
                print(data, end='', flush=True)
                output_buffer.append(data)
        
        try:
            while True:
                try:
                    # Read output with timeout
                    index = child.expect([
                        pexpect.EOF,
                        pexpect.TIMEOUT,
                        r'.*\n',  # Any line
                        r'.*\?.*',  # Questions (prompts)
                        r'.*\(y/n\).*',  # Yes/no prompts
                        r'.*press.*enter.*',  # Enter prompts
                    ], timeout=2)
                    
                    if index == 0:  # EOF
                        print_and_store(child.before)
                        break
                    elif index == 1:  # TIMEOUT
                        # Check if there's any output to read
                        if child.before:
                            print_and_store(child.before)
                        continue
                    elif index in [2, 3, 4, 5]:  # Output or prompts
                        # Print the matched output
                        if child.before:
                            print_and_store(child.before)
                        if child.after and child.after != pexpect.EOF:
                            print_and_store(child.after)

                        # Handle prompts automatically in auto mode
                        if AUTO_MODE and index in [3, 4, 5]:
                            # Generic questions: send empty line
                            # Yes/no prompts: answer 'y'
                            # Press enter prompts: send newline
                            print("\n🤖 Auto-responding to prompt...", flush=True)
                            response = '' if index in [3, 5] else 'y'
                            child.sendline(response)
                            time.sleep(0.5)
                
                except pexpect.TIMEOUT:
                    # Timeout is normal, just continue
                    continue
                except pexpect.EOF:
                    # Process ended
                    if child.before:
                        print_and_store(child.before)
                    break
        
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user", flush=True)
            child.terminate()
            return False
        
        # Wait for process to complete
        child.close()
        exit_code = child.exitstatus
        
        print("-" * 60, flush=True)
        print(f"✅ Codex PTY process completed with exit code: {exit_code}", flush=True)
        
        # Return success if exit code is 0 or if we got output (some versions exit with 1 but still work)
        return exit_code == 0 or len(output_buffer) > 0
        
    except pexpect.exceptions.ExceptionPexpect as e:
        print(f"❌ PTY error: {str(e)}", flush=True)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}", flush=True)
        return False

def run():
    temp_dir = tempfile.mkdtemp()
    try:
        print("📥 Cloning repo...", flush=True)
        token_clone_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
        
        # Clone with more verbose output
        result = subprocess.run(
            ["git", "clone", "--branch", BRANCH, token_clone_url, temp_dir], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Clone failed: {result.stderr}", flush=True)
            # Try without branch specification
            print("🔄 Retrying without branch specification...", flush=True)
            result = subprocess.run(
                ["git", "clone", token_clone_url, temp_dir], 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Clone failed: {result.stderr}")
        
        print("✅ Repository cloned successfully", flush=True)
        
        print("🔑 Updating Git remote with token...", flush=True)
        token_remote_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
        subprocess.run(["git", "remote", "set-url", "origin", token_remote_url], cwd=temp_dir, check=True)
        
        print(f"🤖 Running Codex CLI with prompt: {PROMPT}", flush=True)
        
        codex_path = find_codex_cli()
        
        # Run Codex with PTY
        codex_success = run_codex_with_pty(codex_path, PROMPT, temp_dir)
        
        if not codex_success:
            print("⚠️ Codex had issues, but continuing to check for changes...", flush=True)
        
        print("🔍 Checking for changes...", flush=True)
        timestamp_branch = f"codex-todo-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Configure git user
        subprocess.run(["git", "config", "user.email", "codex@harmoniaai.com"], cwd=temp_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Codex Agent"], cwd=temp_dir, capture_output=True)
        
        subprocess.run(["git", "checkout", "-b", timestamp_branch], cwd=temp_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
        
        # Check if there are changes
        has_changes = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=temp_dir)
        
        if has_changes.returncode != 0:
            # Show what changed
            diff_result = subprocess.run(["git", "diff", "--cached", "--stat"], cwd=temp_dir, capture_output=True, text=True)
            if diff_result.stdout:
                print("📊 Changes detected:", flush=True)
                print(diff_result.stdout, flush=True)
            
            # Show some sample changes
            files_result = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=temp_dir, capture_output=True, text=True)
            if files_result.stdout:
                files = files_result.stdout.strip().split('\n')
                print(f"📝 Modified files: {', '.join(files)}", flush=True)
            
            print("💾 Committing changes...", flush=True)
            subprocess.run(["git", "commit", "-m", f"feat: codex changes for '{PROMPT}'"], cwd=temp_dir, check=True)
            
            print("🟢 Codex changes committed.", flush=True)
            
            # Auto-push in auto mode, ask in interactive mode
            if AUTO_MODE:
                push_choice = "y"
                print("🤖 Auto mode: Pushing automatically", flush=True)
            else:
                try:
                    push_choice = input("🟢 Do you want to push to GitHub and create a PR? (y/n): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    push_choice = "y"  # Default to yes if input fails
                    print("🤖 Input not available, defaulting to yes", flush=True)
            
            if push_choice == 'y':
                print("🚀 Pushing changes...", flush=True)
                push_result = subprocess.run(
                    ["git", "push", "--set-upstream", "origin", timestamp_branch], 
                    cwd=temp_dir, 
                    capture_output=True, 
                    text=True
                )
                
                if push_result.returncode == 0:
                    print("✅ Pushed successfully!", flush=True)
                    
                    print("🔧 Creating Pull Request...", flush=True)
                    try:
                        g = Github(GITHUB_TOKEN)
                        repo = g.get_repo(REPO_NAME)
                        pr = repo.create_pull(
                            title=f"🤖 Codex: {TITLE}",
                            body=f"**Generated by Codex CLI with PTY**\n\nPrompt: {PROMPT}\n\n---\n*Automated PR created by Harmonia Framework*",
                            head=timestamp_branch,
                            base=BRANCH
                        )
                        print(f"✅ PR created: {pr.html_url}", flush=True)
                    except Exception as e:
                        print(f"❌ PR creation failed: {str(e)}", flush=True)
                        print("💡 You can manually create a PR from the pushed branch", flush=True)
                else:
                    print(f"❌ Push failed: {push_result.stderr}", flush=True)
            else:
                print("❌ Push cancelled by user.", flush=True)
        else:
            print("⚠️ No changes to commit.", flush=True)
            print("💡 Codex may not have made any file changes, or changes were reverted", flush=True)
            
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        import traceback
        print("🔍 Full error details:", flush=True)
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up temporary directory...", flush=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("✅ Cleanup complete", flush=True)

if __name__ == "__main__":
    run()
