import React, { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Signup } from './pages/Signup'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'
import { UsageDashboard } from './pages/UsageDashboard'
import { TaskList } from './pages/TaskList'
import { TaskDetail } from './pages/TaskDetail'
import { Dashboard } from './pages/Dashboard'
import { CreateSpec } from './pages/CreateSpec'
import { Changelog } from "./pages/Changelog"
import { FilesPage } from "./pages/FilesPage"
import { GitOperations } from "./pages/GitOperations"
import { Insights } from "./pages/Insights"
import { Kanban } from "./pages/Kanban"
import { KanbanPilot } from "./pages/KanbanPilot"
import { Roadmap } from "./pages/Roadmap"
import { TaskCreate } from "./pages/TaskCreate"
import { IDEPage } from "./pages/IDEPage"
import { TerminalPage } from "./pages/TerminalPage"
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AppLoading } from './components/AppLoading'
import { useWebSocketIntegration } from './hooks/useWebSocketTaskIntegration'
import { initializeAuth, useAuthStore } from './store/auth-store'

/**
 * TaskList wrapper component that integrates with React Router
 */
function TaskListPage() {
  const navigate = useNavigate()

  const handleTaskClick = (taskId: string) => {
    navigate(`/tasks/${taskId}`)
  }

  const handleCreateTask = () => {
    navigate("/tasks/create")
  }

  return <TaskList onTaskClick={handleTaskClick} onCreateTask={handleCreateTask} />
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
 * Kanban wrapper component that integrates with React Router
 */
function KanbanWrapper() {
  const navigate = useNavigate()

  const handleTaskClick = (taskId: string) => {
    navigate(`/tasks/${taskId}`)
  }

  const handleCreateTask = () => {
    navigate("/tasks/create")
  }

  return (
    <Kanban onTaskClick={handleTaskClick} onCreateTask={handleCreateTask} />
  )
}

/**
 * App Provider Component
 * Initializes WebSocket integration and auth state on app startup
 * Shows loading state while auth is being verified
 */
function AppProvider({ children }: { children: React.ReactNode }) {
  useWebSocketIntegration()
  const [isInitializing, setIsInitializing] = useState(true)
  const { isVerifying } = useAuthStore()

  useEffect(() => {
    // Initialize auth state on app startup
    initializeAuth()
      .catch((error) => {
        // Silently fail - auth check runs in background
        console.error('Failed to initialize auth:', error)
      })
      .finally(() => {
        // Mark initialization as complete after auth check
        setIsInitializing(false)
      })
  }, [])

  // Show loading screen while auth is initializing or verifying
  if (isInitializing || isVerifying) {
    return <AppLoading />
  }

  return <>{children}</>
}

function App() {
  return (
    <ErrorBoundary>
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
              <Route path="/tasks/create" element={<TaskCreate />} />
              <Route path="/tasks/:id" element={<TaskDetailPage />} />

              {/* Create spec route */}
              <Route path="/create" element={<CreateSpec />} />

              {/* Kanban and project views */}
              <Route path="/kanban" element={<KanbanWrapper />} />
              {/* U1 pilot: shared-UI Kanban (libs/ui) next to the legacy one */}
              <Route path="/kanban-next" element={<KanbanPilot />} />
              <Route path="/roadmap" element={<Roadmap />} />
              <Route path="/changelog" element={<Changelog />} />
              <Route path="/insights" element={<Insights />} />

              {/* IDE route */}
              <Route path="/ide" element={<IDEPage />} />

              {/* Terminal and file management */}
              <Route path="/terminal" element={<TerminalPage />} />
              <Route path="/files" element={<FilesPage />} />
              <Route path="/git" element={<GitOperations />} />

              {/* Settings and usage routes */}
              <Route path="/settings/*" element={<Settings />} />
              <Route path="/usage" element={<UsageDashboard />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AppProvider>
    </ErrorBoundary>
  )
}

export default App;
