import React from 'react';
import type { PullRequest } from '../types';

interface PullRequestsProps {
  pullRequests: PullRequest[];
}

const PullRequests: React.FC<PullRequestsProps> = ({ pullRequests }) => {
  const getStatusBadge = (status: PullRequest['status']) => {
    switch (status) {
      case 'ci-passed':
        return 'bg-green-100 text-green-600';
      case 'needs-review':
        return 'bg-yellow-100 text-yellow-600';
      case 'merged':
        return 'bg-purple-100 text-purple-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusText = (status: PullRequest['status']) => {
    switch (status) {
      case 'ci-passed':
        return 'CI Passed';
      case 'needs-review':
        return 'Needs Review';
      case 'merged':
        return 'Merged';
      default:
        return 'Unknown';
    }
  };

  return (
    <section className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold mb-4">Pull Requests</h3>
      <div className="space-y-4">
        {pullRequests.map((pr) => (
          <div key={pr.id} className="border p-4 rounded-md bg-gray-50">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">[#{pr.id}] {pr.title}</p>
                <p className="text-sm text-gray-500">
                  Author: {pr.author} | Branch: `{pr.branch}`
                </p>
              </div>
              <span className={`px-2 py-1 text-xs rounded ${getStatusBadge(pr.status)}`}>
                {getStatusText(pr.status)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default PullRequests;
