import { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

const tabs = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/patients', label: 'Patients', icon: '🏥' },
  { path: '/documents', label: 'Documents', icon: '📄' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/assistant', label: 'Assistant', icon: '🤖' },
  { path: '/agents', label: 'Research', icon: '🔍' },
  { path: '/reports', label: 'Reports', icon: '📋' },
  { path: '/security', label: 'Security', icon: '🔐' },
]

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              HI
            </div>
            <h1 className="text-xl font-bold text-gray-900">Healthcare Intelligence Platform</h1>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            Admin User
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => (
              <NavLink
                key={tab.path}
                to={tab.path}
                end={tab.path === '/'}
                className={({ isActive }) =>
                  `px-4 py-3 text-sm whitespace-nowrap transition-colors ${
                    isActive
                      ? 'border-b-2 border-blue-600 text-blue-600 font-semibold'
                      : 'text-gray-500 hover:text-gray-700 hover:border-b-2 hover:border-gray-300'
                  }`
                }
              >
                <span className="mr-1.5">{tab.icon}</span>
                {tab.label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </main>
    </div>
  )
}
