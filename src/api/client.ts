// Enhanced client.ts with project management

const API_BASE_URL = 'http://localhost:8000/api';

export interface ApiIssue {
  url: string;
  repository: string;
  repo: string;
  id: number;
  number: number;
  title: string;
  assignee: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  body: string | null;
  labels: string[];
}

export interface ApiSprint {
  id: string;
  name: string;
  original_name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

// Enhanced repository interface with projects
export interface ApiProject {
  id: string;
  number: number;
  title: string;
  url: string;
  repository_name?: string;
  repository_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ApiRepository {
  id: string;
  name: string;
  full_name: string;
  description: string | null;
  private: boolean;
  html_url: string;
  default_branch: string;
  updated_at: string;
  projects: ApiProject[];
}

// Add new branch interface
export interface ApiBranch {
  name: string;
  sha: string;
  protected: boolean;
}

export interface ApiRepositoryBranches {
  repository: string;
  default_branch: string;
  branches: ApiBranch[];
}

export interface ApiSprintSummary {
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

class ApiClient {
  private async fetchWithErrorHandling<T>(url: string): Promise<T> {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json() as T;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Enhanced methods with project support
  async getIssues(sprintName?: string, status?: string, projectNumber?: number): Promise<ApiIssue[]> {
    let url = `${API_BASE_URL}/issues`;
    const params = new URLSearchParams();
    
    if (sprintName) params.append('sprint_name', sprintName);
    if (status) params.append('status', status);
    if (projectNumber) params.append('project_number', projectNumber.toString());
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    return this.fetchWithErrorHandling<ApiIssue[]>(url);
  }

  async getReadyIssues(sprintName: string, projectNumber?: number): Promise<ApiIssue[]> {
    let url = `${API_BASE_URL}/issues/ready?sprint_name=${encodeURIComponent(sprintName)}`;
    if (projectNumber) {
      url += `&project_number=${projectNumber}`;
    }
    return this.fetchWithErrorHandling<ApiIssue[]>(url);
  }

  async getSprints(projectNumber?: number): Promise<ApiSprint[]> {
    let url = `${API_BASE_URL}/sprints`;
    if (projectNumber) {
      url += `?project_number=${projectNumber}`;
    }
    return this.fetchWithErrorHandling<ApiSprint[]>(url);
  }

  async getSprintSummary(sprintName: string, projectNumber?: number): Promise<ApiSprintSummary> {
    let url = `${API_BASE_URL}/sprint-summary?sprint_name=${encodeURIComponent(sprintName)}`;
    if (projectNumber) {
      url += `&project_number=${projectNumber}`;
    }
    return this.fetchWithErrorHandling<ApiSprintSummary>(url);
  }

  // Repository and project methods
  async getRepositories(): Promise<ApiRepository[]> {
    return this.fetchWithErrorHandling<ApiRepository[]>(`${API_BASE_URL}/repositories`);
  }

  async getProjects(): Promise<ApiProject[]> {
    return this.fetchWithErrorHandling<ApiProject[]>(`${API_BASE_URL}/projects`);
  }

  async getRepositoryBranches(repoName: string): Promise<ApiRepositoryBranches> {
    const url = `${API_BASE_URL}/repositories/${encodeURIComponent(repoName)}/branches`;
    return this.fetchWithErrorHandling<ApiRepositoryBranches>(url);
  }
  
  async triggerCodexGeneration(): Promise<{ message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/run-codex`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Codex trigger error:", error);
      throw error;
    }
  }

  // Update codex method to accept repository parameter
  async runCodex(prompt: string, repo: string, title: string): Promise<{ message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/run-codex`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, repo, title }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Codex run error:", error);
      throw error;
    }
  }
}

export const apiClient = new ApiClient();