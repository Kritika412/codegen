import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface CodexTerminalProps {
  issueId?: string;
  issueTitle?: string;
  issueDescription?: string;
  repo?: string;
}

const CodexTerminal: React.FC<CodexTerminalProps> = ({ 
  issueId, 
  issueTitle = 'Issue',
  issueDescription = '',
  repo = 'hail007/Agent-Testing'
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [terminal, setTerminal] = useState<Terminal | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [prompt, setPrompt] = useState(issueDescription);
  const [autoMode, setAutoMode] = useState(false);
  const fitAddonRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize terminal with proper theme
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1a1a1a',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        selectionBackground: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      convertEol: true,
    });

    const fitAddon = new FitAddon();
    fitAddonRef.current = fitAddon;
    
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    // Connect WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/terminal');
    
    ws.onopen = () => {
      console.log('Terminal WebSocket connected');
      setIsConnected(true);
      term.writeln('🚀 Harmonia Codex Terminal');
      term.writeln('================================');
      term.writeln('Ready to run Codex tasks');
      term.writeln('');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connected':
          setSessionId(data.session_id);
          term.writeln(`📡 Session ID: ${data.session_id}`);
          term.writeln('');
          break;
        
        case 'output':
          // Write output to terminal
          term.write(data.data);
          break;
        
        case 'status':
          if (data.data === 'completed' || data.data === 'stopped') {
            setIsRunning(false);
            term.writeln('\n✅ Task completed');
          }
          break;
        
        case 'error':
          term.writeln(`\n❌ Error: ${data.message || data.data}`);
          setIsRunning(false);
          break;
        
        default:
          console.log('Unknown message type:', data.type);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      term.writeln('\n❌ Connection error');
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      term.writeln('\n📡 Connection closed');
      setIsConnected(false);
      setIsRunning(false);
    };

    // Handle terminal input
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN && isRunning) {
        // Send input to backend
        ws.send(JSON.stringify({
          type: 'input',
          data: data
        }));
      }
    });

    setTerminal(term);
    setSocket(ws);

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      ws.close();
      term.dispose();
    };
  }, []);

  // Update prompt when issueDescription changes
  useEffect(() => {
    setPrompt(issueDescription);
  }, [issueDescription]);

  const startCodex = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      alert('Terminal not connected. Please refresh the page.');
      return;
    }

    if (!prompt.trim()) {
      alert('Please enter a prompt for Codex');
      return;
    }

    // Clear terminal
    if (terminal) {
      terminal.clear();
      terminal.writeln('🚀 Starting Codex...\n');
    }

    // Use the repo passed from props (selected in the UI)
    const actualRepo = repo && repo !== 'Unknown' && repo !== 'Draft Issue' 
      ? repo 
      : 'hail007/Agent-Testing';  // fallback

    // Send command to start Codex
    setIsRunning(true);
    socket.send(JSON.stringify({
      type: 'start_codex',
      prompt: prompt,
      repo: actualRepo,
      title: issueTitle || 'Codex Task',
      auto_mode: autoMode ? 'auto' : 'interactive'
    }));
  };

  const stopCodex = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'stop'
      }));
      setIsRunning(false);
    }
  };

  const clearTerminal = () => {
    if (terminal) {
      terminal.clear();
      terminal.writeln('🚀 Terminal cleared\n');
    }
  };

  const downloadLogs = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: 'get_logs'
      }));
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 mb-6">
      <div className="mb-4">
        <h3 className="text-white text-lg font-semibold mb-2">Codex Terminal</h3>
        
        {/* Repository Info Display */}
        <div className="mb-3 p-2 bg-gray-800 rounded border border-gray-700">
          <div className="text-sm text-gray-300">
            <span className="font-medium">Target Repository:</span> 
            <span className="text-blue-400 ml-2">{repo}</span>
          </div>
        </div>
        
        {/* Prompt Input */}
        <div className="mb-3">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Codex Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full px-3 py-2 bg-gray-800 text-white border border-gray-700 rounded-md focus:outline-none focus:border-blue-500"
            rows={3}
            placeholder="Enter your prompt for Codex..."
            disabled={isRunning}
          />
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            <button
              onClick={startCodex}
              disabled={!isConnected || isRunning}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                !isConnected || isRunning
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {isRunning ? '⚡ Running...' : '▶️ Start Codex'}
            </button>
            
            <button
              onClick={stopCodex}
              disabled={!isRunning}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                !isRunning
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              ⏹️ Stop
            </button>
            
            <button
              onClick={clearTerminal}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
            >
              🧹 Clear
            </button>
          </div>

          <div className="flex items-center space-x-4">
            {/* Auto Mode Toggle */}
            <label className="flex items-center text-white">
              <input
                type="checkbox"
                checked={autoMode}
                onChange={(e) => setAutoMode(e.target.checked)}
                disabled={isRunning}
                className="mr-2"
              />
              Auto-push to GitHub
            </label>

            {/* Connection Status */}
            <div className="flex items-center">
              <div className={`w-2 h-2 rounded-full mr-2 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className={`text-sm ${
                isConnected ? 'text-green-400' : 'text-red-400'
              }`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal Container */}
      <div 
        ref={terminalRef} 
        className="bg-black rounded p-2"
        style={{ height: '400px' }}
      />

      {/* Session Info */}
      {sessionId && (
        <div className="mt-2 text-gray-400 text-xs">
          Session: {sessionId}
        </div>
      )}
    </div>
  );
};

export default CodexTerminal;