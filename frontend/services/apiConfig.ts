import axios from 'axios'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json; charset=utf-8',
  },
})

export default apiClient
