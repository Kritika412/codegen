import { useState } from 'react';

function App() {
  const [selectedSprint, setSelectedSprint] = useState('sprint1');

  return (
    <div className="bg-gray-100 text-gray-900 min-h-screen">
      <header className="bg-indigo-700 text-white py-4 shadow">
        <div className="max-w-7xl mx-auto px-6">
          <h1 className="text-3xl font-bold">Harmonia Agile Agentic Framework</h1>
        </div>
      </header>
      
      <div className="max-w-7xl mx-auto p-6 space-y-8">
        <div className="bg-white p-6 rounded-xl shadow">
          <h2 className="text-xl font-semibold">Direct Header (No Component)</h2>
          <p>Selected Sprint: {selectedSprint}</p>
          <button 
            onClick={() => setSelectedSprint('sprint2')}
            className="bg-blue-500 text-white px-4 py-2 rounded"
          >
            Change Sprint
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
