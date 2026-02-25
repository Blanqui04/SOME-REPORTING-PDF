import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import translations from '../i18n/translations'

const SUPPORTED_LOCALES = ['ca', 'es', 'en', 'pl']
const STORAGE_KEY = 'app_language'

function getInitialLocale() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && SUPPORTED_LOCALES.includes(stored)) return stored

  // Try browser language
  const browserLang = navigator.language?.slice(0, 2)
  if (browserLang && SUPPORTED_LOCALES.includes(browserLang)) return browserLang

  return 'ca' // default
}

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [locale, setLocaleState] = useState(getInitialLocale)

  const setLocale = useCallback((code) => {
    if (SUPPORTED_LOCALES.includes(code)) {
      setLocaleState(code)
      localStorage.setItem(STORAGE_KEY, code)
      document.documentElement.lang = code
    }
  }, [])

  const t = useCallback(
    (key, replacements = {}) => {
      const dict = translations[locale] || translations.ca
      let text = dict[key] ?? key

      // Simple placeholder replacement: {count}, {plural}, etc.
      Object.entries(replacements).forEach(([k, v]) => {
        text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
      })

      return text
    },
    [locale]
  )

  const value = useMemo(
    () => ({ locale, setLocale, t, locales: SUPPORTED_LOCALES }),
    [locale, setLocale, t]
  )

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) throw new Error('useLanguage must be used within LanguageProvider')
  return context
}
