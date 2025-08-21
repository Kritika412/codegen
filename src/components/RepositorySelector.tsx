import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { ApiRepository } from '../api/client';

interface RepositorySelectorProps {
  selectedRepo: string;
  onRepoChange: (repo: string) => void;
  onProjectsFound?: (projects: number[]) => void;
  className?: string;
}

const RepositorySelector: React.FC<RepositorySelectorProps> = ({
  selectedRepo,
  onRepoChange,
  onProjectsFound,
  className = ""
}) => {
  const [repositories, setRepositories] = useState<ApiRepository[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch repositories on component mount
  useEffect(() => {
    const fetchRepositories = async () => {
      setLoading(true);
      setError(null);
      try {
        const repos = await apiClient.getRepositories();
        setRepositories(repos);
        
        // If no repo is selected and we have repos, select the first one
        if (!selectedRepo && repos.length > 0) {
          onRepoChange(repos[0].full_name);
        }
      } catch (err) {
        console.error('Failed to fetch repositories:', err);
        setError('Failed to fetch repositories');
      } finally {
        setLoading(false);
      }
    };

    fetchRepositories();
  }, []);

  // Notify parent about available projects when repository changes
  useEffect(() => {
    if (selectedRepo && repositories.length > 0 && onProjectsFound) {
      const repo = repositories.find(r => r.full_name === selectedRepo);
      if (repo && repo.projects) {
        const projectNumbers = repo.projects.map(p => p.number);
        onProjectsFound(projectNumbers);
      }
    }
  }, [selectedRepo, repositories, onProjectsFound]);

  const formatLastUpdated = (dateString: string): string => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now.getTime() - date.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays === 1) return '1 day ago';
      if (diffDays < 7) return `${diffDays} days ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
      return `${Math.floor(diffDays / 30)} months ago`;
    } catch {
      return '';
    }
  };

  if (loading) {
    return (
      <div className={`${className}`}>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Repository
        </label>
        <div className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 px-3 py-2">
          <span className="text-gray-500">🔄 Loading repositories...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className}`}>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Repository
        </label>
        <div className="mt-1 block w-full rounded-md border-red-300 bg-red-50 px-3 py-2">
          <span className="text-red-600">⚠️ {error}</span>
        </div>
      </div>
    );
  }

  const selectedRepository = repositories.find(r => r.full_name === selectedRepo);

  return (
    <div className={className}>
      <label htmlFor="repository-select" className="block text-sm font-medium text-gray-700 mb-1">
        Target Repository
      </label>
      <select
        id="repository-select"
        value={selectedRepo}
        onChange={(e) => onRepoChange(e.target.value)}
        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
      >
        {repositories.map((repo) => (
          <option key={repo.id} value={repo.full_name}>
            {repo.name} {repo.private ? '🔒' : '🌍'} - {formatLastUpdated(repo.updated_at)}
          </option>
        ))}
      </select>
      
      {/* Repository info */}
      {selectedRepository && (
        <div className="mt-2 text-xs text-gray-500">
          <div className="flex flex-col space-y-1">
            <div className="flex items-center space-x-2">
              <span>{selectedRepository.private ? '🔒 Private' : '🌍 Public'}</span>
              <span>•</span>
              <span>Default: {selectedRepository.default_branch}</span>
              <span>•</span>
              <a 
                href={selectedRepository.html_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                View on GitHub
              </a>
            </div>
            {selectedRepository.description && (
              <div className="text-gray-600 italic">
                {selectedRepository.description}
              </div>
            )}
            {/* Show associated projects */}
            {selectedRepository.projects && selectedRepository.projects.length > 0 && (
              <div className="mt-2 p-2 bg-blue-50 rounded border border-blue-200">
                <div className="text-blue-700 font-medium text-xs mb-1">
                  📋 Associated Projects ({selectedRepository.projects.length}):
                </div>
                <div className="space-y-1">
                  {selectedRepository.projects.map((project) => (
                    <div key={project.id} className="flex items-center space-x-2 text-xs">
                      <span className="text-blue-600">#{project.number}</span>
                      <span className="text-gray-700">{project.title}</span>
                      <a 
                        href={project.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RepositorySelector;