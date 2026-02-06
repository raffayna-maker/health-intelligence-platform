import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import Patients from './components/Patients'
import Documents from './components/Documents'
import Analytics from './components/Analytics'
import Assistant from './components/Assistant'
import FollowupAgent from './components/FollowupAgent'
import Reports from './components/Reports'
import Security from './components/Security'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/patients" element={<Patients />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/agents" element={<FollowupAgent />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/security" element={<Security />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
