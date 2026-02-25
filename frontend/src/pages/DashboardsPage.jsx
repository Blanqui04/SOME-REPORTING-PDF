import { useState, useEffect, useMemo } from 'react'
import { getDashboardsAPI } from '../api/client'
import { useLanguage } from '../context/LanguageContext'
import DashboardCard from '../components/DashboardCard'

export default function DashboardsPage() {
  const [dashboards, setDashboards] = useState([])
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedTag, setSelectedTag] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const { t } = useLanguage()

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 400)
    return () => clearTimeout(timer)
  }, [search])

  useEffect(() => {
    setLoading(true)
    setError(null)
    getDashboardsAPI(debouncedSearch)
      .then((res) => setDashboards(res.data))
      .catch((err) =>
        setError(err.response?.data?.detail || t('dashboards.error'))
      )
      .finally(() => setLoading(false))
  }, [debouncedSearch, t])

  const allTags = useMemo(() => {
    const tagSet = new Set()
    dashboards.forEach((d) => (d.tags || []).forEach((tag) => tagSet.add(tag)))
    return [...tagSet].sort()
  }, [dashboards])

  const filteredDashboards = useMemo(() => {
    if (!selectedTag) return dashboards
    return dashboards.filter((d) => (d.tags || []).includes(selectedTag))
  }, [dashboards, selectedTag])

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('dashboards.title')}</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          {t('dashboards.subtitle')}
        </p>
      </div>

      <div className="mb-6">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-gray-500"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('dashboards.search_placeholder')}
            className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
          />
        </div>
      </div>

      {/* Tag filter chips */}
      {allTags.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedTag(null)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              selectedTag === null
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            {t('dashboards.all_tags')}
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                selectedTag === tag
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-white dark:bg-gray-800 rounded-xl h-40 shadow-sm border border-gray-100 dark:border-gray-700"
            />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-6 py-4 rounded-lg">
          {error}
        </div>
      ) : filteredDashboards.length === 0 ? (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <p className="text-lg">{t('dashboards.not_found')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDashboards.map((d) => (
            <DashboardCard key={d.uid} dashboard={d} />
          ))}
        </div>
      )}
    </div>
  )
}
