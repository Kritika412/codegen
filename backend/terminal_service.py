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
        
    async def start_codex(self, prompt: str, repo: str, title: str, auto_mode: str = "interactive"):
        """Start the REAL Codex CLI process using PTY for proper terminal support"""
        try:
            # Use the correct repository from the issue
            actual_repo = repo if repo and repo != "Unknown" else "hail007/Agent-Testing"
            
            # Log what we're using
            await self.send_message("output", f"🚀 Starting REAL Codex CLI with PTY Support\n")
            await self.send_message("output", f"📝 Prompt: {prompt}\n")
            await self.send_message("output", f"📦 Repository: {actual_repo}\n")
            await self.send_message("output", f"🏷️ Title: {title}\n")
            await self.send_message("output", f"🎮 Mode: {auto_mode}\n")
            await self.send_message("output", "-" * 50 + "\n")
            
            # Use the PTY-enabled Codex script
            codex_script = "run_codex_pty.py"  # Our PTY-enabled Codex script
            
            if not os.path.exists(codex_script):
                await self.send_message("error", f"❌ PTY Codex script not found: {codex_script}\n")
                await self.send_message("output", f"💡 Please create {codex_script} with PTY support\n")
                await self.send_message("output", f"📦 Install pexpect: pip install pexpect\n")
                return
            
            await self.send_message("output", f"📄 Using PTY Codex script: {codex_script}\n")
            
            # Prepare the command using your script's argument format
            cmd = [
                "python", 
                codex_script,
                prompt,          # sys.argv[1] - PROMPT
                actual_repo,     # sys.argv[2] - REPO_NAME  
                title            # sys.argv[3] - TITLE
            ]
            
            # Add auto mode flag if in auto mode
            if auto_mode == "auto":
                cmd.append("auto")  # sys.argv[4] - auto flag
            
            await self.send_message("output", f"🔧 Command: {' '.join(cmd)}\n")
            await self.send_message("output", f"🎯 This will use PTY to properly handle Codex CLI's raw mode\n\n")
            
            # Start the process with proper environment
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                env={
                    **os.environ, 
                    "PYTHONUNBUFFERED": "1",
                    "FORCE_COLOR": "1"
                }
            )
            
            # Start output reader
            self.output_task = asyncio.create_task(self.read_output())
            
        except Exception as e:
            await self.send_message("error", f"Failed to start PTY Codex: {str(e)}")
            logger.error(f"Failed to start PTY Codex: {str(e)}")
    
    async def read_output(self):
        """Read output from the process with real-time streaming"""
        try:
            while self.is_active and self.process and self.process.poll() is None:
                if self.process.stdout:
                    # Read line by line for Codex output
                    line = self.process.stdout.readline()
                    if line:
                        # Store log
                        self.logs.append({
                            'timestamp': datetime.now().isoformat(),
                            'content': line
                        })
                        # Send to websocket immediately
                        await self.send_message("output", line)
                        
                        # Also print to actual terminal for debugging
                        print(line, end='', flush=True)
                    else:
                        # No output available, wait a bit
                        await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0.1)
            
            # Process has ended
            if self.process:
                return_code = self.process.poll()
                if return_code is not None:
                    completion_msg = f"\n✅ Codex completed with exit code: {return_code}\n" if return_code == 0 else f"\n⚠️ Codex exited with code: {return_code}\n"
                    await self.send_message("output", completion_msg)
                    print(completion_msg, flush=True)  # Also print to actual terminal
                    await self.send_message("status", "completed")
        except Exception as e:
            error_msg = f"Error reading output: {str(e)}"
            logger.error(error_msg)
            await self.send_message("error", error_msg)
            print(f"❌ {error_msg}", flush=True)
    
    async def send_input(self, data: str):
        """Send input to the process - handles Codex CLI input prompts"""
        try:
            if self.process and self.process.stdin and not self.process.stdin.closed:
                # Handle special keys
                if data == '\r':  # Enter key
                    self.process.stdin.write('\n')
                    self.process.stdin.flush()
                    # Echo newline to terminal
                    await self.send_message("output", '\n')
                elif data == '\u007f':  # Backspace
                    # Don't send backspace to process, just echo to terminal
                    await self.send_message("output", '\b \b')
                else:
                    # Send regular characters
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
                    # Echo to terminal (so user sees what they're typing)
                    await self.send_message("output", data)
            else:
                await self.send_message("error", "Cannot send input - process not ready or stdin closed")
        except Exception as e:
            await self.send_message("error", f"Failed to send input: {str(e)}")
            logger.error(f"Input error: {str(e)}")
    
    async def send_message(self, msg_type: str, data: str):
        """Send message to websocket with error handling"""
        try:
            if self.websocket and hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json({
                    "type": msg_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            # Don't raise exception, just log it
    
    async def stop(self):
        """Stop the session"""
        self.is_active = False
        if self.process:
            try:
                # Send interrupt signal first
                self.process.terminate()
                await asyncio.sleep(2)
                
                # Force kill if still running
                if self.process.poll() is None:
                    self.process.kill()
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error stopping process: {str(e)}")
        
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