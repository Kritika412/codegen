import React, { useState } from 'react';
import type { Issue } from '../types';

interface IssueHelperProps {
  issues: Issue[];
}

const IssueHelper: React.FC<IssueHelperProps> = ({ issues }) => {
  const [selectedIssue, setSelectedIssue] = useState(issues[0]?.id.toString() || '');
  const [issueDescription, setIssueDescription] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('codex');

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

  return (
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
            {issues.map((issue) => (
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
  );
};

export default IssueHelper;
