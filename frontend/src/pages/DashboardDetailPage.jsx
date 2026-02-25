import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import {
  getDashboardDetailAPI,
  generateReportAPI,
  getReportAPI,
  downloadReportAPI,
  getTemplatesAPI,
} from '../api/client'
import SortablePanelCard from '../components/SortablePanelCard'
import StatusBadge from '../components/StatusBadge'
import { useLanguage } from '../context/LanguageContext'
import { useToast } from '../components/Toast'

const FLAGS = { ca: '\u{1F1E6}\u{1F1E9}', es: '\u{1F1EA}\u{1F1F8}', en: '\u{1F1EC}\u{1F1E7}', pl: '\u{1F1F5}\u{1F1F1}' }

export default function DashboardDetailPage() {
  const { uid } = useParams()
  const { t, locale, locales } = useLanguage()
  const { addToast } = useToast()

  const [dashboard, setDashboard] = useState(null)
  const [selectedPanels, setSelectedPanels] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [generating, setGenerating] = useState(false)
  const [report, setReport] = useState(null)
  const pollingRef = useRef(null)

  const [reportOptions, setReportOptions] = useState({
    title: '',
    description: '',
    time_range_from: 'now-6h',
    time_range_to: 'now',
    language: locale,
    orientation: 'portrait',
    toc_enabled: false,
    watermark_text: '',
    panel_columns: 1,
    include_data_tables: false,
    comparison_time_from: '',
    comparison_time_to: '',
  })
  const [showOptions, setShowOptions] = useState(false)

  const [templates, setTemplates] = useState([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [panelOrder, setPanelOrder] = useState([])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  useEffect(() => {
    getDashboardDetailAPI(uid)
      .then((res) => {
        setDashboard(res.data)
        const panels = res.data.panels.filter((p) => p.type !== 'row')
        setSelectedPanels(new Set(panels.map((p) => p.id)))
        setPanelOrder(panels.map((p) => p.id))
      })
      .catch((err) =>
        setError(err.response?.data?.detail || t('detail.error_load'))
      )
      .finally(() => setLoading(false))

    getTemplatesAPI()
      .then((res) => {
        setTemplates(res.data)
        const def = res.data.find((tpl) => tpl.is_default)
        if (def) setSelectedTemplateId(def.id)
      })
      .catch(() => {})
  }, [uid])

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [])

  const allPanels = dashboard
    ? dashboard.panels.filter((p) => p.type !== 'row')
    : []

  const panelMap = Object.fromEntries(allPanels.map((p) => [p.id, p]))
  const panels = panelOrder.length > 0
    ? panelOrder.map((id) => panelMap[id]).filter(Boolean)
    : allPanels

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setPanelOrder((prev) => {
        const oldIndex = prev.indexOf(active.id)
        const newIndex = prev.indexOf(over.id)
        return arrayMove(prev, oldIndex, newIndex)
      })
    }
  }

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
      const payload = {
        dashboard_uid: uid,
        panel_ids: panelOrder.filter((id) => selectedPanels.has(id)),
        title: reportOptions.title || undefined,
        description: reportOptions.description || undefined,
        time_range_from: reportOptions.time_range_from,
        time_range_to: reportOptions.time_range_to,
        template_id: selectedTemplateId || undefined,
        language: reportOptions.language,
        orientation: reportOptions.orientation,
        toc_enabled: reportOptions.toc_enabled,
        watermark_text: reportOptions.watermark_text || undefined,
        panel_columns: reportOptions.panel_columns,
        include_data_tables: reportOptions.include_data_tables,
        comparison_time_from: reportOptions.comparison_time_from || undefined,
        comparison_time_to: reportOptions.comparison_time_to || undefined,
      }
      const res = await generateReportAPI(payload)
      setReport(res.data)
      addToast(t('detail.toast_generating'), 'info')
      startPolling(res.data.id)
    } catch (err) {
      setError(err.response?.data?.detail || t('detail.error_generate'))
      addToast(t('detail.error_generate'), 'error')
      setGenerating(false)
    }
  }

  const startPolling = (reportId) => {
    pollingRef.current = setInterval(async () => {
      try {
        const res = await getReportAPI(reportId)
        setReport(res.data)
        if (res.data.status === 'completed') {
          clearInterval(pollingRef.current)
          pollingRef.current = null
          setGenerating(false)
          addToast(t('detail.toast_completed'), 'success')
        } else if (res.data.status === 'failed') {
          clearInterval(pollingRef.current)
          pollingRef.current = null
          setGenerating(false)
          addToast(t('detail.toast_failed'), 'error')
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
      setError(t('detail.error_download'))
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
          className="text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 text-sm font-medium mb-4 inline-flex items-center space-x-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
          <span>{t('detail.back')}</span>
        </Link>
        <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-6 py-4 rounded-lg mt-4">
          {error}
        </div>
      </div>
    )
  }

  const plural = selectedPanels.size !== 1 ? 's' : ''

  return (
    <div className="pb-24">
      <Link
        to="/dashboards"
        className="text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 text-sm font-medium mb-6 inline-flex items-center space-x-1"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
        <span>{t('detail.back')}</span>
      </Link>

      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {dashboard.title}
            </h1>
            {dashboard.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
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
          </div>
          <a
            href={`${window.location.protocol}//${window.location.hostname}:3000/d/${uid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-2 px-3 py-1.5 text-sm font-medium text-orange-700 bg-orange-50 hover:bg-orange-100 border border-orange-200 rounded-lg transition-colors dark:text-orange-300 dark:bg-orange-900/30 dark:hover:bg-orange-900/50 dark:border-orange-700"
            title={t('detail.open_grafana')}
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22 5.72c-.17-.85-.54-2.16-2.38-2.55-.48-.1-.97-.15-1.45-.15-1.07 0-2.12.29-3.04.83A6.59 6.59 0 0 0 12 3a6.59 6.59 0 0 0-3.13.85A5.96 5.96 0 0 0 5.83 3C5.35 3 4.86 3.05 4.38 3.17 2.54 3.56 2.17 4.87 2 5.72c-.19.93-.17 1.91.06 2.83.05.2.11.39.19.57A3.78 3.78 0 0 0 2 10.5C2 14.64 6.69 18 12 18s10-3.36 10-7.5c0-.48-.08-.94-.25-1.38.08-.18.14-.37.19-.57.23-.92.25-1.9.06-2.83ZM12 16c-4.42 0-8-2.69-8-5.5A1.82 1.82 0 0 1 5 8.9c.32-.19.67-.31 1.04-.36.57-.08 1.16.05 1.66.37.52.33 1.15.51 1.8.51.64 0 1.27-.18 1.8-.51.52-.33 1.12-.46 1.7-.37.58.08 1.12.36 1.5.78.38.42.64.95.73 1.52.03.16.05.33.05.5 0 .76-.22 1.48-.62 2.11A6.2 6.2 0 0 1 12 16Z" />
            </svg>
            <span>Grafana</span>
          </a>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4">
        <p className="text-gray-600 dark:text-gray-300">
          {t('detail.select_panels')}
        </p>
        <button
          onClick={toggleAll}
          className="text-sm text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
        >
          {selectedPanels.size === panels.length
            ? t('detail.deselect_all')
            : t('detail.select_all')}
        </button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={panels.map((p) => p.id)} strategy={rectSortingStrategy}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {panels.map((panel) => (
              <SortablePanelCard
                key={panel.id}
                panel={panel}
                selected={selectedPanels.has(panel.id)}
                onToggle={() => togglePanel(panel.id)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-6 py-4 rounded-lg mt-6">
          {error}
        </div>
      )}

      {report && (
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{report.title}</h3>
              <div className="flex items-center mt-2 space-x-3">
                <StatusBadge status={report.status} />
                {(report.status === 'pending' || report.status === 'generating') && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {t('detail.generating_pdf')}
                  </span>
                )}
                {report.status === 'completed' && report.pdf_size_bytes && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {(report.pdf_size_bytes / 1024).toFixed(0)} KB
                  </span>
                )}
                {report.status === 'failed' && (
                  <span className="text-sm text-red-600 dark:text-red-400">
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
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  <span>{t('detail.download_pdf')}</span>
                </button>
              )}
              {(report.status === 'completed' || report.status === 'failed') && (
                <button
                  onClick={handleNewReport}
                  className="text-sm text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
                >
                  {t('detail.generate_another')}
                </button>
              )}
            </div>
          </div>
          {(report.status === 'pending' || report.status === 'generating') && (
            <div className="mt-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div className="bg-primary-600 h-2 rounded-full animate-pulse w-2/3" />
            </div>
          )}
        </div>
      )}

      {selectedPanels.size > 0 && !report && (
        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg z-10">
          {showOptions && (
            <div className="max-w-7xl mx-auto px-4 pt-4 pb-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.report_title_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.title}
                  onChange={(e) => setReportOptions((o) => ({ ...o, title: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder={t('detail.report_title_placeholder')}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.description_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.description}
                  onChange={(e) => setReportOptions((o) => ({ ...o, description: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder={t('detail.description_placeholder')}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.template_label')}
                </label>
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="">{t('detail.template_none')}</option>
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.name}{tpl.is_default ? ' ★' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.time_from_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.time_range_from}
                  onChange={(e) => setReportOptions((o) => ({ ...o, time_range_from: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="now-6h"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.time_to_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.time_range_to}
                  onChange={(e) => setReportOptions((o) => ({ ...o, time_range_to: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="now"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.language_label')}
                </label>
                <select
                  value={reportOptions.language}
                  onChange={(e) => setReportOptions((o) => ({ ...o, language: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  {locales.map((code) => (
                    <option key={code} value={code}>
                      {FLAGS[code]} {t(`lang.${code}`)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sprint 5 PDF options */}
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.orientation_label')}
                </label>
                <select
                  value={reportOptions.orientation}
                  onChange={(e) => setReportOptions((o) => ({ ...o, orientation: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="portrait">{t('detail.orientation_portrait')}</option>
                  <option value="landscape">{t('detail.orientation_landscape')}</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.panel_columns_label')}
                </label>
                <select
                  value={reportOptions.panel_columns}
                  onChange={(e) => setReportOptions((o) => ({ ...o, panel_columns: Number(e.target.value) }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value={1}>1 {t('detail.column')}</option>
                  <option value={2}>2 {t('detail.columns')}</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.watermark_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.watermark_text}
                  onChange={(e) => setReportOptions((o) => ({ ...o, watermark_text: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder={t('detail.watermark_placeholder')}
                  maxLength={100}
                />
              </div>

              {/* Toggles row */}
              <div className="flex items-center space-x-6 col-span-full sm:col-span-1">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reportOptions.toc_enabled}
                    onChange={(e) => setReportOptions((o) => ({ ...o, toc_enabled: e.target.checked }))}
                    className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('detail.toc_label')}</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reportOptions.include_data_tables}
                    onChange={(e) => setReportOptions((o) => ({ ...o, include_data_tables: e.target.checked }))}
                    className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('detail.data_tables_label')}</span>
                </label>
              </div>

              {/* Comparison time range */}
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.comparison_from_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.comparison_time_from}
                  onChange={(e) => setReportOptions((o) => ({ ...o, comparison_time_from: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="now-7d"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                  {t('detail.comparison_to_label')}
                </label>
                <input
                  type="text"
                  value={reportOptions.comparison_time_to}
                  onChange={(e) => setReportOptions((o) => ({ ...o, comparison_time_to: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="now-6h"
                />
              </div>
            </div>
          )}
          <div className="max-w-7xl mx-auto flex items-center justify-between p-4">
            <span className="text-sm text-gray-600 dark:text-gray-300">
              {t('detail.panels_selected', { count: selectedPanels.size, plural })}
            </span>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowOptions(!showOptions)}
                className="text-sm text-primary-600 hover:text-primary-800 dark:text-primary-400 dark:hover:text-primary-300 font-medium"
              >
                {showOptions ? t('common.hide_options') : t('common.options')}
              </button>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-8 rounded-lg transition-colors disabled:opacity-50 text-base"
              >
                {generating ? t('detail.generating') : t('detail.generate_pdf')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
