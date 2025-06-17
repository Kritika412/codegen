const API_BASE_URL = 'http://localhost:8000/api';

export interface ApiIssue {
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
  start_date: string;
  end_date: string;
}

class ApiClient {
  private async fetchWithErrorHandling(url: string): Promise<any> {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  async getIssues(sprintName?: string): Promise<ApiIssue[]> {
    const url = sprintName 
      ? `${API_BASE_URL}/issues?sprint_name=${encodeURIComponent(sprintName)}`
      : `${API_BASE_URL}/issues`;
    
    return this.fetchWithErrorHandling(url);
  }

  async getSprints(): Promise<ApiSprint[]> {
    return this.fetchWithErrorHandling(`${API_BASE_URL}/sprints`);
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
  
  
  
}

export const apiClient = new ApiClient();
