import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { ApiProject } from '../api/client';

interface ProjectSelectorProps {
  selectedProjectNumber: number;
  onProjectChange: (projectNumber: number) => void;
  className?: string;
}

const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  selectedProjectNumber,
  onProjectChange,
  className = ""
}) => {
  const [projects, setProjects] = useState<ApiProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch projects on component mount
  useEffect(() => {
    const fetchProjects = async () => {
      setLoading(true);
      setError(null);
      try {
        const projectData = await apiClient.getProjects();
        setProjects(projectData);
        
        // If no project is selected and we have projects, select the first one
        if (!selectedProjectNumber && projectData.length > 0) {
          onProjectChange(projectData[0].number);
        }
      } catch (err) {
        console.error('Failed to fetch projects:', err);
        setError('Failed to fetch projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

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
          GitHub Project
        </label>
        <div className="mt-1 block w-full rounded-md border-gray-300 bg-gray-100 px-3 py-2">
          <span className="text-gray-500">🔄 Loading projects...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className}`}>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          GitHub Project
        </label>
        <div className="mt-1 block w-full rounded-md border-red-300 bg-red-50 px-3 py-2">
          <span className="text-red-600">⚠️ {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <label htmlFor="project-select" className="block text-sm font-medium text-gray-700 mb-1">
        GitHub Project
      </label>
      <select
        id="project-select"
        value={selectedProjectNumber}
        onChange={(e) => onProjectChange(parseInt(e.target.value))}
        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
      >
        {projects.map((project) => (
          <option key={project.id} value={project.number}>
            Project #{project.number}: {project.title}
          </option>
        ))}
      </select>
      
      {/* Project info */}
      {selectedProjectNumber && (
        <div className="mt-2 text-xs text-gray-500">
          {(() => {
            const project = projects.find(p => p.number === selectedProjectNumber);
            if (!project) return null;
            
            return (
              <div className="flex flex-col space-y-1">
                <div className="flex items-center space-x-2">
                  <span>📋 Project #{project.number}</span>
                  <span>•</span>
                  <span>Updated: {formatLastUpdated(project.updated_at)}</span>
                  <span>•</span>
                  <a 
                    href={project.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    View Project
                  </a>
                </div>
                <div className="text-gray-600 italic">
                  {project.title}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export default ProjectSelector;