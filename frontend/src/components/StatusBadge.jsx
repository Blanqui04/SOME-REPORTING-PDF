import { useLanguage } from '../context/LanguageContext'

export default function StatusBadge({ status }) {
  const { t } = useLanguage()

  const config = {
    pending:    { classes: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300' },
    generating: { classes: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' },
    completed:  { classes: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300' },
    failed:     { classes: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300' },
  }

  const label = t(`status.${status}`) !== `status.${status}`
    ? t(`status.${status}`)
    : status

  const { classes } = config[status] || config.pending

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${classes}`}
    >
      {status === 'generating' && (
        <span className="mr-1.5 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
      )}
      {label}
    </span>
  )
}
