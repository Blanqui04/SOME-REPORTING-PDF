import { Link } from 'react-router-dom'
import { useLanguage } from '../context/LanguageContext'

export default function NotFoundPage() {
  const { t } = useLanguage()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          {t('notfound.title')}
        </h2>
        <p className="text-gray-500 mb-8">
          {t('notfound.subtitle')}
        </p>
        <Link
          to="/dashboards"
          className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors inline-block"
        >
          {t('notfound.back')}
        </Link>
      </div>
    </div>
  )
}
