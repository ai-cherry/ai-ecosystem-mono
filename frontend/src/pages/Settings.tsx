import { useState } from 'react';

const Settings = () => {
  const [apiEndpoint, setApiEndpoint] = useState('/api/v1');
  const [pollingInterval, setPollingInterval] = useState(5);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');
  
  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    
    // Simulate saving settings
    setTimeout(() => {
      setIsSaving(false);
      setSavedMessage('Settings saved successfully!');
      
      setTimeout(() => {
        setSavedMessage('');
      }, 3000);
    }, 1000);
  };
  
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
      </div>
      
      {savedMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-6">
          <span className="block sm:inline">{savedMessage}</span>
        </div>
      )}
      
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <form onSubmit={handleSave}>
          <h2 className="text-lg font-medium mb-4">API Settings</h2>
          
          <div className="mb-4">
            <label htmlFor="apiEndpoint" className="block text-sm font-medium text-gray-700 mb-1">
              API Endpoint
            </label>
            <input
              type="text"
              id="apiEndpoint"
              value={apiEndpoint}
              onChange={(e) => setApiEndpoint(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="pollingInterval" className="block text-sm font-medium text-gray-700 mb-1">
              Polling Interval (seconds)
            </label>
            <input
              type="number"
              id="pollingInterval"
              value={pollingInterval}
              onChange={(e) => setPollingInterval(parseInt(e.target.value))}
              min={1}
              max={60}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          
          <h2 className="text-lg font-medium mb-4 mt-6">Display Settings</h2>
          
          <div className="mb-4 flex items-center">
            <input
              type="checkbox"
              id="darkMode"
              checked={isDarkMode}
              onChange={(e) => setIsDarkMode(e.target.checked)}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor="darkMode" className="ml-2 block text-sm text-gray-900">
              Dark Mode
            </label>
          </div>
          
          <div className="mt-6 border-t pt-6">
            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-lg font-medium mb-4">About</h2>
        <p className="text-gray-600 mb-4">
          AI Ecosystem Admin Dashboard v1.0.0
        </p>
        <p className="text-gray-600">
          This dashboard is designed to manage and monitor AI agents and workflows
          within the AI Ecosystem platform.
        </p>
      </div>
    </div>
  );
};

export default Settings;
