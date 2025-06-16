import React from 'react';
import type { Sprint } from '../types';

interface SprintPickerProps {
  sprints: Sprint[];
  selectedSprint: string;
  onSprintChange: (sprintId: string) => void;
}

const SprintPicker: React.FC<SprintPickerProps> = ({
  sprints,
  selectedSprint,
  onSprintChange,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle load sprint logic here
    console.log('Loading sprint:', selectedSprint);
  };

  return (
    <section className="bg-white p-6 rounded-xl shadow border border-gray-200">
      <h2 className="text-xl font-semibold mb-2">Select Current Sprint</h2>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="sprint-select" className="block text-sm font-medium text-gray-700">
            GitHub Sprint (Milestone)
          </label>
          <select
            id="sprint-select"
            value={selectedSprint}
            onChange={(e) => onSprintChange(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
          >
            {sprints.map((sprint) => (
              <option key={sprint.id} value={sprint.id}>
                {sprint.name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
        >
          Load Sprint
        </button>
      </form>
    </section>
  );
};

export default SprintPicker;
