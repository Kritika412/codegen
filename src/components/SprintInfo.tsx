import React from 'react';
import type { Sprint } from '../types';

interface SprintInfoProps {
  sprint: Sprint;
}

const SprintInfo: React.FC<SprintInfoProps> = ({ sprint }) => {
  return (
    <section className="bg-white p-6 rounded-xl shadow">
      <h2 className="text-2xl font-bold mb-2">Current Sprint: {sprint.dateRange}</h2>
      <p className="text-gray-600">
        Days Remaining: <strong>{sprint.daysRemaining}</strong>
      </p>
      <p className="text-gray-600">Sprint Goals: {sprint.goals}</p>
    </section>
  );
};

export default SprintInfo;
