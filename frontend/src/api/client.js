import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client

export const loginAPI = (username, password) => {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  return client.post('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export const getMeAPI = () => client.get('/auth/me')

export const getDashboardsAPI = (search = '') => {
  const params = search ? { search } : {}
  return client.get('/grafana/dashboards', { params })
}

export const getDashboardDetailAPI = (uid) =>
  client.get(`/grafana/dashboards/${uid}`)

export const generateReportAPI = (data) =>
  client.post('/reports/generate', data)

export const getReportsAPI = (page = 1, perPage = 20, status = null) => {
  const params = { page, per_page: perPage }
  if (status) params.status = status
  return client.get('/reports', { params })
}

export const getReportAPI = (id) => client.get(`/reports/${id}`)

export const downloadReportAPI = (id) =>
  client.get(`/reports/${id}/download`, { responseType: 'blob' })

export const deleteReportAPI = (id) =>
  client.delete(`/reports/${id}`)

export const registerAPI = (data) =>
  client.post('/auth/register', data)

// --- Templates ---
export const getTemplatesAPI = () =>
  client.get('/templates')

export const getTemplateAPI = (id) =>
  client.get(`/templates/${id}`)

export const createTemplateAPI = (data) =>
  client.post('/templates', data)

export const updateTemplateAPI = (id, data) =>
  client.put(`/templates/${id}`, data)

export const deleteTemplateAPI = (id) =>
  client.delete(`/templates/${id}`)

export const uploadTemplatePDFAPI = (id, data) =>
  client.post(`/templates/${id}/upload-pdf`, data)

export const uploadTemplatePDFFileAPI = (id, file) => {
  const formData = new FormData()
  formData.append('file', file)
  return client.post(`/templates/${id}/upload-pdf-file`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export const removeTemplatePDFAPI = (id) =>
  client.delete(`/templates/${id}/base-pdf`)
