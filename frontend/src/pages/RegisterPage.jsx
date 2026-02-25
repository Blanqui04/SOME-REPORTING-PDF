import { useState } from 'react'
import { useNavigate, Navigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { registerAPI } from '../api/client'
import LanguageSelector from '../components/LanguageSelector'

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const { user } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()

  if (user) {
    return <Navigate to="/dashboards" replace />
  }

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (form.password !== form.confirmPassword) {
      setError(t('register.passwords_mismatch'))
      return
    }

    setSubmitting(true)
    try {
      await registerAPI({
        email: form.email,
        username: form.username,
        password: form.password,
      })
      navigate('/login')
    } catch (err) {
      const msg = err.response?.data?.detail || t('register.error')
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="flex justify-end mb-4">
          <LanguageSelector />
        </div>
        <div className="text-center mb-8">
          <svg
            className="mx-auto h-12 w-12 text-primary-600"
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
          <h1 className="text-2xl font-bold text-gray-900 mt-4">
            {t('register.title')}
          </h1>
          <p className="text-gray-500 mt-2">{t('register.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('register.email')}
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow"
              placeholder={t('register.email_placeholder')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('register.username')}
            </label>
            <input
              type="text"
              name="username"
              value={form.username}
              onChange={handleChange}
              required
              minLength={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow"
              placeholder={t('register.username_placeholder')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('register.password')}
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow"
              placeholder="********"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('register.confirm_password')}
            </label>
            <input
              type="password"
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              required
              minLength={8}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow"
              placeholder="********"
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-base"
          >
            {submitting ? t('register.submitting') : t('register.submit')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          {t('register.has_account')}{' '}
          <Link
            to="/login"
            className="text-primary-600 hover:text-primary-800 font-medium"
          >
            {t('register.login_link')}
          </Link>
        </p>
      </div>
    </div>
  )
}
