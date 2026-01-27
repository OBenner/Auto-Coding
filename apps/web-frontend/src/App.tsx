import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { TaskList } from './pages/TaskList';
import { TaskDetail } from './pages/TaskDetail';
import './styles/responsive.css';

// Placeholder for future components
function WelcomeScreen({ onNavigateToTasks }: { onNavigateToTasks: () => void }) {
  const { t } = useTranslation(['common']);

  return (
    <div className="responsive-min-height bg-gray-50 flex items-center justify-center responsive-padding-y">
      <div className="welcome-content text-center mx-auto px-4 md:px-6 lg:px-8">
        <h1 className="responsive-heading-xl text-gray-900 mb-4 md:mb-6">
          {t('common:appName')}
        </h1>
        <p className="text-base md:text-lg lg:text-xl text-gray-600 mb-6 md:mb-8">
          Browser-based access to Auto Claude autonomous coding framework
        </p>
        <div className="responsive-card bg-white shadow-md text-left">
          <h2 className="text-lg md:text-xl lg:text-2xl font-semibold mb-3 md:mb-4">
            Getting Started
          </h2>
          <ul className="space-y-2 md:space-y-3 text-sm md:text-base text-gray-700">
            <li>• Connect to your Auto Claude backend</li>
            <li>• View and manage tasks</li>
            <li>• Monitor agent progress in real-time</li>
            <li>• Access from any device with a browser</li>
          </ul>
          <div className="mt-6 md:mt-8 flex justify-center">
            <button
              onClick={onNavigateToTasks}
              className="responsive-button bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              View Tasks
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Route types
type Route =
  | { type: 'welcome' }
  | { type: 'tasks' }
  | { type: 'task-detail'; taskId: string };

// Parse hash to determine current route
function parseRoute(hash: string): Route {
  // Remove leading '#' if present
  const path = hash.startsWith('#') ? hash.slice(1) : hash;

  if (!path || path === '/') {
    return { type: 'welcome' };
  }

  if (path === '/tasks') {
    return { type: 'tasks' };
  }

  // Match /tasks/:id pattern
  const taskDetailMatch = path.match(/^\/tasks\/([^/]+)$/);
  if (taskDetailMatch) {
    return { type: 'task-detail', taskId: taskDetailMatch[1] };
  }

  // Default to welcome for unknown routes
  return { type: 'welcome' };
}

// Generate hash for a route
function routeToHash(route: Route): string {
  switch (route.type) {
    case 'welcome':
      return '#/';
    case 'tasks':
      return '#/tasks';
    case 'task-detail':
      return `#/tasks/${route.taskId}`;
  }
}

export function App() {
  const [isLoading, setIsLoading] = useState(true);
  const [currentRoute, setCurrentRoute] = useState<Route>(() =>
    parseRoute(window.location.hash)
  );

  // Handle hash changes (browser back/forward)
  useEffect(() => {
    const handleHashChange = () => {
      setCurrentRoute(parseRoute(window.location.hash));
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Navigation helpers
  const navigateTo = useCallback((route: Route) => {
    const hash = routeToHash(route);
    window.location.hash = hash;
    setCurrentRoute(route);
  }, []);

  const navigateToTasks = useCallback(() => {
    navigateTo({ type: 'tasks' });
  }, [navigateTo]);

  const navigateToTaskDetail = useCallback((taskId: string) => {
    navigateTo({ type: 'task-detail', taskId });
  }, [navigateTo]);

  const navigateBack = useCallback(() => {
    navigateTo({ type: 'tasks' });
  }, [navigateTo]);

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

  // Render current route
  switch (currentRoute.type) {
    case 'welcome':
      return <WelcomeScreen onNavigateToTasks={navigateToTasks} />;

    case 'tasks':
      return <TaskList onTaskClick={navigateToTaskDetail} />;

    case 'task-detail':
      return <TaskDetail taskId={currentRoute.taskId} onBack={navigateBack} />;
  }
}
