import { useLanguage } from '../context/LanguageContext'

export default function PanelCard({ panel, selected, onToggle }) {
  const { t } = useLanguage()

  const typeLabel = t(`panel.${panel.type}`) !== `panel.${panel.type}`
    ? t(`panel.${panel.type}`)
    : panel.type

  return (
    <button
      onClick={onToggle}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
        selected
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 shadow-sm'
          : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 dark:text-white truncate">{panel.title}</p>
          <span className="inline-block mt-1.5 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
            {typeLabel}
          </span>
        </div>
        <div
          className={`flex-shrink-0 ml-3 w-6 h-6 rounded-md border-2 flex items-center justify-center transition-colors ${
            selected
              ? 'bg-primary-600 border-primary-600'
              : 'border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700'
          }`}
        >
          {selected && (
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={3}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m4.5 12.75 6 6 9-13.5"
              />
            </svg>
          )}
        </div>
      </div>
    </button>
  )
}
