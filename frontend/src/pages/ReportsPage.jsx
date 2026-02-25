import { useState, useEffect } from 'react'
import { getReportsAPI, downloadReportAPI } from '../api/client'
import ReportRow from '../components/ReportRow'
import { useLanguage } from '../context/LanguageContext'

export default function ReportsPage() {
  const { t } = useLanguage()
  const [reports, setReports] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [previewName, setPreviewName] = useState('')

  const perPage = 10

  const statusTabs = [
    { label: t('reports.tab_all'), value: null },
    { label: t('reports.tab_completed'), value: 'completed' },
    { label: t('reports.tab_pending'), value: 'pending' },
    { label: t('reports.tab_failed'), value: 'failed' },
  ]

  useEffect(() => {
    setLoading(true)
    setError(null)
    getReportsAPI(page, perPage, statusFilter)
      .then((res) => {
        setReports(res.data.items)
        setPages(res.data.pages)
        setTotal(res.data.total)
      })
      .catch((err) => {
        setError(err.response?.data?.detail || t('reports.error'))
      })
      .finally(() => setLoading(false))
  }, [page, statusFilter])

  const handlePreview = async (report) => {
    try {
      const res = await downloadReportAPI(report.id)
      const url = URL.createObjectURL(res.data)
      setPreviewUrl(url)
      setPreviewName(report.title || report.file_name)
    } catch {
      setError(t('reports.preview_error'))
    }
  }

  const closePreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setPreviewName('')
  }

  const plural = total !== 1 ? 's' : ''

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('reports.title')}
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          {t('reports.total', { count: total, plural })}
        </p>
      </div>

      <div className="flex space-x-2 mb-6 flex-wrap gap-y-2">
        {statusTabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => {
              setStatusFilter(tab.value)
              setPage(1)
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === tab.value
                ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 dark:border-gray-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-6 py-4 rounded-lg mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-white dark:bg-gray-800 rounded-xl h-20 shadow-sm border border-gray-100 dark:border-gray-700"
            />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <svg
            className="mx-auto h-16 w-16 text-gray-300 dark:text-gray-600 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
            />
          </svg>
          <p className="text-lg">{t('reports.empty_title')}</p>
          <p className="mt-2">{t('reports.empty_subtitle')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <ReportRow key={r.id} report={r} onPreview={handlePreview} />
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="mt-8 flex items-center justify-center space-x-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-900 dark:text-white"
          >
            {t('common.previous')}
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {t('common.page')} {page} {t('common.of')} {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-900 dark:text-white"
          >
            {t('common.next')}
          </button>
        </div>
      )}

      {/* PDF Preview Modal */}
      {previewUrl && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                {previewName}
              </h3>
              <button
                onClick={closePreview}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 p-2">
              <iframe
                src={previewUrl}
                className="w-full h-full rounded-lg border border-gray-200 dark:border-gray-700"
                title="PDF Preview"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
