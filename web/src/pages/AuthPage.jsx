import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GitPullRequestIcon } from '@primer/octicons-react'
import { useAuth } from '../auth'

export default function AuthPage({ mode }) {
  const signup = mode === 'signup'
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const onSubmit = async (e) => {
    e.preventDefault()
    const form = Object.fromEntries(new FormData(e.currentTarget))
    setBusy(true)
    setError(null)
    try {
      await signIn(signup ? '/auth/signup' : '/auth/login', form)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <main className="page">
      <div className="auth">
        <form className="auth-card" onSubmit={onSubmit}>
          <div>
            <h1>{signup ? 'Find your first PR' : 'Log in to FirstPR'}</h1>
            <p className="lede">
              {signup
                ? "We read the packages in your public GitHub repos and show open issues in projects that use them."
                : 'Pick up where you left off.'}
            </p>
          </div>
          {signup ? (
            <>
              <div className="field">
                <label htmlFor="github_username">GitHub username</label>
                <input className="input" id="github_username" name="github_username" required autoComplete="username"
                  spellCheck={false} autoCapitalize="none" pattern="[A-Za-z0-9\-]+" placeholder="octocat" />
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input className="input" id="email" name="email" type="email" required autoComplete="email" spellCheck={false} />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input className="input" id="password" name="password" type="password" required minLength={8} maxLength={72}
                  autoComplete="new-password" aria-describedby="pw-hint" />
                <span className="hint" id="pw-hint">At least 8 characters.</span>
              </div>
            </>
          ) : (
            <>
              <div className="field">
                <label htmlFor="login">GitHub username or email</label>
                <input className="input" id="login" name="login" required autoComplete="username" spellCheck={false} autoCapitalize="none" />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input className="input" id="password" name="password" type="password" required autoComplete="current-password" />
              </div>
            </>
          )}
          {error && <p className="error-text" role="alert">{error}</p>}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? (signup ? 'Importing your repos…' : 'Logging in…') : signup ? 'Create account' : 'Log in'}
          </button>
          {busy && signup && (
            <p className="progress-note" role="status">
              <GitPullRequestIcon size={16} />
              Reading your public repos from GitHub. This takes about 20 seconds.
            </p>
          )}
        </form>
        <p className="auth-switch">
          {signup ? <>Already have an account? <Link to="/login">Log in</Link></> : <>New here? <Link to="/signup">Create an account</Link></>}
        </p>
      </div>
    </main>
  )
}
