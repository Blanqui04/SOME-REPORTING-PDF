import { useState, useEffect } from 'react'
import { getReportStatsAPI } from '../api/client'
import { useLanguage } from '../context/LanguageContext'

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STATUS_COLORS = {
  completed: 'bg-green-500 dark:bg-green-600',
  pending: 'bg-yellow-500 dark:bg-yellow-600',
  generating: 'bg-blue-500 dark:bg-blue-600',
  failed: 'bg-red-500 dark:bg-red-600',
}

export default function StatsPage() {
  const { t } = useLanguage()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getReportStatsAPI()
      .then((res) => setStats(res.data))
      .catch((err) => setError(err.response?.data?.detail || t('stats.error')))
      .finally(() => setLoading(false))
  }, [t])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('stats.title')}</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">{t('stats.subtitle')}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-white dark:bg-gray-800 rounded-xl h-32 shadow-sm border border-gray-100 dark:border-gray-700" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">{t('stats.title')}</h1>
        <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-6 py-4 rounded-lg">{error}</div>
      </div>
    )
  }

  const byStatus = stats?.by_status || {}
  const total = stats?.total || 0
  const maxStatus = Math.max(...Object.values(byStatus), 1)

  const cards = [
    {
      label: t('stats.total_reports'),
      value: total,
      icon: (
        <svg className="w-8 h-8 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
      ),
    },
    {
      label: t('stats.completed'),
      value: byStatus.completed || 0,
      icon: (
        <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
      ),
    },
    {
      label: t('stats.total_size'),
      value: formatBytes(stats?.total_size_bytes),
      icon: (
        <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
        </svg>
      ),
    },
    {
      label: t('stats.avg_size'),
      value: formatBytes(stats?.avg_size_bytes),
      icon: (
        <svg className="w-8 h-8 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
        </svg>
      ),
    },
  ]

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('stats.title')}</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">{t('stats.subtitle')}</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {cards.map((card) => (
          <div
            key={card.label}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">{card.label}</p>
                <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">{card.value}</p>
              </div>
              {card.icon}
            </div>
          </div>
        ))}
      </div>

      {/* Status distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('stats.by_status')}
          </h2>
          <div className="space-y-4">
            {Object.entries(byStatus).map(([status, count]) => (
              <div key={status}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize">
                    {t(`status.${status}`)}
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{count}</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                  <div
                    className={`h-2.5 rounded-full transition-all ${STATUS_COLORS[status] || 'bg-gray-500'}`}
                    style={{ width: `${(count / maxStatus) * 100}%` }}
                  />
                </div>
              </div>
            ))}
            {Object.keys(byStatus).length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">{t('stats.no_data')}</p>
            )}
          </div>
        </div>

        {/* Top dashboards */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('stats.top_dashboards')}
          </h2>
          {stats?.top_dashboards?.length > 0 ? (
            <div className="space-y-3">
              {stats.top_dashboards.map((d, idx) => (
                <div key={d.dashboard_uid} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-bold text-gray-400 dark:text-gray-500 w-6 text-right">
                      #{idx + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {d.dashboard_title || d.dashboard_uid}
                    </span>
                  </div>
                  <span className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                    {d.count} {d.count === 1 ? t('stats.report_singular') : t('stats.report_plural')}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">{t('stats.no_data')}</p>
          )}
        </div>
      </div>
    </div>
  )
}
