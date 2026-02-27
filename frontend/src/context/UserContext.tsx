import React, { createContext, useContext, useEffect, useState } from 'react'
import { setAuthToken } from '../api/client'

interface DemoUser {
  username: string
  display_name: string
  role: string
  assigned_patients: string[]
}

interface UserContextValue {
  currentUser: DemoUser | null
  allUsers: DemoUser[]
  selectUser: (username: string) => Promise<void>
  clearUser: () => void
}

const UserContext = createContext<UserContextValue>({
  currentUser: null,
  allUsers: [],
  selectUser: async () => {},
  clearUser: () => {},
})

export function useUser() {
  return useContext(UserContext)
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [allUsers, setAllUsers] = useState<DemoUser[]>([])
  const [currentUser, setCurrentUser] = useState<DemoUser | null>(null)

  useEffect(() => {
    fetch('/api/auth/users')
      .then(r => r.json())
      .then(data => setAllUsers(data.users || []))
      .catch(() => {})
  }, [])

  async function selectUser(username: string) {
    const res = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    })
    if (!res.ok) throw new Error('Failed to get token')
    const data = await res.json()
    setAuthToken(data.access_token)
    setCurrentUser({
      username: data.username,
      display_name: data.display_name,
      role: data.role,
      assigned_patients: data.assigned_patients || [],
    })
  }

  function clearUser() {
    setAuthToken(null)
    setCurrentUser(null)
  }

  return (
    <UserContext.Provider value={{ currentUser, allUsers, selectUser, clearUser }}>
      {children}
    </UserContext.Provider>
  )
}
