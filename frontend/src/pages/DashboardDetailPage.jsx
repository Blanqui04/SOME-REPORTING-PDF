import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  getDashboardDetailAPI,
  generateReportAPI,
  getReportAPI,
  downloadReportAPI,
} from '../api/client'
import PanelCard from '../components/PanelCard'
import StatusBadge from '../components/StatusBadge'

export default function DashboardDetailPage() {
  const { uid } = useParams()
  const [dashboard, setDashboard] = useState(null)
  const [selectedPanels, setSelectedPanels] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [generating, setGenerating] = useState(false)
  const [report, setReport] = useState(null)
  const pollingRef = useRef(null)

  useEffect(() => {
    getDashboardDetailAPI(uid)
      .then((res) => {
        setDashboard(res.data)
        const panels = res.data.panels.filter((p) => p.type !== 'row')
        setSelectedPanels(new Set(panels.map((p) => p.id)))
      })
      .catch((err) =>
        setError(err.response?.data?.detail || 'Error al cargar dashboard')
      )
      .finally(() => setLoading(false))
  }, [uid])

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  const panels = dashboard
    ? dashboard.panels.filter((p) => p.type !== 'row')
    : []

  const togglePanel = (panelId) => {
    setSelectedPanels((prev) => {
      const next = new Set(prev)
      if (next.has(panelId)) next.delete(panelId)
      else next.add(panelId)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedPanels.size === panels.length) {
      setSelectedPanels(new Set())
    } else {
      setSelectedPanels(new Set(panels.map((p) => p.id)))
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setReport(null)
    setError(null)
    try {
      const res = await generateReportAPI({
        dashboard_uid: uid,
        panel_ids: [...selectedPanels],
      })
      setReport(res.data)
      startPolling(res.data.id)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al generar informe')
      setGenerating(false)
    }
  }

  const startPolling = (reportId) => {
    pollingRef.current = setInterval(async () => {
      try {
        const res = await getReportAPI(reportId)
        setReport(res.data)
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          clearInterval(pollingRef.current)
          pollingRef.current = null
          setGenerating(false)
        }
      } catch {
        clearInterval(pollingRef.current)
        pollingRef.current = null
        setGenerating(false)
      }
    }, 2000)
  }

  const handleDownload = async () => {
    if (!report) return
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
      setError('Error al descargar el informe')
    }
  }

  const handleNewReport = () => {
    setReport(null)
    setError(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error && !dashboard) {
    return (
      <div>
        <Link
          to="/dashboards"
          className="text-primary-600 hover:text-primary-800 text-sm font-medium mb-4 inline-flex items-center space-x-1"
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
              d="M15.75 19.5 8.25 12l7.5-7.5"
            />
          </svg>
          <span>Volver a dashboards</span>
        </Link>
        <div className="bg-red-50 text-red-700 px-6 py-4 rounded-lg mt-4">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="pb-24">
      <Link
        to="/dashboards"
        className="text-primary-600 hover:text-primary-800 text-sm font-medium mb-6 inline-flex items-center space-x-1"
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
            d="M15.75 19.5 8.25 12l7.5-7.5"
          />
        </svg>
        <span>Volver a dashboards</span>
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {dashboard.title}
        </h1>
        {dashboard.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {dashboard.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mb-4">
        <p className="text-gray-600">
          Selecciona los paneles que quieres incluir en el informe:
        </p>
        <button
          onClick={toggleAll}
          className="text-sm text-primary-600 hover:text-primary-800 font-medium"
        >
          {selectedPanels.size === panels.length
            ? 'Deseleccionar todos'
            : 'Seleccionar todos'}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {panels.map((panel) => (
          <PanelCard
            key={panel.id}
            panel={panel}
            selected={selectedPanels.has(panel.id)}
            onToggle={() => togglePanel(panel.id)}
          />
        ))}
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 px-6 py-4 rounded-lg mt-6">
          {error}
        </div>
      )}

      {report && (
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">{report.title}</h3>
              <div className="flex items-center mt-2 space-x-3">
                <StatusBadge status={report.status} />
                {(report.status === 'pending' ||
                  report.status === 'generating') && (
                  <span className="text-sm text-gray-500">
                    Generando PDF...
                  </span>
                )}
                {report.status === 'completed' && report.pdf_size_bytes && (
                  <span className="text-sm text-gray-500">
                    {(report.pdf_size_bytes / 1024).toFixed(0)} KB
                  </span>
                )}
                {report.status === 'failed' && (
                  <span className="text-sm text-red-600">
                    {report.error_message}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {report.status === 'completed' && (
                <button
                  onClick={handleDownload}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 px-6 rounded-lg transition-colors flex items-center space-x-2"
                >
                  <svg
                    className="w-5 h-5"
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
                  <span>Descargar PDF</span>
                </button>
              )}
              {(report.status === 'completed' ||
                report.status === 'failed') && (
                <button
                  onClick={handleNewReport}
                  className="text-sm text-primary-600 hover:text-primary-800 font-medium"
                >
                  Generar otro
                </button>
              )}
            </div>
          </div>
          {(report.status === 'pending' || report.status === 'generating') && (
            <div className="mt-4 w-full bg-gray-200 rounded-full h-2">
              <div className="bg-primary-600 h-2 rounded-full animate-pulse w-2/3" />
            </div>
          )}
        </div>
      )}

      {selectedPanels.size > 0 && !report && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-lg p-4 z-10">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <span className="text-sm text-gray-600">
              {selectedPanels.size} panel
              {selectedPanels.size !== 1 ? 'es' : ''} seleccionado
              {selectedPanels.size !== 1 ? 's' : ''}
            </span>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 text-base"
            >
              {generating ? 'Generando...' : 'Generar PDF'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
