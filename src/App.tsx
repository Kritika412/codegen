import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import './App.css';
import { apiClient } from './api/client';
import type { ApiIssue, ApiSprint } from './api/client';

// Define all data inline (remove types dependency)
const mockSprints = [
  {
    id: 'sprint1',
    name: 'Sprint 34: June 14 – June 17',
    dateRange: 'June 14 – June 17',
    daysRemaining: 1,
    goals: 'Improve issue tracking automation',
  },
  {
    id: 'sprint2',
    name: 'Sprint 33: June 10 – June 13',
    dateRange: 'June 10 – June 13',
    daysRemaining: 0,
    goals: 'Complete dashboard implementation',
  },
  {
    id: 'sprint3',
    name: 'Sprint 32: June 6 – June 9',
    dateRange: 'June 6 – June 9',
    daysRemaining: 0,
    goals: 'Refactor core modules',
  },
];

const mockIssues = [
  {
    id: 345,
    title: 'Add auth middleware',
    assignee: 'Alice',
    status: 'in-progress',
    body: 'Implement authentication middleware for API routes.',
  },
  {
    id: 346,
    title: 'Fix broken PR status badge',
    assignee: 'Bob',
    status: 'blocked',
    body: 'The PR status badge is not updating correctly on the dashboard.',
  },
];

const mockAgentTasks = [
  {
    id: 'task1',
    agent: 'claude',
    description: 'Generate integration tests',
    status: 'running',
  },
  {
    id: 'task2',
    agent: 'codex',
    description: 'refactoring: utils module',
    status: 'done',
  },
];

const mockPullRequests = [
  {
    id: 123,
    title: 'Add dashboard view',
    author: 'Carol',
    branch: 'feature/dashboard',
    status: 'ci-passed',
  },
  {
    id: 124,
    title: 'Update agent task handler',
    author: 'Dave',
    branch: 'refactor/agent-tasks',
    status: 'needs-review',
  },
];

const mockStats = {
  total: 18,
  completed: 7,
  inProgress: 6,
  blocked: 2,
};

// Interfaces for Sprint Summary
interface SprintSummary {
  current_sprint: string;
  start_date: string;
  end_date: string;
  days_remaining: number;
  sprint_goals: string;
  total_issues: number;
  backlog: number;
  ready: number;
  in_progress: number;
  in_review: number;
}

