import { Link } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

export default function DashboardCard({ dashboard }) {
  const { t } = useLanguage()

  return (
    <Link
      to={`/dashboards/${dashboard.uid}`}
      className="block bg-white dark:bg-gray-800 rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-100 dark:border-gray-700 p-6 hover:border-primary-200 dark:hover:border-primary-700 group"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate group-hover:text-primary-700 dark:group-hover:text-primary-400 transition-colors">
            {dashboard.title}
          </h3>
        </div>
        <svg
          className="h-5 w-5 text-gray-400 dark:text-gray-500 group-hover:text-primary-500 dark:group-hover:text-primary-400 ml-2 flex-shrink-0 transition-colors"
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
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        {t('dashboards.click_to_select')}
      </p>
    </Link>
  )
}
