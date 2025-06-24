"""
Codex service for handling AI-powered code generation and repository management.

This service manages the integration with Codex CLI for automated code generation,
Git operations, and pull request creation.
"""

import subprocess
import tempfile
import os
import shutil
from datetime import datetime
from typing import Dict, Optional
from github import Github

from app.core.config import Config, logger
from app.core.exceptions import CodexExecutionError, GitHubAPIError
from app.utils.helpers import parse_github_repo_url


class CodexService:
    """
    Service class for Codex CLI operations.
    
    Handles code generation, Git operations, and pull request management
    through the Codex CLI tool.
    """
    
    def __init__(self):
        """Initialize Codex service with required API keys and configuration."""
        if not Config.OPENAI_API_KEY:
            raise CodexExecutionError("OpenAI API key not configured")
        if not Config.GITHUB_TOKEN:
            raise CodexExecutionError("GitHub token not configured")
            
        self.openai_api_key = Config.OPENAI_API_KEY
        self.github_token = Config.GITHUB_TOKEN
        self.github_client = Github(self.github_token)
        
        # Set environment variable for Codex CLI
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
    
    def run_codex_workflow(self, prompt: str, repo_name: str, 
                          branch: str = "main", auto_push: bool = False) -> Dict[str, str]:
        """
        Execute the complete Codex workflow: clone, generate, commit, and optionally push.
        
        Args:
            prompt: The prompt for code generation
            repo_name: Repository name in format "owner/repo"
            branch: Source branch to work from
            auto_push: Whether to automatically push and create PR
            
        Returns:
            Dictionary with operation results
            
        Raises:
            CodexExecutionError: If any step in the workflow fails
        """
        temp_dir = None
        try:
            # Parse repository information
            repo_info = parse_github_repo_url(repo_name)
            if not repo_info['owner'] or not repo_info['repo']:
                raise CodexExecutionError(f"Invalid repository format: {repo_name}")
            
            repo_url = f"https://github.com/{repo_name}.git"
            logger.info(f"Starting Codex workflow for prompt: '{prompt}' on repo: {repo_name}")
            
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Clone repository
            self._clone_repository(repo_url, branch, temp_dir)
            
            # Setup Git authentication
            self._setup_git_auth(repo_name, temp_dir)
            
            # Run Codex CLI
            self._run_codex_cli(prompt, temp_dir)
            
            # Create and commit changes
            timestamp_branch = f"codex-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            has_changes = self._commit_changes(prompt, timestamp_branch, temp_dir)
            
            if not has_changes:
                logger.info("No changes were made by Codex")
                return {
                    "status": "no_changes",
                    "message": "No changes were made by Codex",
                    "branch_name": None,
                    "pr_url": None
                }
            
            result = {
                "status": "committed",
                "message": f"Codex changes committed to branch '{timestamp_branch}'",
                "branch_name": timestamp_branch,
                "pr_url": None
            }
            
            # Push and create PR if requested
            if auto_push:
                pr_url = self._push_and_create_pr(prompt, repo_name, timestamp_branch, branch, temp_dir)
                result.update({
                    "status": "pushed",
                    "message": f"Codex changes pushed and PR created",
                    "pr_url": pr_url
                })
            
            logger.info(f"Codex workflow completed successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Codex workflow failed: {str(e)}")
            raise CodexExecutionError(f"Codex workflow failed: {str(e)}")
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
    
    def _clone_repository(self, repo_url: str, branch: str, temp_dir: str) -> None:
        """Clone the repository to temporary directory."""
        try:
            logger.info(f"Cloning repository {repo_url} (branch: {branch})")
            subprocess.run(
                ["git", "clone", "--branch", branch, repo_url, temp_dir],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Repository cloned successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise CodexExecutionError(f"Failed to clone repository: {e.stderr}")
    
    def _setup_git_auth(self, repo_name: str, temp_dir: str) -> None:
        """Setup Git authentication with token."""
        try:
            token_remote_url = f"https://{self.github_token}@github.com/{repo_name}.git"
            subprocess.run(
                ["git", "remote", "set-url", "origin", token_remote_url],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Git authentication configured")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git auth setup failed: {e.stderr}")
            raise CodexExecutionError(f"Failed to setup Git authentication: {e.stderr}")
    
    def _run_codex_cli(self, prompt: str, temp_dir: str) -> None:
        """Run Codex CLI with the given prompt."""
        try:
            logger.info(f"Running Codex CLI with prompt: {prompt}")
            subprocess.run(
                ["codex", "--approval-mode", "full-auto", prompt],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Codex CLI executed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Codex CLI failed: {e.stderr}")
            raise CodexExecutionError(f"Codex CLI execution failed: {e.stderr}")
        except FileNotFoundError:
            raise CodexExecutionError("Codex CLI not found. Please ensure it's installed and in PATH.")
    
    def _commit_changes(self, prompt: str, branch_name: str, temp_dir: str) -> bool:
        """Create a new branch and commit changes."""
        try:
            # Create new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Created branch: {branch_name}")
            
            # Stage all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Check if there are staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=temp_dir,
                capture_output=True
            )
            
            if result.returncode == 0:
                # No changes to commit
                logger.info("No changes detected to commit")
                return False
            
            # Commit changes
            commit_message = f"feat: codex changes for '{prompt}'"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Changes committed with message: {commit_message}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git commit failed: {e.stderr}")
            raise CodexExecutionError(f"Failed to commit changes: {e.stderr}")
    
    def _push_and_create_pr(self, prompt: str, repo_name: str, branch_name: str, 
                           base_branch: str, temp_dir: str) -> str:
        """Push branch and create pull request."""
        try:
            # Push branch
            subprocess.run(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_dir,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Branch {branch_name} pushed successfully")
            
            # Create pull request
            repo = self.github_client.get_repo(repo_name)
            pr = repo.create_pull(
                title=f"Codex PR: {prompt}",
                body=f"Automated code generation based on prompt: '{prompt}'\n\nGenerated by Harmonia Codex service.",
                head=branch_name,
                base=base_branch
            )
            
            logger.info(f"Pull request created: {pr.html_url}")
            return pr.html_url
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git push failed: {e.stderr}")
            raise CodexExecutionError(f"Failed to push branch: {e.stderr}")
        except Exception as e:
            logger.error(f"PR creation failed: {str(e)}")
            raise GitHubAPIError(f"Failed to create pull request: {str(e)}")
    
    def validate_codex_availability(self) -> bool:
        """
        Check if Codex CLI is available and properly configured.
        
        Returns:
            True if Codex CLI is available
        """
        try:
            subprocess.run(
                ["codex", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_codex_status(self) -> Dict[str, bool]:
        """
        Get status of Codex dependencies and configuration.
        
        Returns:
            Dictionary with status information
        """
        return {
            "codex_cli_available": self.validate_codex_availability(),
            "openai_api_key_configured": bool(Config.OPENAI_API_KEY),
            "github_token_configured": bool(Config.GITHUB_TOKEN)
        }
