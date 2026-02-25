import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import LanguageSelector from './LanguageSelector'
import ThemeToggle from './ThemeToggle'

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
        ? 'text-primary-700 bg-primary-50 dark:text-primary-300 dark:bg-primary-900/40'
        : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:text-primary-400 dark:hover:bg-gray-700'
    }`

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <svg
                className="h-8 w-8 text-primary-600 dark:text-primary-400"
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
              <span className="text-xl font-bold text-gray-900 dark:text-white">
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
              <NavLink to="/stats" className={linkClass}>
                {t('nav.stats')}
              </NavLink>
              <NavLink to="/templates" className={linkClass}>
                {t('nav.templates')}
              </NavLink>
              <NavLink to="/compare" className={linkClass}>
                {t('nav.compare')}
              </NavLink>
            </div>

            <div className="hidden sm:flex items-center space-x-3">
              <ThemeToggle />
              <LanguageSelector />
              <span className="text-sm text-gray-600 dark:text-gray-300">{user?.username}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 font-medium transition-colors"
              >
                {t('nav.logout')}
              </button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="sm:hidden p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
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
            <div className="sm:hidden border-t border-gray-200 dark:border-gray-700 py-3 space-y-1">
              <NavLink to="/dashboards" className={linkClass} onClick={() => setMenuOpen(false)}>
                {t('nav.dashboards')}
              </NavLink>
              <NavLink to="/reports" className={linkClass} onClick={() => setMenuOpen(false)}>
                {t('nav.reports')}
              </NavLink>
              <NavLink to="/stats" className={linkClass} onClick={() => setMenuOpen(false)}>
                {t('nav.stats')}
              </NavLink>
              <NavLink to="/templates" className={linkClass} onClick={() => setMenuOpen(false)}>
                {t('nav.templates')}
              </NavLink>
              <NavLink to="/compare" className={linkClass} onClick={() => setMenuOpen(false)}>
                {t('nav.compare')}
              </NavLink>
              <div className="px-4 pt-2 flex items-center space-x-3">
                <ThemeToggle />
                <LanguageSelector className="flex-1" />
              </div>
              <div className="flex items-center justify-between px-4 pt-2 border-t border-gray-100 dark:border-gray-700 mt-2">
                <span className="text-sm text-gray-600 dark:text-gray-300">{user?.username}</span>
                <button
                  onClick={handleLogout}
                  className="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 font-medium"
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
