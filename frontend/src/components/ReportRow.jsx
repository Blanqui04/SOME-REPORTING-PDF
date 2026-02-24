import { useState } from 'react'
import { downloadReportAPI } from '../api/client'
import StatusBadge from './StatusBadge'

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatSize(bytes) {
  if (!bytes) return null
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function ReportRow({ report }) {
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const res = await downloadReportAPI(report.id)
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = report.file_name
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      // silent
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center justify-between">
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-gray-900 truncate">{report.title}</h3>
        <div className="flex items-center mt-1 space-x-2 text-sm text-gray-500 flex-wrap">
          <span>{report.dashboard_title}</span>
          <span>&middot;</span>
          <span>{formatDate(report.created_at)}</span>
          {report.pdf_size_bytes && (
            <>
              <span>&middot;</span>
              <span>{formatSize(report.pdf_size_bytes)}</span>
            </>
          )}
        </div>
        {report.error_message && (
          <p className="mt-1 text-sm text-red-600 truncate">
            {report.error_message}
          </p>
        )}
      </div>
      <div className="flex items-center space-x-3 ml-4 flex-shrink-0">
        <StatusBadge status={report.status} />
        {report.status === 'completed' && (
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors disabled:opacity-50 flex items-center space-x-1.5"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
              />
            </svg>
            <span>{downloading ? '...' : 'Descargar'}</span>
          </button>
        )}
      </div>
    </div>
  )
}