function App() {
  // FIXED: State declarations with proper separation
  const [selectedSprint, setSelectedSprint] = useState('sprint1');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [issueDescription, setIssueDescription] = useState('');
  const [originalIssueDescription, setOriginalIssueDescription] = useState(''); // NEW: Track original
  const [selectedLLM, setSelectedLLM] = useState('codex');
  
  // API state
  const [sprints, setSprints] = useState<ApiSprint[]>([]);
  const [issues, setIssues] = useState<ApiIssue[]>([]);
  const [readyIssues, setReadyIssues] = useState<ApiIssue[]>([]); // NEW: Only Ready issues for Codex
  const [sprintSummary, setSprintSummary] = useState<SprintSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Issue editing states
  const [isUpdatingIssue, setIsUpdatingIssue] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState<string | null>(null);
  
  // Mock data fallback
  const [useMockData, setUseMockData] = useState(false);
  
  const fetchIssues = async (sprintName?: string) => {
    // Don't fetch issues if no sprint name is provided
    if (!sprintName) {
      console.log('No sprint name provided, skipping issue fetch');
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const issueData = await apiClient.getIssues(sprintName);
      setIssues(issueData);
    } catch (error) {
      console.warn('Failed to fetch issues:', error);
      setError('Failed to fetch issues from GitHub. Using mock data.');
      setUseMockData(true);
    } finally {
      setLoading(false);
    }
  };

  // NEW: Fetch only Ready issues for Codex functionality
  const fetchReadyIssues = async (sprintName: string) => {
    try {
      const readyIssueData = await apiClient.getReadyIssues(sprintName);
      setReadyIssues(readyIssueData);
      console.log(`Fetched ${readyIssueData.length} ready issues for Codex`);
    } catch (error) {
      console.warn('Failed to fetch ready issues:', error);
      setReadyIssues([]);
    }
  };

  // Fetch sprint summary
  const fetchSprintSummary = async (sprintName: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/sprints/summary?sprint_name=${encodeURIComponent(sprintName)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const summary = await response.json();
      setSprintSummary(summary);
    } catch (error) {
      console.error('Error fetching sprint summary:', error);
      setSprintSummary(null);
    }
  };

  // Function to fetch sprint list
  const fetchSprints = async () => {
    setLoading(true);
    setError(null);
    try {
      const sprintData = await apiClient.getSprints();
      setSprints(sprintData);
      setUseMockData(false);
    } catch (error) {
      console.warn('Failed to fetch sprints:', error);
      setError('Failed to fetch sprints from GitHub. Using mock data.');
      setUseMockData(true);
      setSprints([]); // fallback to mockSprints in displaySprints
    } finally {
      setLoading(false);
    }
  };

  // Initialize data when component mounts
  useEffect(() => {
    const initializeData = async () => {
      await fetchSprints();
      // Don't fetch issues immediately - wait for sprint selection
    };
    initializeData();
  }, []);

  // Fetch issues for the period when sprint changes
  useEffect(() => {
    if (!useMockData && selectedSprint && sprints.length > 0) {
      const currentSprint = sprints.find(s => s.id === selectedSprint);
      if (currentSprint) {
        // Use original_name for API calls (without dates)
        fetchIssues(currentSprint.original_name);
        fetchReadyIssues(currentSprint.original_name); // NEW: Also fetch Ready issues
        fetchSprintSummary(currentSprint.original_name);
      }
    }
  }, [selectedSprint, sprints, useMockData]);

  // Make sure we have a selected sprint when sprints are loaded
  useEffect(() => {
    if (sprints.length > 0 && !selectedSprint) {
      // Find the current sprint first, otherwise use the first one
      const currentSprint = sprints.find(s => s.is_current);
      const defaultSprint = currentSprint || sprints[0];
      setSelectedSprint(defaultSprint.id);
    }
  }, [sprints, selectedSprint]);
  
  // Helper function to format dates
  const formatDate = (dateString: string): string => {
    if (!dateString) return '';
    try {
      // Handle date strings properly by treating them as local dates
      let date;
      if (dateString.includes('T')) {
        // If it has time component, remove it and treat as local date
        const dateOnly = dateString.split('T')[0];
        const [year, month, day] = dateOnly.split('-').map(Number);
        date = new Date(year, month - 1, day); // month is 0-indexed
      } else {
        // If it's just a date, parse it as local date
        const [year, month, day] = dateString.split('-').map(Number);
        date = new Date(year, month - 1, day); // month is 0-indexed
      }
      
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric'
      });
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateString;
    }
  };
  
  // Select data to display currently
  const displaySprints = useMockData ? mockSprints : sprints.length > 0 ? sprints.map(s => ({
    id: s.id,
    name: s.name,
    dateRange: s.start_date && s.end_date ? `${formatDate(s.start_date)} – ${formatDate(s.end_date)}` : s.name,
    daysRemaining: s.end_date ? Math.max(0, Math.ceil((new Date(s.end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))) : 0,
    goals: 'Sprint goals from API'
  })) : mockSprints;
  
  const displayIssues = useMockData
    ? []
    : issues.length > 0
      ? issues.map(issue => ({
          id: `${issue.repo}#${issue.number}`, // composite id
          title: issue.title,
          assignee: issue.assignee || 'Unassigned',
          status: issue.status,
          body: issue.body || '',
          repo: issue.repo,
          number: issue.number,
          url: issue.url, // keep number for display
        }))
      : [];

  // NEW: Ready issues for Codex section (only Ready status)
  const displayReadyIssues = useMockData
    ? []
    : readyIssues.length > 0
      ? readyIssues.map(issue => ({
          id: `${issue.repo}#${issue.number}`, // composite id
          title: issue.title,
          assignee: issue.assignee || 'Unassigned',
          status: issue.status,
          body: issue.body || '',
          repo: issue.repo,
          number: issue.number,
          url: issue.url,
        }))
      : [];

  const currentSprint = displaySprints.find(sprint => sprint.id === selectedSprint) || displaySprints[0];

  const handleSprintChange = (sprintId: string) => {
    setSelectedSprint(sprintId);
  };

  const handleAsk = () => {
    console.log('Asking for help with issue:', selectedIssue);
  };

  const handleCode = async () => {
    const issue = displayReadyIssues.find(issue => issue.id === selectedIssue); // CHANGED: Use Ready issues
    const prompt = issueDescription || "Add backend logic";
    const repo = issue?.repo;

    const response = await fetch("http://localhost:8000/api/run-codex", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, repo }),
    });
    if (response.ok) {
      alert("✅ Codex is running. Check your terminal.");
    } else {
      alert("❌ Failed to trigger Codex.");
    }
  };
  
  // FIXED: Handle issue selection changes properly (now uses Ready issues)
  const handleIssueSelectionChange = (issueId: string) => {
    setSelectedIssue(issueId);
    const issue = displayReadyIssues.find(issue => issue.id === issueId); // CHANGED: Use Ready issues
    if (issue) {
      const description = issue.body || '';
      setIssueDescription(description);
      setOriginalIssueDescription(description);
    } else {
      setIssueDescription('');
      setOriginalIssueDescription('');
    }
  };

  // FIXED: Handle saving issue description changes
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedIssue || !issueDescription.trim()) {
      alert('Please select an issue and provide a description.');
      return;
    }

    const issue = displayReadyIssues.find(issue => issue.id === selectedIssue); // CHANGED: Use Ready issues
    if (!issue) {
      alert('Selected issue not found.');
      return;
    }

    setIsUpdatingIssue(true);
    setError(null);
    setUpdateSuccess(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/issues/${issue.number}?repo_name=${encodeURIComponent(issue.repo)}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            body: issueDescription.trim()
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      console.log('Issue updated:', result);

      // Update local state
      setIssues(prevIssues =>
        prevIssues.map(i =>
          i.number === issue.number
            ? { ...i, body: issueDescription.trim() }
            : i
        )
      );

      // Update the original description to the new saved value
      setOriginalIssueDescription(issueDescription.trim());

      setUpdateSuccess('Issue description updated successfully!');
      
      // Clear success message after 3 seconds
      setTimeout(() => setUpdateSuccess(null), 3000);
      
    } catch (error) {
      console.error('Error updating issue:', error);
      setError(`Failed to update issue: ${error}`);
    } finally {
      setIsUpdatingIssue(false);
    }
  };

  // FIXED: Better useEffect for issue description handling (now uses Ready issues)
  useEffect(() => {
    if (displayReadyIssues.length > 0) {
      // Only update if we don't have a selected issue or if the current selection is not in the new list
      const found = displayReadyIssues.find(issue => issue.id.toString() === selectedIssue);
      if (!selectedIssue || !found) {
        const firstIssue = displayReadyIssues[0];
        setSelectedIssue(firstIssue.id.toString());
        const description = firstIssue.body || '';
        setIssueDescription(description);
        setOriginalIssueDescription(description);
      } else if (found) {
        // Only update if the issue body has changed from an external source
        // and we haven't made local changes
        const currentDescription = found.body || '';
        if (currentDescription !== originalIssueDescription && 
            issueDescription === originalIssueDescription) {
          setIssueDescription(currentDescription);
          setOriginalIssueDescription(currentDescription);
        }
      }
    } else {
      setIssueDescription('');
      setOriginalIssueDescription('');
    }
  }, [displayReadyIssues]); // CHANGED: Use displayReadyIssues instead of displayIssues

  return (
    <div className="bg-gray-100 text-gray-900 min-h-screen">
      <Header />
      
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        {/* Success Message */}
        {updateSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="text-sm text-green-700">
              <strong>✅ {updateSuccess}</strong>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <div className="text-sm text-yellow-700">
              <strong>⚠️ {error}</strong>
            </div>
          </div>
        )}
        
        {/* Loading indicator */}
        {loading && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <div className="text-sm text-blue-700">
              🔄 Loading issues...
            </div>
          </div>
        )}

        {/* Sprint Picker */}
        <section className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-2">Select Current Sprint</h2>
          <form className="space-y-4">
            <div>
              <label htmlFor="sprint-select" className="block text-sm font-medium text-gray-700">
                GitHub Sprint (Milestone)
              </label>
              <select
                id="sprint-select"
                value={selectedSprint}
                onChange={(e) => handleSprintChange(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                {displaySprints.map((sprint) => (
                  <option key={sprint.id} value={sprint.id}>
                    {sprint.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
            >
              Load Sprint
            </button>
          </form>
        </section>

        {/* Issue Helper */}
        <section className="bg-indigo-50 p-6 rounded-xl shadow border border-indigo-200">
          <h2 className="text-xl font-semibold mb-2">Ask Codex or Claude for Help</h2>
          <form className="space-y-4" onSubmit={handleSave}>
            {/* FIXED: Issue selection dropdown */}
            <div>
              <label htmlFor="issue-select" className="block text-sm font-medium text-gray-700">
                Select Issue
              </label>
              <select
                id="issue-select"
                value={selectedIssue}
                onChange={(e) => handleIssueSelectionChange(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                disabled={displayReadyIssues.length === 0}
              >
                {displayReadyIssues.length === 0 ? (
                  <option value="">No Ready issues available for Codex assistance</option>
                ) : (
                  displayReadyIssues.map((issue) => (
                    <option key={issue.id} value={issue.id}>
                      [{issue.repo}] [#{issue.number}] {issue.title} (Ready)
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* FIXED: Issue description textarea with change indicator */}
            <div>
              <label htmlFor="issue-description" className="block text-sm font-medium text-gray-700">
                Edit Issue Description
              </label>
              <textarea
                id="issue-description"
                rows={4}
                value={issueDescription}
                onChange={(e) => setIssueDescription(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Update or refine the issue details..."
                disabled={isUpdatingIssue}
              />
              {/* Show if there are unsaved changes */}
              {issueDescription !== originalIssueDescription && (
                <p className="text-xs text-orange-600 mt-1">
                  * You have unsaved changes
                </p>
              )}
            </div>

            <div>
              <label htmlFor="llm-select" className="block text-sm font-medium text-gray-700">
                Choose Code Generator
              </label>
              <select
                id="llm-select"
                value={selectedLLM}
                onChange={(e) => setSelectedLLM(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="codex">Codex</option>
                <option value="claude" disabled>Claude (disabled)</option>
              </select>
            </div>

            <div className="flex space-x-4">
              <button
                type="button"
                onClick={handleAsk}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 opacity-50 cursor-not-allowed"
                disabled
              >
                Ask
              </button>
              <button
                type="button"
                onClick={handleCode}
                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                disabled={isUpdatingIssue}
              >
                Code
              </button>
              {/* FIXED: Save button now works properly */}
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                disabled={isUpdatingIssue || !issueDescription.trim()}
              >
                {isUpdatingIssue ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </section>

        {/* Sprint Info */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h2 className="text-2xl font-bold mb-2">
            Current Sprint: {sprintSummary && sprintSummary.start_date && sprintSummary.end_date ? 
              `${formatDate(sprintSummary.start_date)} - ${formatDate(sprintSummary.end_date)}` : 
              currentSprint.dateRange
            }
          </h2>
          <p className="text-gray-600">
            Days Remaining: <strong>{sprintSummary ? sprintSummary.days_remaining : currentSprint.daysRemaining}</strong>
          </p>
          <p className="text-gray-600">
            Sprint Goals: {sprintSummary ? sprintSummary.sprint_goals : currentSprint.goals}
          </p>
        </section>

        {/* Sprint Status Summary */}
        <section className="bg-white p-6 rounded-xl shadow grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold">{sprintSummary ? sprintSummary.total_issues : mockStats.total}</div>
            <div className="text-sm text-gray-500">Total Issues</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-600">{sprintSummary ? sprintSummary.backlog : 0}</div>
            <div className="text-sm text-gray-500">Backlog</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{sprintSummary ? sprintSummary.ready : 0}</div>
            <div className="text-sm text-gray-500">Ready</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-500">{sprintSummary ? sprintSummary.in_progress : mockStats.inProgress}</div>
            <div className="text-sm text-gray-500">In Progress</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{sprintSummary ? sprintSummary.in_review : 0}</div>
            <div className="text-sm text-gray-500">In Review</div>
          </div>
        </section>

        {/* Issues List */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Sprint Issues</h3>
          <div className="space-y-4">
            {displayIssues.length === 0 ? (
              <div className="text-gray-400 text-center">No issues for this sprint.</div>
            ) : (
              displayIssues.map((issue) => (
                <div key={issue.id} className="border p-4 rounded-md flex justify-between items-center bg-gray-50">
                  <div>
                    <p className="font-medium">[{issue.repo}] [#{issue.number}] {issue.title}</p>
                    <p className="text-sm text-gray-500">
                      Assigned to: {issue.assignee ?? 'Unassigned'}
                    </p>
                  </div>
                  {/* Fixed: Use the actual GitHub URL from the API */}
                  {issue.url ? (
                    <a 
                      href={issue.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      View on GitHub
                    </a>
                  ) : (
                    <span className="text-gray-400">No GitHub link</span>
                  )}
                </div>
              ))
            )}
          </div>
        </section>

        {/* Active Agent Tasks */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Running Tasks (Agents)</h3>
          <div className="text-gray-400 text-center py-8">
            🚧 This feature is under development.
          </div>
        </section>

        {/* PR Feed */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Pull Requests</h3>
          <div className="text-gray-400 text-center py-8">
            🚧 This feature is under development.
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;