import React, { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Signup } from './pages/Signup'
import { Login } from './pages/Login'
import { Settings } from './pages/Settings'
import { UsageDashboard } from './pages/UsageDashboard'
import { TerminalPage } from './pages/TerminalPage'
import { TaskList } from './pages/TaskList'
import { getCloudConfig, getCloudStatus } from './config/cloud'

function HomePage() {
  const cloudConfig = getCloudConfig()
  const cloudStatus = getCloudStatus()
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full bg-white rounded-lg shadow-lg p-8">
        <div className="text-center space-y-6">
          <div className="flex justify-center">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <span className="text-3xl text-white font-bold">AC</span>
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-gray-900">
              Auto Code
            </h1>
            <p className="text-xl text-gray-600">
              Web Interface
            </p>
          </div>

          <div className="pt-4 pb-2 border-t border-gray-200">
            <p className="text-gray-500 text-sm">
              Autonomous coding framework powered by Claude AI
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
              <div className="text-2xl mb-2">🤖</div>
              <h3 className="font-semibold text-gray-900 mb-1">Multi-Agent System</h3>
              <p className="text-sm text-gray-600">
                Coordinated AI agents working together
              </p>
            </div>

            <div className="p-4 bg-purple-50 rounded-lg border border-purple-100">
              <div className="text-2xl mb-2">🔒</div>
              <h3 className="font-semibold text-gray-900 mb-1">Secure Sandbox</h3>
              <p className="text-sm text-gray-600">
                Isolated execution environment
              </p>
            </div>
          </div>

          <div className="pt-6 space-y-3">
            {/* Cloud Mode Badge */}
            <div className="flex items-center justify-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200">
                <span className="text-lg">{cloudStatus.emoji}</span>
                <span className={cloudStatus.color}>{cloudStatus.label}</span>
              </span>
            </div>

            {/* API Status */}
            <p className="text-sm text-gray-500">
              API Status: <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="text-green-600 font-medium">
                  {cloudConfig.apiUrl}
                </span>
              </span>
            </p>

            {/* Cloud Info */}
            {cloudConfig.isCloud && (
              <div className="pt-2">
                <p className="text-xs text-gray-400">
                  Running in cloud-hosted mode with secure backend infrastructure
                </p>
              </div>
            )}
          </div>

          {/* Auth Links */}
          <div className="pt-6 flex gap-4 justify-center border-t border-gray-200">
            <a
              href="/tasks"
              className="px-6 py-2 text-blue-600 hover:text-blue-700 font-medium"
            >
              View Tasks
            </a>
            <a
              href="/login"
              className="px-6 py-2 text-blue-600 hover:text-blue-700 font-medium"
            >
              Sign In
            </a>
            <a
              href="/signup"
              className="px-6 py-2 bg-gradient-to-br from-blue-500 to-purple-600 text-white rounded-md hover:opacity-90 font-medium"
            >
              Get Started
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

function App() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  const handleTaskClick = (taskId: string) => {
    setSelectedTaskId(taskId)
    // TODO: Navigate to task detail page when implemented
    console.log('Task clicked:', taskId)
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
        <Route path="/settings/*" element={<Settings />} />
        <Route path="/usage" element={<UsageDashboard />} />
        <Route path="/terminal" element={<TerminalPage />} />
        <Route path="/tasks" element={<TaskList onTaskClick={handleTaskClick} />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
