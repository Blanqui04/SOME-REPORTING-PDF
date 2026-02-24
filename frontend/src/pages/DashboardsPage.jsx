import { useState, useEffect } from 'react'
import { getDashboardsAPI } from '../api/client'
import DashboardCard from '../components/DashboardCard'

export default function DashboardsPage() {
  const [dashboards, setDashboards] = useState([])
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
        setError(err.response?.data?.detail || 'Error al cargar dashboards')
      )
      .finally(() => setLoading(false))
  }, [debouncedSearch])

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboards</h1>
        <p className="text-gray-500 mt-1">
          Selecciona un dashboard para generar un informe PDF
        </p>
      </div>

      <div className="mb-6">
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
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
            placeholder="Buscar dashboards..."
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-base outline-none transition-shadow"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-white rounded-xl h-40 shadow-sm border border-gray-100"
            />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-700 px-6 py-4 rounded-lg">
          {error}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg">No se encontraron dashboards</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboards.map((d) => (
            <DashboardCard key={d.uid} dashboard={d} />
          ))}
        </div>
      )}
    </div>
  )
}
