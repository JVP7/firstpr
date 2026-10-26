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
import Account from './pages/Account'
import Privacy from './pages/Privacy'
import './styles.css'

const REPO = 'https://github.com/JVP7/firstpr'

function Footer() {
  const { user } = useAuth()
  return (
    <footer className="footer">
      <div className="footer-inner">
        <nav aria-label="Footer" className="footer-links">
          {user && (
            <>
              <Link to="/">Matches</Link>
              <Link to="/search">Search</Link>
              <Link to="/saved">Saved</Link>
              <Link to="/account">Account settings</Link>
            </>
          )}
          <Link to="/privacy">Privacy &amp; security</Link>
          <a href={REPO} target="_blank" rel="noreferrer">Source code</a>
          <a href={`${REPO}/issues/new`} target="_blank" rel="noreferrer">Report a problem</a>
        </nav>
        <p className="footer-note">Starpull · open issues in projects that use your packages · formerly FirstPR</p>
      </div>
    </footer>
  )
}

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
            <Link to="/account" className="who">@{user.github_username}</Link>
            <button className="btn quiet small" onClick={signOut}>Log out</button>
          </div>
        </div>
      </header>
      <main id="main" className="page"><Outlet /></main>
      <Footer />
    </>
  )
}

function PublicOnly({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return null
  return user ? <Navigate to="/" replace /> : <>{children}<Footer /></>
}

// Readable whether or not you're logged in, so people can check it before signing up.
function OpenPage({ children }) {
  const { ready } = useAuth()
  if (!ready) return null
  return (
    <>
      <header className="nav">
        <div className="nav-inner">
          <Link to="/" className="wordmark"><GitPullRequestIcon size={18} />Starpull</Link>
        </div>
      </header>
      <main id="main" className="page">{children}</main>
      <Footer />
    </>
  )
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
            <Route path="account" element={<Account />} />
          </Route>
          <Route path="/privacy" element={<OpenPage><Privacy /></OpenPage>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
