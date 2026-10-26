// Same-origin path: Vite proxies /api in dev and Vercel rewrites it in prod, so the session
// cookie is first-party and the API needs no CORS.
const BASE = '/api'

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body && JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, "Can't reach the FirstPR server. Check your connection and try again.")
  }
  if (res.status === 401) window.dispatchEvent(new Event('firstpr:logout'))
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : detail?.[0]?.msg ?? `Request failed (${res.status})`
    throw new ApiError(res.status, message)
  }
  return data
}
