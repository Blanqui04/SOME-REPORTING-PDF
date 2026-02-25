import { useLanguage } from '../context/LanguageContext'

const FLAGS = {
  ca: '🇦🇩',
  es: '🇪🇸',
  en: '🇬🇧',
  pl: '🇵🇱',
}

export default function LanguageSelector({ className = '' }) {
  const { locale, setLocale, t, locales } = useLanguage()

  return (
    <select
      value={locale}
      onChange={(e) => setLocale(e.target.value)}
      className={`bg-white border border-gray-300 rounded-lg text-sm px-2 py-1.5 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none cursor-pointer ${className}`}
      aria-label="Language"
    >
      {locales.map((code) => (
        <option key={code} value={code}>
          {FLAGS[code]} {t(`lang.${code}`)}
        </option>
      ))}
    </select>
  )
}
