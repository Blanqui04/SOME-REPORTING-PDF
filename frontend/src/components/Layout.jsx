import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import LanguageSelector from './LanguageSelector'

export default function Layout() {
  const { user, logout } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const linkClass = ({ isActive }) =>
    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'text-primary-700 bg-primary-50'
        : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50'
    }`

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <svg
                className="h-8 w-8 text-primary-600"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                />
              </svg>
              <span className="text-xl font-bold text-gray-900">
                PDF Reporter
              </span>
            </div>

            {/* Desktop nav */}
            <div className="hidden sm:flex items-center space-x-1">
              <NavLink to="/dashboards" className={linkClass}>
                {t('nav.dashboards')}
              </NavLink>
              <NavLink to="/reports" className={linkClass}>
                {t('nav.reports')}
              </NavLink>
              <NavLink to="/templates" className={linkClass}>
                {t('nav.templates')}
              </NavLink>
            </div>

            <div className="hidden sm:flex items-center space-x-4">
              <LanguageSelector />
              <span className="text-sm text-gray-600">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-800 font-medium transition-colors"
              >
                {t('nav.logout')}
              </button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="sm:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100"
              aria-label={t('nav.open_menu')}
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                {menuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                )}
              </svg>
            </button>
          </div>

          {/* Mobile menu */}
          {menuOpen && (
            <div className="sm:hidden border-t border-gray-200 py-3 space-y-1">
              <NavLink
                to="/dashboards"
                className={linkClass}
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.dashboards')}
              </NavLink>
              <NavLink
                to="/reports"
                className={linkClass}
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.reports')}
              </NavLink>
              <NavLink
                to="/templates"
                className={linkClass}
                onClick={() => setMenuOpen(false)}
              >
                {t('nav.templates')}
              </NavLink>
              <div className="px-4 pt-2">
                <LanguageSelector className="w-full" />
              </div>
              <div className="flex items-center justify-between px-4 pt-2 border-t border-gray-100 mt-2">
                <span className="text-sm text-gray-600">{user?.username}</span>
                <button
                  onClick={handleLogout}
                  className="text-sm text-red-600 hover:text-red-800 font-medium"
                >
                  {t('nav.logout')}
                </button>
              </div>
            </div>
          )}
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
