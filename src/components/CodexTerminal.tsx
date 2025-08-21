import React, { useEffect, useRef, useState, useCallback } from 'react';
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
  const [outputBuffer, setOutputBuffer] = useState(''); // Buffer for chunked output
  const fitAddonRef = useRef<FitAddon | null>(null);
  
  // Use refs to prevent stale closures
  const socketRef = useRef<WebSocket | null>(null);
  const terminalRef2 = useRef<Terminal | null>(null);
  const isConnectedRef = useRef(false);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (socketRef.current) {
      console.log('Closing existing WebSocket connection');
      socketRef.current.close();
      socketRef.current = null;
    }
    if (terminalRef2.current) {
      terminalRef2.current.dispose();
      terminalRef2.current = null;
    }
    setSocket(null);
    setTerminal(null);
    setIsConnected(false);
    isConnectedRef.current = false;
    setSessionId(null);
  }, []);

  // Initialize terminal and WebSocket
  const initialize = useCallback(() => {
    if (!terminalRef.current) return;

    console.log('Initializing terminal and WebSocket...');

    // Create terminal
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

    // Store terminal reference
    terminalRef2.current = term;
    setTerminal(term);

    // Create WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws/terminal');
    socketRef.current = ws;
    
    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      if (!isConnectedRef.current) { // Prevent duplicate messages
        isConnectedRef.current = true;
        setIsConnected(true);
        setSocket(ws);
        
        term.writeln('🚀 Harmonia Codex Terminal');
        term.writeln('================================');
        term.writeln('Ready to run REAL Codex Agent');
        term.writeln('💡 Toggle "Interactive Mode" for full Codex experience');
        term.writeln('');
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'connected':
            setSessionId(data.session_id);
            term.writeln(`🔗 Session ID: ${data.session_id}`);
            term.writeln('');
            break;
          
          case 'output':
            term.write(data.data);
            break;
          
          case 'status':
            if (data.data === 'completed' || data.data === 'stopped') {
              setIsRunning(false);
              term.writeln('\n✅ Codex task completed');
            }
            break;
          
          case 'error':
            term.writeln(`\n❌ Error: ${data.message || data.data}`);
            setIsRunning(false);
            break;
          
          default:
            console.log('Unknown message type:', data.type);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (isConnectedRef.current) {
        term.writeln('\n❌ Connection error');
        setIsConnected(false);
        isConnectedRef.current = false;
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      if (isConnectedRef.current) {
        term.writeln('\n🔌 Connection closed');
        setIsConnected(false);
        isConnectedRef.current = false;
        setIsRunning(false);
      }
    };

    // Handle terminal input
    term.onData((data) => {
      if (socketRef.current?.readyState === WebSocket.OPEN && isRunning) {
        socketRef.current.send(JSON.stringify({
          type: 'input',
          data: data
        }));
      }
    });

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cleanup();
    };
  }, [cleanup, isRunning]);

  // Effect with proper cleanup
  useEffect(() => {
    let mounted = true;
    
    // Delay initialization slightly to avoid React Strict Mode issues
    const timer = setTimeout(() => {
      if (mounted) {
        initialize();
      }
    }, 100);

    return () => {
      mounted = false;
      clearTimeout(timer);
      cleanup();
    };
  }, []); // Empty dependency array

  // Update prompt when issueDescription changes
  useEffect(() => {
    setPrompt(issueDescription);
  }, [issueDescription]);

  const startCodex = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      alert('Terminal not connected. Please refresh the page.');
      return;
    }

    if (!prompt.trim()) {
      alert('Please enter a prompt for Codex');
      return;
    }

    // Clear terminal
    if (terminalRef2.current) {
      terminalRef2.current.clear();
      terminalRef2.current.writeln('🚀 Starting REAL Codex Agent...\n');
      
      if (!autoMode) {
        terminalRef2.current.writeln('🎮 Interactive Mode: You can type responses when Codex asks questions');
        terminalRef2.current.writeln('💡 Tip: Follow Codex prompts and provide input as needed');
        terminalRef2.current.writeln('');
      } else {
        terminalRef2.current.writeln('🤖 Auto Mode: Codex will run automatically');
        terminalRef2.current.writeln('');
      }
    }

    // Use the repo passed from props
    const actualRepo = repo && repo !== 'Unknown' && repo !== 'Draft Issue' 
      ? repo 
      : 'hail007/Agent-Testing';

    // Send command to start REAL Codex
    setIsRunning(true);
    socketRef.current.send(JSON.stringify({
      type: 'start_codex',
      prompt: prompt,
      repo: actualRepo,
      title: issueTitle || 'Codex Task',
      auto_mode: autoMode ? 'auto' : 'interactive'
    }));
  };

  const stopCodex = () => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'stop'
      }));
      setIsRunning(false);
    }
  };

  const clearTerminal = () => {
    if (terminalRef2.current) {
      terminalRef2.current.clear();
      terminalRef2.current.writeln('🧹 Terminal cleared\n');
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4 mb-6">
      <div className="mb-4">
        <h3 className="text-white text-lg font-semibold mb-2">🤖 Real Codex Agent Terminal</h3>
        
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
            Codex Agent Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full px-3 py-2 bg-gray-800 text-white border border-gray-700 rounded-md focus:outline-none focus:border-blue-500"
            rows={3}
            placeholder="Describe what you want Codex to build..."
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
              {isRunning ? '⚡ Running Codex...' : '🤖 Start Real Codex'}
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
            {/* Mode Toggle */}
            <label className="flex items-center text-white">
              <input
                type="checkbox"
                checked={autoMode}
                onChange={(e) => setAutoMode(e.target.checked)}
                disabled={isRunning}
                className="mr-2"
              />
              {autoMode ? '🤖 Auto Mode' : '🎮 Interactive Mode'}
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

        {/* Mode Explanation */}
        <div className="mt-3 p-2 bg-blue-900 rounded border border-blue-700">
          <div className="text-xs text-blue-200">
            <strong>💡 Mode Guide:</strong>
            <br />
            <strong>🎮 Interactive Mode:</strong> Codex will ask questions and wait for your responses (recommended)
            <br />
            <strong>🤖 Auto Mode:</strong> Codex runs automatically with default responses
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
          Session: {sessionId} | Mode: {autoMode ? 'Auto' : 'Interactive'} | Status: {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      )}
    </div>
  );
};

export default CodexTerminal;