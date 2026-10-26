import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { MarkGithubIcon } from '@primer/octicons-react'
import { useAuth } from '../auth'
import { NewPasswordField } from '../components'

const OAUTH_ERRORS = {
  denied: 'GitHub sign-in was cancelled.',
  state: 'That sign-in link expired. Try again.',
  github: "GitHub didn't confirm your account. Try again in a minute.",
  config: "GitHub sign-in isn't set up on this server yet.",
}

const NOTICES = {
  deleted: 'Your account and everything linked to it were deleted.',
}

// Full-page navigation, not fetch: the API redirects to GitHub and back.
const GithubButton = ({ children }) => (
  <a className="btn" href="/api/auth/github/start"><MarkGithubIcon size={16} />{children}</a>
)

export default function AuthPage({ mode }) {
  const signup = mode === 'signup'
  const { signIn, pendingGithub } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(OAUTH_ERRORS[params.get('error')] ?? null)
  const notice = params.get('deleted') ? NOTICES.deleted : null

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

  const errorText = error && <p className="error-text" role="alert">{error}</p>
  const noticeText = notice && <p className="success-text" role="status">{notice}</p>

  if (signup && !pendingGithub) {
    return (
      <main className="page">
        <div className="auth">
          <div className="auth-card">
            <div>
              <h1>Find your first PR</h1>
              <p className="lede">
                We read the packages in your public GitHub repos and show open issues in projects that use them.
                First, confirm your GitHub account. We only see your public profile.
              </p>
            </div>
            {errorText}
            <GithubButton>Continue with GitHub</GithubButton>
          </div>
          <p className="auth-switch">Already have an account? <Link to="/login">Log in</Link></p>
        </div>
      </main>
    )
  }

  return (
    <main className="page">
      <div className="auth">
        <form className="auth-card" onSubmit={onSubmit}>
          <div>
            <h1>{signup ? 'Almost done' : 'Log in to Starpull'}</h1>
            <p className="lede">
              {signup ? <>GitHub confirmed you as <strong>@{pendingGithub}</strong>. Add an email and password for logging in.</>
                : 'Pick up where you left off.'}
            </p>
          </div>
          {noticeText}
          {signup ? (
            <>
              <div className="field">
                <label htmlFor="email">Email</label>
                <input className="input" id="email" name="email" type="email" required autoComplete="email" spellCheck={false} />
              </div>
              <NewPasswordField id="password" name="password" label="Password" username={pendingGithub} />
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
          {errorText}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? (signup ? 'Importing your repos…' : 'Logging in…') : signup ? 'Create account' : 'Log in'}
          </button>
          {busy && signup && (
            <p className="progress-note" role="status">
              <MarkGithubIcon size={16} />
              Reading your public repos from GitHub. This takes about 20 seconds.
            </p>
          )}
          {!signup && (
            <>
              <p className="divider">or</p>
              <a className="btn secondary" href="/api/auth/github/start"><MarkGithubIcon size={16} />Log in with GitHub</a>
            </>
          )}
        </form>
        <p className="auth-switch">
          {signup ? <>Already have an account? <Link to="/login">Log in</Link></> : <>New here? <Link to="/signup">Create an account</Link></>}
        </p>
      </div>
    </main>
  )
}
