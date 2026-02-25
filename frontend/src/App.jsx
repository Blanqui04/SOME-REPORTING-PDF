import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardsPage from './pages/DashboardsPage'
import DashboardDetailPage from './pages/DashboardDetailPage'
import ReportsPage from './pages/ReportsPage'
import StatsPage from './pages/StatsPage'
import TemplatesPage from './pages/TemplatesPage'
import CompareReportsPage from './pages/CompareReportsPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboards" replace />} />
          <Route path="/dashboards" element={<DashboardsPage />} />
          <Route path="/dashboards/:uid" element={<DashboardDetailPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/templates" element={<TemplatesPage />} />
          <Route path="/compare" element={<CompareReportsPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
