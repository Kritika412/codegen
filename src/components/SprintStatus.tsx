import React from 'react';
import type { SprintStats } from '../types';

interface SprintStatusProps {
  stats: SprintStats;
}

const SprintStatus: React.FC<SprintStatusProps> = ({ stats }) => {
  return (
    <section className="bg-white p-6 rounded-xl shadow grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="text-center">
        <div className="text-3xl font-bold">{stats.total}</div>
        <div className="text-sm text-gray-500">Total Issues</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-green-600">{stats.completed}</div>
        <div className="text-sm text-gray-500">Completed</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-yellow-500">{stats.inProgress}</div>
        <div className="text-sm text-gray-500">In Progress</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold text-red-500">{stats.blocked}</div>
        <div className="text-sm text-gray-500">Blocked</div>
      </div>
    </section>
  );
};

export default SprintStatus;
