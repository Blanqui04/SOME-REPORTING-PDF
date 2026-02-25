import { useState, useEffect, useCallback } from 'react'
import { getReportsAPI, downloadReportAPI } from '../api/client'
import { useLanguage } from '../context/LanguageContext'
import StatusBadge from '../components/StatusBadge'

export default function CompareReportsPage() {
  const { t } = useLanguage()
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [leftId, setLeftId] = useState('')
  const [rightId, setRightId] = useState('')
  const [leftUrl, setLeftUrl] = useState(null)
  const [rightUrl, setRightUrl] = useState(null)
  const [loadingPdf, setLoadingPdf] = useState({ left: false, right: false })

  useEffect(() => {
    getReportsAPI({ status: 'completed', per_page: 100 })
      .then((res) => setReports(res.data.items || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const loadPdf = useCallback(async (reportId, side) => {
    if (!reportId) return
    setLoadingPdf((prev) => ({ ...prev, [side]: true }))
    try {
      const res = await downloadReportAPI(reportId)
      const url = URL.createObjectURL(res.data)
      if (side === 'left') {
        if (leftUrl) URL.revokeObjectURL(leftUrl)
        setLeftUrl(url)
      } else {
        if (rightUrl) URL.revokeObjectURL(rightUrl)
        setRightUrl(url)
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingPdf((prev) => ({ ...prev, [side]: false }))
    }
  }, [leftUrl, rightUrl])

  useEffect(() => {
    loadPdf(leftId, 'left')
  }, [leftId])

  useEffect(() => {
    loadPdf(rightId, 'right')
  }, [rightId])

  useEffect(() => {
    return () => {
      if (leftUrl) URL.revokeObjectURL(leftUrl)
      if (rightUrl) URL.revokeObjectURL(rightUrl)
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    )
  }

  const completedReports = reports.filter((r) => r.status === 'completed')

  const renderSelector = (side, value, onChange) => (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
    >
      <option value="">{t('compare.select_report')}</option>
      {completedReports.map((r) => (
        <option key={r.id} value={r.id}>
          {r.title} — {new Date(r.created_at).toLocaleDateString()}
        </option>
      ))}
    </select>
  )

  const renderViewer = (url, isLoading) => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      )
    }
    if (!url) {
      return (
        <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
            <p className="text-sm">{t('compare.select_to_preview')}</p>
          </div>
        </div>
      )
    }
    return (
      <iframe
        src={url}
        className="w-full h-full rounded-b-lg"
        title="PDF preview"
      />
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        {t('compare.title')}
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Left panel */}
        <div className="flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              {t('compare.report_a')}
            </label>
            {renderSelector('left', leftId, setLeftId)}
          </div>
          <div className="flex-1 bg-gray-100 dark:bg-gray-900">
            {renderViewer(leftUrl, loadingPdf.left)}
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="p-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
              {t('compare.report_b')}
            </label>
            {renderSelector('right', rightId, setRightId)}
          </div>
          <div className="flex-1 bg-gray-100 dark:bg-gray-900">
            {renderViewer(rightUrl, loadingPdf.right)}
          </div>
        </div>
      </div>
    </div>
  )
}
