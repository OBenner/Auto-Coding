import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Signup } from './pages/Signup'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'
import { UsageDashboard } from './pages/UsageDashboard'
import { TaskList } from './pages/TaskList'
import { TaskDetail } from './pages/TaskDetail'
import { Dashboard } from './pages/Dashboard'
import { CreateSpec } from './pages/CreateSpec'
import { Layout } from './components/Layout'
import { useWebSocketIntegration } from './hooks/useWebSocketTaskIntegration'
import { initializeAuth } from './store/auth-store'

/**
 * TaskList wrapper component that integrates with React Router
 */
function TaskListPage() {
  const navigate = useNavigate()

  const handleTaskClick = (taskId: string) => {
    navigate(`/tasks/${taskId}`)
  }

  return <TaskList onTaskClick={handleTaskClick} />
}

/**
 * TaskDetail wrapper component that integrates with React Router
 */
function TaskDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const handleBack = () => {
    navigate('/tasks')
  }

  if (!id) {
    return <Navigate to="/tasks" replace />
  }

  return <TaskDetail taskId={id} onBack={handleBack} />
}

/**
 * App Provider Component
 * Initializes WebSocket integration and auth state on app startup
 */
function AppProvider({ children }: { children: React.ReactNode }) {
  const { isConnected } = useWebSocketIntegration()

  useEffect(() => {
    // Initialize auth state on app startup
    initializeAuth().catch((error) => {
      // Silently fail - auth check runs in background
      console.error('Failed to initialize auth:', error)
    })
  }, [])

  // You can use isConnected to show loading state or connection status
  // For now, we just render children regardless of connection state
  // The WebSocket will reconnect automatically

  return <>{children}</>
}

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          {/* Auth routes - outside layout */}
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />

          {/* Main app routes - inside layout */}
          <Route element={<Layout />}>
            {/* Dashboard is now the main landing page */}
            <Route path="/" element={<Dashboard />} />

            {/* Dashboard route */}
            <Route path="/dashboard" element={<Dashboard />} />

            {/* Task routes */}
            <Route path="/tasks" element={<TaskListPage />} />
            <Route path="/tasks/:id" element={<TaskDetailPage />} />

            {/* Create spec route */}
            <Route path="/create" element={<CreateSpec />} />

            {/* Settings and usage routes */}
            <Route path="/settings/*" element={<Settings />} />
            <Route path="/usage" element={<UsageDashboard />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  )
}

export default App
