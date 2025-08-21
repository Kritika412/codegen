import subprocess
import tempfile
import os
import shutil
import sys
import platform
import shutil as sh
from github import Github
from dotenv import load_dotenv
from datetime import datetime

# === Load environment variables ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# === Configuration ===
BRANCH = "main"
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Write helpful backend code"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
REPO_URL = f"https://github.com/{REPO_NAME}.git"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex Todo"

print(f'📝 Prompt: {PROMPT}', flush=True)
print(f'📦 Repository: {REPO_NAME}', flush=True)
print(f'🏷️ Title: {TITLE}', flush=True)
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
            f"npm install -g codex\n"
            f"And that it's on your PATH."
        )
    return codex_path

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
        print("🎯 Using full-auto approval mode", flush=True)
        
        codex_path = find_codex_cli()
        
        # Run Codex with real-time output
        print("🚀 Starting Codex...", flush=True)
        print("-" * 60, flush=True)
        
        codex_process = subprocess.Popen(
            [codex_path, "--approval-mode", "full-auto", PROMPT], 
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        while True:
            output = codex_process.stdout.readline()
            if output == '' and codex_process.poll() is not None:
                break
            if output:
                print(output.strip(), flush=True)
        
        return_code = codex_process.wait()
        
        if return_code != 0:
            raise Exception(f"Codex CLI failed with exit code {return_code}")
        
        print("-" * 60, flush=True)
        print("✅ Codex completed successfully", flush=True)
        
        print("🔍 Checking for changes...", flush=True)
        timestamp_branch = f"codex-todo-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
            
            print("💾 Committing changes...", flush=True)
            subprocess.run(["git", "commit", "-m", f"feat: codex changes for '{PROMPT}'"], cwd=temp_dir, check=True)
            
            print("🟢 Codex changes committed.", flush=True)
            
            # In interactive mode, ask user. In auto mode, just push
            if len(sys.argv) > 4 and sys.argv[4] == "auto":
                push_choice = "y"
                print("🤖 Auto mode: Pushing automatically", flush=True)
            else:
                push_choice = input("🟢 Do you want to push to GitHub and create a PR? (y/n): ").strip().lower()
            
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
                            body=f"**Generated by Codex CLI**\n\nPrompt: {PROMPT}\n\n---\n*Automated PR created by Harmonia Framework*",
                            head=timestamp_branch,
                            base=BRANCH
                        )
                        print(f"✅ PR created: {pr.html_url}", flush=True)
                    except Exception as e:
                        print(f"❌ PR creation failed: {str(e)}", flush=True)
                else:
                    print(f"❌ Push failed: {push_result.stderr}", flush=True)
            else:
                print("❌ Push cancelled by user.", flush=True)
        else:
            print("⚠️ No changes to commit.", flush=True)
            
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