import { Link } from 'react-router-dom'

export default function DashboardCard({ dashboard }) {
  return (
    <Link
      to={`/dashboards/${dashboard.uid}`}
      className="block bg-white rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-100 p-6 hover:border-primary-200 group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 truncate group-hover:text-primary-700 transition-colors">
            {dashboard.title}
          </h3>
        </div>
        <svg
          className="h-5 w-5 text-gray-400 group-hover:text-primary-500 ml-2 flex-shrink-0 transition-colors"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m8.25 4.5 7.5 7.5-7.5 7.5"
          />
        </svg>
      </div>

      {dashboard.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
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

      <p className="mt-4 text-sm text-gray-500">
        Haz clic para seleccionar paneles
      </p>
    </Link>
  )
}
