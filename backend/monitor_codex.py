#!/usr/bin/env python3
"""
Monitor Codex output in real-time via WebSocket
Run this in a separate terminal to see live output
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime

async def monitor_terminal():
    """Connect to the terminal WebSocket and display output"""
    uri = "ws://localhost:8000/ws/terminal"
    
    print("🔍 Connecting to Codex Terminal Monitor...")
    print("=" * 60)
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected! Monitoring Codex output...")
            print("=" * 60)
            
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data['type'] == 'connected':
                        print(f"🔗 Session: {data['session_id']}")
                        
                    elif data['type'] == 'output':
                        # Print output directly without extra formatting
                        print(data['data'], end='', flush=True)
                        
                    elif data['type'] == 'status':
                        if data['data'] in ['completed', 'stopped']:
                            print(f"\n🏁 Status: {data['data']}")
                            
                    elif data['type'] == 'error':
                        print(f"\n❌ Error: {data.get('message', data.get('data', 'Unknown error'))}")
                        
                except websockets.exceptions.ConnectionClosed:
                    print("\n🔌 Connection closed")
                    break
                except json.JSONDecodeError:
                    print("\n⚠️ Received invalid JSON")
                except KeyboardInterrupt:
                    print("\n👋 Monitor stopped by user")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Could not connect to WebSocket server")
        print("💡 Make sure your main.py server is running on port 8000")
    except Exception as e:
        print(f"❌ Monitor error: {str(e)}")

def main():
    """Main function"""
    print("🚀 Codex Terminal Monitor")
    print("This will show real-time output from Codex sessions")
    print("Press Ctrl+C to stop monitoring")
    print("")
    
    try:
        asyncio.run(monitor_terminal())
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")

if __name__ == "__main__":
    main()