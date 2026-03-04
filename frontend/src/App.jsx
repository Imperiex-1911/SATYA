import { Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Results from './pages/Results'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/results/:analysisId" element={<Results />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
