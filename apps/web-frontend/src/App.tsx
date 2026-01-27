import React from 'react'

function App() {
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
              Auto Claude
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
            <p className="text-sm text-gray-500">
              API Status: <span className="inline-flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="text-green-600 font-medium">
                  {import.meta.env.VITE_API_URL || 'Not configured'}
                </span>
              </span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
