export interface Sprint {
  id: string;
  name: string;
  dateRange: string;
  daysRemaining: number;
  goals: string;
}

export interface Issue {
  id: number;
  title: string;
  assignee: string;
  status: 'completed' | 'in-progress' | 'blocked' | 'todo';
  description?: string;
}

export interface AgentTask {
  id: string;
  agent: 'claude' | 'codex';
  description: string;
  status: 'running' | 'done' | 'failed';
  prUrl?: string;
}

export interface PullRequest {
  id: number;
  title: string;
  author: string;
  branch: string;
  status: 'ci-passed' | 'needs-review' | 'merged';
}

export interface SprintStats {
  total: number;
  completed: number;
  inProgress: number;
  blocked: number;
}
