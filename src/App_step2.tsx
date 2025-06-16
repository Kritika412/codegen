import Header from './components/Header';

function App() {
  return (
    <div className="bg-gray-100 text-gray-900 min-h-screen">
      <Header />
      
      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-white p-6 rounded-xl shadow">
          <h2 className="text-xl font-semibold">Test with Header Component</h2>
          <p>Header component loaded successfully!</p>
        </div>
      </div>
    </div>
  );
}

export default App;
