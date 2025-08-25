import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CodexTerminal from './components/CodexTerminal';
import RepositorySelector from './components/RepositorySelector';
import ProjectSelector from './components/ProjectSelector';
import './App.css';
import { apiClient } from './api/client';
import type { ApiIssue, ApiSprint } from './api/client';

// Define all data inline (remove types dependency)
const mockSprints = [
  {
    id: 'sprint1',
    name: 'Sprint 34: June 14 — June 17',
    dateRange: 'June 14 — June 17',
    daysRemaining: 1,
    goals: 'Improve issue tracking automation',
  },
  {
    id: 'sprint2',
    name: 'Sprint 33: June 10 — June 13',
    dateRange: 'June 10 — June 13',
    daysRemaining: 0,
    goals: 'Complete dashboard implementation',
  },
  {
    id: 'sprint3',
    name: 'Sprint 32: June 6 — June 9',
    dateRange: 'June 6 — June 9',
    daysRemaining: 0,
    goals: 'Refactor core modules',
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
  // State declarations with proper separation
  const [selectedSprint, setSelectedSprint] = useState('sprint1');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('harmoniaailabs/Symptom-to-Next-Step-Advisor-Non-Diagnostic-');
  const [selectedProjectNumber, setSelectedProjectNumber] = useState<number>(1); // Default project
  const [issueDescription, setIssueDescription] = useState('');
  const [originalIssueDescription, setOriginalIssueDescription] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('codex');
  const [showTerminal, setShowTerminal] = useState(false);
  
  // API state
  const [sprints, setSprints] = useState<ApiSprint[]>([]);
  const [issues, setIssues] = useState<ApiIssue[]>([]);
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
      const issueData = await apiClient.getIssues(sprintName, undefined, selectedProjectNumber);
      setIssues(issueData);
    } catch (error) {
      console.warn('Failed to fetch issues:', error);
      setError('Failed to fetch issues from GitHub. Using mock data.');
      setUseMockData(true);
    } finally {
      setLoading(false);
    }
  };

  // Fetch sprint summary
  const fetchSprintSummary = async (sprintName: string) => {
    try {
      const summary = await apiClient.getSprintSummary(sprintName, selectedProjectNumber);
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
      const sprintData = await apiClient.getSprints(selectedProjectNumber);
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

  // Refetch data when project changes
  useEffect(() => {
    if (selectedProjectNumber) {
      fetchSprints();
      // Clear current sprint selection to force user to reselect
      setSelectedSprint('');
      setIssues([]);
      setSprintSummary(null);
    }
  }, [selectedProjectNumber]);

  // Fetch issues for the period when sprint changes
  useEffect(() => {
    if (!useMockData && selectedSprint && sprints.length > 0) {
      const currentSprint = sprints.find(s => s.id === selectedSprint);
      if (currentSprint) {
        fetchIssues(currentSprint.name);
        fetchSprintSummary(currentSprint.name);
      }
    }
  }, [selectedSprint, sprints, useMockData, selectedProjectNumber]);

  // Make sure we have a selected sprint when sprints are loaded
  useEffect(() => {
    if (sprints.length > 0 && !selectedSprint) {
      setSelectedSprint(sprints[0].id);
    }
  }, [sprints, selectedSprint]);
  
  // Helper function to format dates
  const formatDate = (dateString: string): string => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
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
    dateRange: s.start_date && s.end_date ? `${formatDate(s.start_date)} — ${formatDate(s.end_date)}` : s.name,
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

  const currentSprint = displaySprints.find(sprint => sprint.id === selectedSprint) || displaySprints[0];

  const handleSprintChange = (sprintId: string) => {
    setSelectedSprint(sprintId);
  };

  // Handler for repository change
  const handleRepoChange = (repo: string) => {
    setSelectedRepo(repo);
  };

  // Handler for project change
  const handleProjectChange = (projectNumber: number) => {
    setSelectedProjectNumber(projectNumber);
  };

  // Handler for when repository selector finds available projects
  const handleProjectsFound = (projects: number[]) => {
    setAvailableProjects(projects);
    // If the current selected project is not in the available projects, switch to the first available
    if (projects.length > 0 && !projects.includes(selectedProjectNumber)) {
      setSelectedProjectNumber(projects[0]);
    }
  };

  const handleAsk = () => {
    console.log('Asking for help with issue:', selectedIssue);
  };

  const handleCode = async () => {
    // Show terminal instead of running directly
    setShowTerminal(true);
    // Scroll to terminal after a brief delay
    setTimeout(() => {
      document.querySelector('.bg-gray-900')?.scrollIntoView({ 
        behavior: 'smooth' 
      });
    }, 100);
  };

  const handleCodeOld = async () => {
    const issue = displayIssues.find(issue => issue.id === selectedIssue);
    const prompt = issueDescription || "Add backend logic";
    const repo = selectedRepo; // Use selected repo instead of issue repo
    const title = issue?.title || "Issue Title";

    try {
      const result = await apiClient.runCodex(prompt, repo, title);
      alert(`✅ ${result.message}`);
    } catch (error) {
      alert("❌ Failed to trigger Codex. See console for details.");
      console.error(error);
    }
  };
  
  // Handle issue selection changes properly
  const handleIssueSelectionChange = (issueId: string) => {
    setSelectedIssue(issueId);
    const issue = displayIssues.find(issue => issue.id === issueId);
    if (issue) {
      const description = issue.body || '';
      setIssueDescription(description);
      setOriginalIssueDescription(description);
    } else {
      setIssueDescription('');
      setOriginalIssueDescription('');
    }
  };

  // Handle saving issue description changes
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedIssue || !issueDescription.trim()) {
      alert('Please select an issue and provide a description.');
      return;
    }

    const issue = displayIssues.find(issue => issue.id === selectedIssue);
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

  // Better useEffect for issue description handling
  useEffect(() => {
    if (displayIssues.length > 0) {
      // Only update if we don't have a selected issue or if the current selection is not in the new list
      const found = displayIssues.find(issue => issue.id.toString() === selectedIssue);
      if (!selectedIssue || !found) {
        const firstIssue = displayIssues[0];
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
  }, [displayIssues]); // Removed selectedIssue from dependencies

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
              🔄 Loading...
            </div>
          </div>
        )}

        {/* Project and Repository Selection */}
        <section className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-4">Project and Repository Configuration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Project Selector */}
            <ProjectSelector
              selectedProjectNumber={selectedProjectNumber}
              onProjectChange={handleProjectChange}
            />
            
            {/* Repository Selector */}
            <RepositorySelector
              selectedRepo={selectedRepo}
              onRepoChange={handleRepoChange}
              onProjectsFound={handleProjectsFound}
            />
          </div>
          
          {/* Context Info */}
          <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
            <div className="text-sm text-blue-800">
              <strong>📋 Current Context:</strong> Project #{selectedProjectNumber} | Repository: {selectedRepo}
              <br />
              <span className="text-xs text-blue-600">
                Sprints and issues will be loaded from the selected project. Repository is used for Codex operations.
              </span>
            </div>
          </div>
        </section>

        {/* Sprint Picker */}
        <section className="bg-white p-6 rounded-xl shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-2">Select Current Sprint</h2>
          <form className="space-y-4">
            <div>
              <label htmlFor="sprint-select" className="block text-sm font-medium text-gray-700">
                GitHub Sprint (Milestone) - Project #{selectedProjectNumber}
              </label>
              <select
                id="sprint-select"
                value={selectedSprint}
                onChange={(e) => handleSprintChange(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                disabled={displaySprints.length === 0}
              >
                {displaySprints.length === 0 ? (
                  <option value="">No sprints available for this project</option>
                ) : (
                  displaySprints.map((sprint) => (
                    <option key={sprint.id} value={sprint.id}>
                      {sprint.name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <button
              type="submit"
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:bg-gray-400"
              disabled={!selectedSprint}
            >
              Load Sprint
            </button>
          </form>
        </section>

        {/* Issue Helper */}
        <section className="bg-indigo-50 p-6 rounded-xl shadow border border-indigo-200">
          <h2 className="text-xl font-semibold mb-2">Ask Codex or Claude for Help</h2>
          <form className="space-y-4" onSubmit={handleSave}>
            {/* Issue selection dropdown */}
            <div>
              <label htmlFor="issue-select" className="block text-sm font-medium text-gray-700">
                Select Issue from Project #{selectedProjectNumber}
              </label>
              <select
                id="issue-select"
                value={selectedIssue}
                onChange={(e) => handleIssueSelectionChange(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                disabled={displayIssues.length === 0}
              >
                {displayIssues.length === 0 ? (
                  <option value="">No issues available for this sprint</option>
                ) : (
                  displayIssues.map((issue) => (
                    <option key={issue.id} value={issue.id}>
                      [{issue.repo}] [#{issue.number}] {issue.title}
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* Issue description textarea with change indicator */}
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

            {/* Execution Context Display */}
            <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
  <div className="text-sm text-blue-800">
    <strong>🎯 Execution Context:</strong> 
    {selectedProjectNumber === 1 ? ' Hail Project' : ` Project #${selectedProjectNumber}`} | Repository: {selectedRepo}
    <br />
    <span className="text-xs text-blue-600">
      Iterations and issues will be loaded from the selected project. Repository is used for Codex operations.
    </span>
  </div>
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
                disabled={isUpdatingIssue || !selectedIssue}
              >
                {showTerminal ? '📺 Terminal Open' : '🖥️ Open Terminal'}
              </button>
              <button
                type="button"
                onClick={handleCodeOld}
                className="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600"
                disabled={isUpdatingIssue || !selectedIssue}
              >
                Run Old Way
              </button>
              {showTerminal && (
                <button
                  type="button"
                  onClick={() => setShowTerminal(false)}
                  className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                >
                  Close Terminal
                </button>
              )}
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

        {/* Codex Terminal - Shows when showTerminal is true */}
        {showTerminal && (
          <CodexTerminal
            issueId={selectedIssue}
            issueTitle={displayIssues.find(i => i.id === selectedIssue)?.title}
            issueDescription={issueDescription}
            repo={selectedRepo} // Use selected repo instead of issue repo
          />
        )}

        {/* Sprint Info */}
        {currentSprint && (
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
            <p className="text-sm text-blue-600 mt-2">
              📋 Project #{selectedProjectNumber} | 🎯 Repository: {selectedRepo}
            </p>
          </section>
        )}

        {/* Sprint Status Summary */}
        {currentSprint && (
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
        )}

        {/* Issues List */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">
            Sprint Issues 
            {selectedProjectNumber && (
              <span className="text-sm text-gray-500 ml-2">(Project #{selectedProjectNumber})</span>
            )}
          </h3>
          <div className="space-y-4">
            {displayIssues.length === 0 ? (
              <div className="text-gray-400 text-center py-8">
                {!selectedSprint ? (
                  <div>
                    <div className="text-lg mb-2">📋 Select a Sprint</div>
                    <div className="text-sm">Choose a sprint from Project #{selectedProjectNumber} to view issues.</div>
                  </div>
                ) : (
                  <div>
                    <div className="text-lg mb-2">📝 No Issues Found</div>
                    <div className="text-sm">No issues found for this sprint in Project #{selectedProjectNumber}.</div>
                  </div>
                )}
              </div>
            ) : (
              displayIssues.map((issue) => (
                <div 
                  key={issue.id} 
                  className={`border p-4 rounded-md flex justify-between items-center ${
                    selectedIssue === issue.id ? 'bg-indigo-50 border-indigo-300' : 'bg-gray-50'
                  } hover:bg-gray-100 cursor-pointer transition-colors`}
                  onClick={() => handleIssueSelectionChange(issue.id)}
                >
                  <div>
                    <p className="font-medium">[{issue.repo}] [#{issue.number}] {issue.title}</p>
                    <p className="text-sm text-gray-500">
                      Assigned to: {issue.assignee ?? 'Unassigned'}
                    </p>
                    {selectedIssue === issue.id && (
                      <p className="text-xs text-indigo-600 mt-1">
                        ✓ Selected for Codex → Target Repo: {selectedRepo}
                      </p>
                    )}
                  </div>
                  {/* Fixed: Use the actual GitHub URL from the API */}
                  {issue.url ? (
                    <a 
                      href={issue.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                      onClick={(e) => e.stopPropagation()}
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
            <div className="text-xs mt-2">Future: Show active Codex tasks across all projects and repositories</div>
          </div>
        </section>

        {/* PR Feed */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Pull Requests</h3>
          <div className="text-gray-400 text-center py-8">
            🚧 This feature is under development.
            <div className="text-xs mt-2">Future: Show PRs from selected repository: {selectedRepo}</div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;