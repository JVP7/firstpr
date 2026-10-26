import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!getToken())

  useEffect(() => {
    if (getToken()) api('/me').then(setUser, () => setToken(null)).finally(() => setReady(true))
    const onLogout = () => setUser(null)
    window.addEventListener('firstpr:logout', onLogout)
    return () => window.removeEventListener('firstpr:logout', onLogout)
  }, [])

  const signIn = async (path, body) => {
    const res = await api(path, { method: 'POST', body })
    setToken(res.token)
    setUser(await api('/me'))
    return res
  }
  const signOut = () => {
    setToken(null)
    setUser(null)
  }
  const refresh = async () => setUser(await api('/me'))

  return <AuthContext.Provider value={{ user, ready, signIn, signOut, refresh }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
