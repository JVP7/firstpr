const BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'firstpr.token'

// shortcut: token in localStorage is readable by any XSS on this origin; move to an httpOnly cookie before real users.
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let res
  try {
    res = await fetch(BASE + path, { method, headers, body: body && JSON.stringify(body) })
  } catch {
    throw new ApiError(0, "Can't reach the FirstPR server. Check your connection and try again.")
  }
  if (res.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event('firstpr:logout'))
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : detail?.[0]?.msg ?? `Request failed (${res.status})`
    throw new ApiError(res.status, message)
  }
  return data
}
