import React, { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useUser } from '../context/UserContext'

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

const roleBadgeClass: Record<string, string> = {
  admin: 'bg-blue-100 text-blue-700',
  doctor: 'bg-green-100 text-green-700',
  nurse: 'bg-yellow-100 text-yellow-700',
}

export default function Layout({ children }: { children: ReactNode }) {
  const { currentUser, allUsers, selectUser, clearUser } = useUser()

  function handleUserChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    if (!val) {
      clearUser()
    } else {
      selectUser(val).catch(console.error)
    }
  }

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
          <div className="flex items-center gap-2">
            {currentUser && (
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${roleBadgeClass[currentUser.role] || 'bg-gray-100 text-gray-700'}`}>
                {currentUser.role}
              </span>
            )}
            <select
              value={currentUser?.username || ''}
              onChange={handleUserChange}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">No auth (Admin)</option>
              {allUsers.map(u => (
                <option key={u.username} value={u.username}>
                  {u.display_name} [{u.role}]
                </option>
              ))}
            </select>
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
