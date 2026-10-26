import { useState } from 'react'
import { MarkGithubIcon, SyncIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useAuth } from '../auth'

// One small form state machine per section: idle -> busy -> done | error.
function useAction() {
  const [state, setState] = useState({ status: 'idle', message: null })
  const run = async (fn, doneMessage) => {
    setState({ status: 'busy', message: null })
    try {
      await fn()
      setState({ status: 'done', message: doneMessage })
      return true
    } catch (err) {
      setState({ status: 'error', message: err.message })
      return false
    }
  }
  return [state, run]
}

const Feedback = ({ state }) =>
  state.message && (
    <p className={state.status === 'error' ? 'error-text' : 'success-text'} role={state.status === 'error' ? 'alert' : 'status'}>
      {state.message}
    </p>
  )

function EmailSection({ user, onChanged }) {
  const [state, run] = useAction()
  const onSubmit = (e) => {
    e.preventDefault()
    const form = e.currentTarget
    const body = Object.fromEntries(new FormData(form))
    run(async () => {
      await api('/me', { method: 'PATCH', body })
      form.reset()
      await onChanged()
    }, 'Email updated.')
  }
  return (
    <section className="section" aria-labelledby="profile-h">
      <h2 id="profile-h">Profile</h2>
      <div className="field">
        <span className="hint">GitHub account</span>
        <span className="readonly"><MarkGithubIcon size={16} />@{user.github_username}</span>
        <p>Verified through GitHub sign-in, so it can't be edited here. To use another GitHub account, create a new Starpull account with it.</p>
      </div>
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input className="input" id="email" name="email" type="email" required autoComplete="email" spellCheck={false} />
          <span className="hint">Currently {user.email}</span>
        </div>
        <div className="field">
          <label htmlFor="email-pw">Current password</label>
          <input className="input" id="email-pw" name="current_password" type="password" required autoComplete="current-password" />
        </div>
        <Feedback state={state} />
        <button className="btn secondary" type="submit" disabled={state.status === 'busy'}>Update email</button>
      </form>
    </section>
  )
}

function PasswordSection() {
  const [state, run] = useAction()
  const onSubmit = (e) => {
    e.preventDefault()
    const form = e.currentTarget
    const body = Object.fromEntries(new FormData(form))
    run(async () => {
      await api('/me/password', { method: 'PATCH', body })
      form.reset()
    }, 'Password changed. Your other devices were signed out.')
  }
  return (
    <section className="section" aria-labelledby="pw-h">
      <h2 id="pw-h">Password</h2>
      <form onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="cur-pw">Current password</label>
          <input className="input" id="cur-pw" name="current_password" type="password" required autoComplete="current-password" />
        </div>
        <div className="field">
          <label htmlFor="new-pw">New password</label>
          <input className="input" id="new-pw" name="new_password" type="password" required minLength={8} maxLength={72}
            autoComplete="new-password" aria-describedby="new-pw-hint" />
          <span className="hint" id="new-pw-hint">At least 8 characters. Changing it signs out every other device.</span>
        </div>
        <Feedback state={state} />
        <button className="btn secondary" type="submit" disabled={state.status === 'busy'}>Change password</button>
      </form>
    </section>
  )
}

function ReposSection({ user, onChanged }) {
  const [state, run] = useAction()
  const refresh = () =>
    run(async () => {
      const res = await api('/me/sync', { method: 'POST' })
      await onChanged()
      return res
    }, 'Repos refreshed from GitHub.')
  return (
    <section className="section" aria-labelledby="repos-h">
      <h2 id="repos-h">Your repos</h2>
      <p>
        {user.repos.length
          ? `Starpull reads up to 20 of your most recently pushed public repos (skipping forks and archived ones) to find the packages you use. ${user.repos.length} are linked now.`
          : 'No repos linked yet. Starpull reads up to 20 of your most recently pushed public repos, skipping forks and archived ones.'}{' '}
        Refresh after you push something new.
      </p>
      {user.repos.length > 0 && (
        <ul className="repo-list">{user.repos.map((r) => <li key={r.repo_id}><code className="pkg plain">{r.full_name}</code></li>)}</ul>
      )}
      <Feedback state={state} />
      <div>
        <button className="btn secondary" onClick={refresh} disabled={state.status === 'busy'}>
          <SyncIcon size={16} />{state.status === 'busy' ? 'Reading GitHub… about 20 seconds' : 'Refresh from GitHub'}
        </button>
      </div>
    </section>
  )
}

function SessionsSection({ onSignedOut }) {
  const [state, run] = useAction()
  const endAll = () => run(async () => {
    await api('/me/sessions/end-all', { method: 'POST' })
    onSignedOut()
  })
  return (
    <section className="section" aria-labelledby="sessions-h">
      <h2 id="sessions-h">Sessions</h2>
      <p>Signed in on a shared or lost device? This signs you out everywhere, including here.</p>
      <Feedback state={state} />
      <div><button className="btn secondary" onClick={endAll} disabled={state.status === 'busy'}>Sign out everywhere</button></div>
    </section>
  )
}

function DangerZone({ user, onDeleted }) {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const [state, run] = useAction()
  const matches = typed.toLowerCase() === user.github_username.toLowerCase()

  const onSubmit = (e) => {
    e.preventDefault()
    const body = Object.fromEntries(new FormData(e.currentTarget))
    run(async () => {
      await api('/me', { method: 'DELETE', body })
      onDeleted()
    })
  }

  return (
    <section className="section danger" aria-labelledby="danger-h">
      <h2 id="danger-h">Danger zone</h2>
      <div className="danger-row">
        <div>
          <strong>Delete this account</strong>
          <p>Removes your account, linked repos, skills, saved issues and team memberships right away. This can't be undone.</p>
          <p>
            GitHub separately remembers that you approved Starpull. To remove that too, revoke Starpull under{' '}
            <a href="https://github.com/settings/applications" target="_blank" rel="noreferrer">GitHub → Settings → Applications</a>.
          </p>
        </div>
        {!open && <button className="btn destructive-outline" onClick={() => setOpen(true)}>Delete account</button>}
      </div>
      {open && (
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="confirm">Type <strong>{user.github_username}</strong> to confirm</label>
            <input className="input" id="confirm" name="confirm_username" required autoComplete="off" spellCheck={false}
              autoCapitalize="none" value={typed} onChange={(e) => setTyped(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="del-pw">Current password</label>
            <input className="input" id="del-pw" name="current_password" type="password" required autoComplete="current-password" />
          </div>
          <Feedback state={state} />
          <div className="actions">
            <button className="btn destructive" type="submit" disabled={!matches || state.status === 'busy'}>
              Delete my account permanently
            </button>
            <button className="btn quiet" type="button" onClick={() => { setOpen(false); setTyped('') }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}

export default function Account() {
  const { user, refresh } = useAuth()
  // A full page load after the session ends drops every bit of in-memory account state, and
  // keeps the ?deleted notice (a client-side redirect to /login would win the race and drop it).
  const leave = (path) => window.location.replace(path)
  return (
    <>
      <div className="page-head">
        <h1>Account settings</h1>
        <p>Manage how you sign in and what Starpull knows about you.</p>
      </div>
      <div className="settings">
        <EmailSection user={user} onChanged={refresh} />
        <PasswordSection />
        <ReposSection user={user} onChanged={refresh} />
        <SessionsSection onSignedOut={() => leave('/login')} />
        <DangerZone user={user} onDeleted={() => leave('/login?deleted=1')} />
      </div>
    </>
  )
}
