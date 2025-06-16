import React from 'react';
import type { AgentTask } from '../types';

interface AgentTasksProps {
  tasks: AgentTask[];
}

const AgentTasks: React.FC<AgentTasksProps> = ({ tasks }) => {
  const getStatusColor = (status: AgentTask['status']) => {
    switch (status) {
      case 'running':
        return 'text-yellow-500';
      case 'done':
        return 'text-green-600';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusText = (status: AgentTask['status']) => {
    switch (status) {
      case 'running':
        return 'Running';
      case 'done':
        return 'Done';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  return (
    <section className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold mb-4">Running Tasks (Agents)</h3>
      <ul className="space-y-4">
        {tasks.map((task) => (
          <li key={task.id} className="border p-4 rounded-md bg-gray-50">
            <div className="flex justify-between">
              <div>
                <p className="font-medium">
                  {task.agent === 'claude' ? 'Claude' : 'Codex'} is working on: {task.description}
                </p>
                <p className="text-sm text-gray-500">
                  Status: <span className={getStatusColor(task.status)}>{getStatusText(task.status)}</span>
                </p>
              </div>
              {task.prUrl && (
                <a href={task.prUrl} className="text-blue-600 hover:underline">
                  View PR
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default AgentTasks;
