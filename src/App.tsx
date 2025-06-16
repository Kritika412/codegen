import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import './App.css';
import { apiClient } from './api/client';
import type { ApiIssue, ApiSprint } from './api/client';

// 모든 데이터를 인라인으로 정의 (types 의존성 제거)
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

function App() {
  const [selectedSprint, setSelectedSprint] = useState('sprint1');
  const [selectedIssue, setSelectedIssue] = useState('');
  const [issueDescription, setIssueDescription] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('codex');
  
  // API 상태
  const [sprints, setSprints] = useState<ApiSprint[]>([]);
  const [issues, setIssues] = useState<ApiIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Mock data fallback
  const [useMockData, setUseMockData] = useState(false);
  
  // API 데이터 가져오기
  const fetchSprints = async () => {
    try {
      const sprintData = await apiClient.getSprints();
      setSprints(sprintData);
      if (sprintData.length > 0 && !selectedSprint) {
        setSelectedSprint(sprintData[0].id);
      }
    } catch (error) {
      console.warn('Failed to fetch sprints, using mock data:', error);
      setUseMockData(true);
    }
  };
  
  const fetchIssues = async (sprintName?: string) => {
    setLoading(true);
    setError(null);
    try {
      const issueData = await apiClient.getIssues(sprintName);
      setIssues(issueData);
      if (issueData.length > 0 && !selectedIssue) {
        setSelectedIssue(issueData[0].number.toString());
      }
    } catch (error) {
      console.warn('Failed to fetch issues:', error);
      setError('Failed to fetch issues from GitHub. Using mock data.');
      setUseMockData(true);
    } finally {
      setLoading(false);
    }
  };
  
  // 컴포넌트 마운트 시 데이터 초기화
  useEffect(() => {
    fetchSprints();
    fetchIssues();
  }, []);
  
  // Sprint 변경 시 해당 기간 이슈 가져오기
  useEffect(() => {
    if (!useMockData && selectedSprint) {
      const currentSprint = sprints.find(s => s.id === selectedSprint);
      if (currentSprint) {
        fetchIssues(currentSprint.name);
      }
    }
  }, [selectedSprint, sprints, useMockData]);
  
  // 현재 표시할 데이터 선택
  const displaySprints = useMockData ? mockSprints : sprints.length > 0 ? sprints.map(s => ({
    id: s.id,
    name: s.name,
    dateRange: `${s.start_date} – ${s.end_date}`,
    daysRemaining: Math.max(0, Math.ceil((new Date(s.end_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))),
    goals: 'Sprint goals from API'
  })) : mockSprints;
  
  const displayIssues = useMockData
    ? []
    : issues.length > 0
      ? issues.map(issue => ({
          id: issue.number,
          title: issue.title,
          assignee: issue.assignee || 'Unassigned',
          status: issue.status,
          body: issue.body || '',
        }))
      : [];
  
  const currentSprint = displaySprints.find(sprint => sprint.id === selectedSprint) || displaySprints[0];

  const handleSprintChange = (sprintId: string) => {
    setSelectedSprint(sprintId);
  };

  const handleAsk = () => {
    console.log('Asking for help with issue:', selectedIssue);
  };

  const handleCode = () => {
    console.log('Generating code for issue:', selectedIssue);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Saving changes:', { selectedIssue, issueDescription, selectedLLM });
  };

  // Ensure initial issue description is set when issues are loaded
  useEffect(() => {
    if (displayIssues.length > 0) {
      // If selectedIssue is not in the list, select the first one
      const found = displayIssues.find(issue => issue.id.toString() === selectedIssue);
      if (!selectedIssue || !found) {
        setSelectedIssue(displayIssues[0].id.toString());
        setIssueDescription(displayIssues[0].body || '');
      } else {
        setIssueDescription(found.body || '');
      }
    } else {
      setIssueDescription('');
    }
    // eslint-disable-next-line
  }, [displayIssues, selectedIssue]);

  return (
    <div className="bg-gray-100 text-gray-900 min-h-screen">
      <Header />
      
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        {/* 에러 메시지 */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <div className="text-sm text-yellow-700">
              <strong>⚠️ {error}</strong>
            </div>
          </div>
        )}
        
        {/* 로딩 인디케이터 */}
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
            <div>
              <label htmlFor="issue-select" className="block text-sm font-medium text-gray-700">
                Select Issue
              </label>
              <select
                id="issue-select"
                value={selectedIssue}
                onChange={(e) => setSelectedIssue(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
              >
                {displayIssues.map((issue) => (
                  <option key={issue.id} value={issue.id.toString()}>
                    [#{issue.id}] {issue.title}
                  </option>
                ))}
              </select>
            </div>

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
              />
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
                <option value="claude">Claude</option>
              </select>
            </div>

            <div className="flex space-x-4">
              <button
                type="button"
                onClick={handleAsk}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Ask
              </button>
              <button
                type="button"
                onClick={handleCode}
                className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
              >
                Code
              </button>
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Save Changes
              </button>
            </div>
          </form>
        </section>

        {/* Sprint Info */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h2 className="text-2xl font-bold mb-2">Current Sprint: {currentSprint.dateRange}</h2>
          <p className="text-gray-600">Days Remaining: <strong>{currentSprint.daysRemaining}</strong></p>
          <p className="text-gray-600">Sprint Goals: {currentSprint.goals}</p>
        </section>

        {/* Sprint Status Summary */}
        <section className="bg-white p-6 rounded-xl shadow grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold">{mockStats.total}</div>
            <div className="text-sm text-gray-500">Total Issues</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{mockStats.completed}</div>
            <div className="text-sm text-gray-500">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-500">{mockStats.inProgress}</div>
            <div className="text-sm text-gray-500">In Progress</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-500">{mockStats.blocked}</div>
            <div className="text-sm text-gray-500">Blocked</div>
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
                    <p className="font-medium">[#{issue.id}] {issue.title}</p>
                    <p className="text-sm text-gray-500">Assigned to: {issue.assignee}</p>
                  </div>
                  <a href="#" className="text-blue-600 hover:underline">View on GitHub</a>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Active Agent Tasks */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Running Tasks (Agents)</h3>
          <ul className="space-y-4">
            {mockAgentTasks.map((task) => (
              <li key={task.id} className="border p-4 rounded-md bg-gray-50">
                <div className="flex justify-between">
                  <div>
                    <p className="font-medium">{task.agent === 'claude' ? 'Claude is working on:' : 'Codex refactoring:'} {task.description}</p>
                    <p className="text-sm text-gray-500">
                      Status: <span className={task.status === 'running' ? 'text-yellow-500' : 'text-green-600'}>{task.status === 'running' ? 'Running' : 'Done'}</span>
                    </p>
                  </div>
                  <a href="#" className="text-blue-600 hover:underline">View PR</a>
                </div>
              </li>
            ))}
          </ul>
        </section>

        {/* PR Feed */}
        <section className="bg-white p-6 rounded-xl shadow">
          <h3 className="text-xl font-semibold mb-4">Pull Requests</h3>
          <div className="space-y-4">
            {mockPullRequests.map((pr) => (
              <div key={pr.id} className="border p-4 rounded-md bg-gray-50">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="font-medium">[#{pr.id}] {pr.title}</p>
                    <p className="text-sm text-gray-500">Author: {pr.author} | Branch: `{pr.branch}`</p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded ${
                    pr.status === 'ci-passed' ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
                  }`}>
                    {pr.status === 'ci-passed' ? 'CI Passed' : 'Needs Review'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
