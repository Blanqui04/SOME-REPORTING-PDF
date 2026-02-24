import { useState, useEffect } from 'react'
import { getReportsAPI } from '../api/client'
import ReportRow from '../components/ReportRow'

const statusTabs = [
  { label: 'Todos', value: null },
  { label: 'Completados', value: 'completed' },
  { label: 'Pendientes', value: 'pending' },
  { label: 'Fallidos', value: 'failed' },
]

export default function ReportsPage() {
  const [reports, setReports] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState(null)
  const [loading, setLoading] = useState(true)

  const perPage = 10

  useEffect(() => {
    setLoading(true)
    getReportsAPI(page, perPage, statusFilter)
      .then((res) => {
        setReports(res.data.items)
        setPages(res.data.pages)
        setTotal(res.data.total)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [page, statusFilter])

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Historial de informes
        </h1>
        <p className="text-gray-500 mt-1">
          {total} informe{total !== 1 ? 's' : ''} en total
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
                ? 'bg-primary-100 text-primary-700'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-white rounded-xl h-20 shadow-sm border border-gray-100"
            />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <svg
            className="mx-auto h-16 w-16 text-gray-300 mb-4"
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
          <p className="text-lg">No hay informes todavia</p>
          <p className="mt-2">Genera tu primer informe desde un dashboard</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <ReportRow key={r.id} report={r} />
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="mt-8 flex items-center justify-center space-x-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50 transition-colors"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Pagina {page} de {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page === pages}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm disabled:opacity-50 hover:bg-gray-50 transition-colors"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  )
}
