import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [pendingGithub, setPendingGithub] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    // The session lives in an httpOnly cookie, so asking /me is the only way to know who is logged in.
    api('/auth/session')
      .then((s) => {
        setPendingGithub(s.pending_github)
        return s.user ? api('/me') : null
      })
      .then(setUser, () => setUser(null))
      .finally(() => setReady(true))
    const onLogout = () => setUser(null)
    window.addEventListener('firstpr:logout', onLogout)
    return () => window.removeEventListener('firstpr:logout', onLogout)
  }, [])

  const signIn = async (path, body) => {
    const res = await api(path, { method: 'POST', body })
    setUser(await api('/me'))
    return res
  }
  const signOut = async () => {
    await api('/auth/logout', { method: 'POST' }).catch(() => {})
    setUser(null)
  }
  const refresh = async () => setUser(await api('/me'))

  return <AuthContext.Provider value={{ user, pendingGithub, ready, signIn, signOut, refresh }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
