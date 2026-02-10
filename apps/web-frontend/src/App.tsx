import React from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Signup } from './pages/Signup'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'
import { UsageDashboard } from './pages/UsageDashboard'
import { TaskList } from './pages/TaskList'
import { TaskDetail } from './pages/TaskDetail'
import { Dashboard } from './pages/Dashboard'
import { Layout } from './components/Layout'

/**
 * Temporary CreateSpec placeholder component
 * Will be replaced with full CreateSpec implementation in phase-3
 */
function CreateSpecPlaceholder() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Create Spec</h1>
      <p className="text-muted-foreground">
        Spec creation form coming soon.
      </p>
    </div>
  )
}

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

function App() {
  return (
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

          {/* Create spec route (placeholder for now) */}
          <Route path="/create" element={<CreateSpecPlaceholder />} />

          {/* Settings and usage routes */}
          <Route path="/settings/*" element={<Settings />} />
          <Route path="/usage" element={<UsageDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
