import React from 'react';
import type { Issue } from '../types';

interface IssuesListProps {
  issues: Issue[];
}

const IssuesList: React.FC<IssuesListProps> = ({ issues }) => {
  return (
    <section className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold mb-4">Sprint Issues</h3>
      <div className="space-y-4">
        {issues.map((issue) => (
          <div
            key={issue.id}
            className="border p-4 rounded-md flex justify-between items-center bg-gray-50"
          >
            <div>
              <p className="font-medium">[#{issue.id}] {issue.title}</p>
              <p className="text-sm text-gray-500">Assigned to: {issue.assignee}</p>
            </div>
            <a href="#" className="text-blue-600 hover:underline">
              View on GitHub
            </a>
          </div>
        ))}
      </div>
    </section>
  );
};

export default IssuesList;
