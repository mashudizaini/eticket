import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const authAPI = {
  login: (username, password) => api.post('/auth/login', { username, password }),
}

// Dashboard
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getUsers: () => api.get('/dashboard/users'),
}

// Tickets
export const ticketsAPI = {
  getAll: (params) => api.get('/tickets/', { params }),
  getOne: (id) => api.get(`/tickets/${id}`),
  create: (data) => {
    const formData = new FormData()
    Object.keys(data).forEach(key => {
      if (key === 'files') {
        data.files.forEach(file => formData.append('files', file))
      } else {
        formData.append(key, data[key])
      }
    })
    return api.post('/tickets/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  update: (id, data) => api.patch(`/tickets/${id}`, data),
  assign: (id, data) => api.patch(`/tickets/${id}/assign`, data),
  finish: (id, data) => api.patch(`/tickets/${id}/resolve`, data),
  cancel: (id, data) => api.patch(`/tickets/${id}/cancel`, data),
  getTimeline: (id) => api.get(`/tickets/${id}/timeline`),
  getTeams: () => api.get('/tickets/teams'),
  getMyTeam: () => api.get('/tickets/my-team'),
  close: (id) => api.patch(`/tickets/${id}/close`),
  postpone: (id, data) => api.patch(`/tickets/${id}/postpone`, data),
}

export default api
