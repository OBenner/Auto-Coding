import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

// Placeholder for future components
function WelcomeScreen() {
  const { t } = useTranslation(['common']);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center max-w-2xl mx-auto px-4">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {t('common:appName')}
        </h1>
        <p className="text-lg text-gray-600 mb-6">
          Browser-based access to Auto Claude autonomous coding framework
        </p>
        <div className="bg-white rounded-lg shadow-md p-6 text-left">
          <h2 className="text-xl font-semibold mb-3">Getting Started</h2>
          <ul className="space-y-2 text-gray-700">
            <li>• Connect to your Auto Claude backend</li>
            <li>• View and manage tasks</li>
            <li>• Monitor agent progress in real-time</li>
            <li>• Access from any device with a browser</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export function App() {
  const [isLoading, setIsLoading] = useState(true);

  // Initial load - check API connection
  useEffect(() => {
    // Simulate initial load check
    const checkConnection = async () => {
      try {
        // In future subtasks, this will check API connectivity
        await new Promise(resolve => setTimeout(resolve, 500));
        setIsLoading(false);
      } catch (error) {
        console.error('[App] Initialization error:', error);
        setIsLoading(false);
      }
    };

    checkConnection();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return <WelcomeScreen />;
}
