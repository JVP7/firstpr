import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, NavLink, Link, Outlet, Route, Routes } from 'react-router-dom'
import { GitPullRequestIcon } from '@primer/octicons-react'
import { AuthProvider, useAuth } from './auth'
import Stars from './Stars'
import AuthPage from './pages/AuthPage'
import Matches from './pages/Matches'
import Search from './pages/Search'
import IssueDetail from './pages/IssueDetail'
import Saved from './pages/Saved'
import './styles.css'

function Shell() {
  const { user, ready, signOut } = useAuth()
  if (!ready) return null
  if (!user) return <Navigate to="/login" replace />
  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="nav">
        <div className="nav-inner">
          <Link to="/" className="wordmark"><GitPullRequestIcon size={18} />Starpull</Link>
          <nav className="nav-links" aria-label="Main">
            <NavLink to="/" end>Matches</NavLink>
            <NavLink to="/search">Search</NavLink>
            <NavLink to="/saved">Saved</NavLink>
          </nav>
          <div className="nav-user">
            <span className="who">@{user.github_username}</span>
            <button className="btn quiet small" onClick={signOut}>Log out</button>
          </div>
        </div>
      </header>
      <main id="main" className="page"><Outlet /></main>
    </>
  )
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return null
  return user ? <Navigate to="/" replace /> : children
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Stars />
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicOnly><AuthPage mode="login" /></PublicOnly>} />
          <Route path="/signup" element={<PublicOnly><AuthPage mode="signup" /></PublicOnly>} />
          <Route element={<Shell />}>
            <Route index element={<Matches />} />
            <Route path="search" element={<Search />} />
            <Route path="issues/:issueId" element={<IssueDetail />} />
            <Route path="saved" element={<Saved />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
