import asyncio
import json
import os
import subprocess
import uuid
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger("harmonia_api")

class TerminalSession:
    def __init__(self, session_id: str, websocket):
        self.session_id = session_id
        self.websocket = websocket
        self.process: Optional[subprocess.Popen] = None
        self.output_task: Optional[asyncio.Task] = None
        self.is_active = True
        self.logs = []
        
    async def start_codex(self, prompt: str, repo: str, title: str):
        """Start the codex process"""
        try:
            # Use the correct repository from the issue
            actual_repo = repo if repo and repo != "Unknown" else "hail007/Agent-Testing"
            
            # Log what we're using
            await self.send_message("output", f"🚀 Starting Codex with prompt: {prompt}\n")
            await self.send_message("output", f"📦 Repository: {actual_repo}\n")
            await self.send_message("output", f"📝 Title: {title}\n")
            await self.send_message("output", "-" * 50 + "\n")
            
            # Prepare the command - use our improved script
            cmd = [
                "python", 
                "run_codex_improved.py",  # Use the improved script
                prompt, 
                actual_repo, 
                title,
                "auto"  # Use auto mode to avoid TTY issues
            ]
            
            # Start the process without TTY
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            
            # Start output reader
            self.output_task = asyncio.create_task(self.read_output())
            
        except Exception as e:
            await self.send_message("error", f"Failed to start Codex: {str(e)}")
            logger.error(f"Failed to start Codex: {str(e)}")
    
    async def read_output(self):
        """Read output from the process"""
        try:
            while self.is_active and self.process and self.process.poll() is None:
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        # Store log
                        self.logs.append({
                            'timestamp': datetime.now().isoformat(),
                            'content': line
                        })
                        # Send to websocket
                        await self.send_message("output", line)
                await asyncio.sleep(0.01)
            
            # Process has ended
            if self.process:
                return_code = self.process.poll()
                if return_code is not None:
                    if return_code == 0:
                        await self.send_message("output", f"\n✅ Process completed successfully\n")
                    else:
                        await self.send_message("output", f"\n⚠️ Process exited with code: {return_code}\n")
                    await self.send_message("status", "completed")
        except Exception as e:
            logger.error(f"Error reading output: {str(e)}")
            await self.send_message("error", f"Error reading output: {str(e)}")
    
    async def send_input(self, data: str):
        """Send input to the process"""
        try:
            if self.process and self.process.stdin:
                self.process.stdin.write(data + '\n')
                self.process.stdin.flush()
                await self.send_message("output", f"> {data}\n")
        except Exception as e:
            await self.send_message("error", f"Failed to send input: {str(e)}")
    
    async def send_message(self, msg_type: str, data: str):
        """Send message to websocket"""
        try:
            if self.websocket:
                await self.websocket.send_json({
                    "type": msg_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
    
    async def stop(self):
        """Stop the session"""
        self.is_active = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        
        if self.output_task:
            self.output_task.cancel()
    
    def get_logs(self):
        """Get all logs from this session"""
        return self.logs

class TerminalManager:
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
    
    async def create_session(self, websocket) -> str:
        """Create a new terminal session"""
        session_id = str(uuid.uuid4())
        session = TerminalSession(session_id, websocket)
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    async def remove_session(self, session_id: str):
        """Remove and cleanup a session"""
        if session_id in self.sessions:
            await self.sessions[session_id].stop()
            del self.sessions[session_id]

# Global terminal manager instance
terminal_manager = TerminalManager()