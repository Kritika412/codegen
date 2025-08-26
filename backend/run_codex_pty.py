"""Run Codex CLI, auto-commit any changes, and create a PR."""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

from dotenv import load_dotenv
from github import Github


# === Environment ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# === CLI arguments ===
BRANCH = "main"
PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Write helpful backend code"
REPO_NAME = sys.argv[2] if len(sys.argv) > 2 else "hail007/Agent-Testing"
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Codex change"


def find_codex_cli() -> str:
    """Locate the codex CLI binary"""
    cmd = "codex.cmd" if platform.system() == "Windows" else "codex"
    path = shutil.which(cmd)
    if not path:
        raise FileNotFoundError("Codex CLI not found. Install with `npm install -g @openai/codex`.")
    print(f"🔍 Codex CLI path: {path}", flush=True)
    return path


def run_codex(codex_path: str, prompt: str, cwd: str) -> bool:
    """Execute Codex in full‑auto mode and stream output."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = OPENAI_API_KEY or ""
    cmd = [codex_path, "--approval-mode", "full-auto", prompt]
    print(f"🚀 Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd, env=env)
    print(f"✅ Codex exit code: {result.returncode}", flush=True)
    return result.returncode == 0


def main() -> None:
    temp_dir = tempfile.mkdtemp()
    try:
        print("📥 Cloning repo...", flush=True)
        token_url = f"https://{GITHUB_TOKEN}@github.com/{REPO_NAME}.git"
        base_branch = BRANCH
        try:
            subprocess.run(
                ["git", "clone", "--branch", base_branch, token_url, temp_dir],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"❌ Clone failed: {e.stderr.strip()}", flush=True)
            print("🔄 Retrying without branch specification...", flush=True)
            subprocess.run(["git", "clone", token_url, temp_dir], check=True)
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            base_branch = result.stdout.strip()

        subprocess.run(["git", "remote", "set-url", "origin", token_url], cwd=temp_dir, check=True)

        codex_path = find_codex_cli()
        run_codex(codex_path, PROMPT, temp_dir)

        print("🔍 Checking for changes...", flush=True)
        subprocess.run(["git", "config", "user.email", "codex@harmoniaai.com"], cwd=temp_dir)
        subprocess.run(["git", "config", "user.name", "Codex Agent"], cwd=temp_dir)
        subprocess.run(["git", "add", "-A"], cwd=temp_dir)

        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=temp_dir)
        if diff.returncode == 0:
            print("⚠️ No changes to commit.", flush=True)
            return

        branch = f"codex-todo-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        subprocess.run(["git", "checkout", "-b", branch], cwd=temp_dir, check=True)
        subprocess.run(["git", "commit", "-m", f"feat: codex changes for '{PROMPT}'"], cwd=temp_dir, check=True)

        print("🚀 Pushing changes...", flush=True)
        push = subprocess.run([
            "git",
            "push",
            "--set-upstream",
            "origin",
            branch,
        ], cwd=temp_dir, capture_output=True, text=True)

        if push.returncode != 0:
            print(f"❌ Push failed: {push.stderr}", flush=True)
            return

        print("✅ Pushed successfully!", flush=True)
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        pr = repo.create_pull(
            title=f"🤖 Codex: {TITLE}",
            body=f"Prompt: {PROMPT}\n\nAutomated PR created by Codex.",
            head=branch,
            base=base_branch,
        )
        print(f"✅ PR created: {pr.html_url}", flush=True)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

