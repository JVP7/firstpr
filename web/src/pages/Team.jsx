import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useLoad } from '../useLoad'
import { ErrorState, Skeletons } from '../components'
import { STATUSES } from './Saved'

function Members({ team, me, isOwner, onChanged, onLeft }) {
  const [error, setError] = useState(null)
  const act = async (fn) => {
    setError(null)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    }
  }
  const add = (e) => {
    e.preventDefault()
    const form = e.currentTarget
    act(async () => {
      await api(`/teams/${team.team_id}/members`, { method: 'POST', body: { github_username: new FormData(form).get('github_username').trim() } })
      form.reset()
      onChanged()
    })
  }
  const remove = (m) => act(async () => {
    await api(`/teams/${team.team_id}/members/${m.user_id}`, { method: 'DELETE' })
    m.user_id === me ? onLeft() : onChanged()
  })

  return (
    <section className="section" aria-labelledby="members-h">
      <h2 id="members-h">Members</h2>
      <ul className="members">
        {team.members.map((m) => (
          <li key={m.user_id}>
            <strong>@{m.github_username}</strong>
            {m.role === 'owner' && <span className="role">Owner</span>}
            {/* Owners delete the team instead of leaving, so a team is never left without an owner. */}
            {(m.user_id === me ? m.role !== 'owner' : isOwner) && (
              <button className="btn quiet small" onClick={() => remove(m)}>
                {m.user_id === me ? 'Leave team' : 'Remove'}
              </button>
            )}
          </li>
        ))}
      </ul>
      {isOwner && (
        <form className="inline-form" onSubmit={add}>
          <label className="sr-only" htmlFor="member">GitHub username</label>
          <input className="input" id="member" name="github_username" required maxLength={39} placeholder="GitHub username"
            autoComplete="off" autoCapitalize="none" spellCheck={false} />
          <button className="btn secondary" type="submit">Add</button>
        </form>
      )}
      {error && <p className="error-text" role="alert">{error}</p>}
    </section>
  )
}

function Progress({ teamId }) {
  const saved = useLoad(() => api(`/teams/${teamId}/saved`), [teamId])
  const [tab, setTab] = useState('interested')
  if (saved.loading) return <Skeletons count={1} />
  if (saved.error) return <ErrorState error={saved.error} onRetry={saved.reload} />
  // The query returns only statuses someone has used; fill in the rest as empty columns.
  const byStatus = Object.fromEntries(saved.data.map((g) => [g.status, g.issues]))

  return (
    <section aria-labelledby="progress-h" style={{ display: 'grid', gap: 12 }}>
      <h2 id="progress-h" style={{ fontSize: 16 }}>Team progress</h2>
      {saved.data.length === 0 && (
        <p className="muted" style={{ fontSize: 14 }}>Nobody on the team has saved an issue yet. Issues members save show up here.</p>
      )}
      <div className="tabs" role="tablist" aria-label="Status">
        {STATUSES.map(([value, label]) => (
          <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>
            {label} {byStatus[value]?.length ?? 0}
          </button>
        ))}
      </div>
      <div className="board">
        {STATUSES.map(([value, label]) => {
          const items = byStatus[value] ?? []
          return (
            <section key={value} className="column" data-active={tab === value} aria-label={label}>
              <h3><span>{label}</span><span>{items.length}</span></h3>
              {items.length ? (
                <ul className="list">
                  {items.map((it) => (
                    <li key={`${it.user_id}-${it.issue_id}`} className="card">
                      <span className="repo-line"><span className="name">{it.repo}</span></span>
                      <Link className="card-title" to={`/issues/${it.issue_id}`}>{it.title} <span className="num">#{it.number}</span></Link>
                      <span className="repo-line">@{it.github_username}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="empty-col">None yet</p>
              )}
            </section>
          )
        })}
      </div>
    </section>
  )
}

function Target({ team, isOwner, onChanged }) {
  const [state, setState] = useState({ busy: false, error: null })
  const onSubmit = async (e) => {
    e.preventDefault()
    setState({ busy: true, error: null })
    try {
      const fullName = new FormData(e.currentTarget).get('full_name').trim()
      await api(`/teams/${team.team_id}/target`, { method: 'PUT', body: { full_name: fullName || null } })
      setState({ busy: false, error: null })
      onChanged()
    } catch (err) {
      setState({ busy: false, error: err.message })
    }
  }
  return (
    <section className="section" aria-labelledby="target-h">
      <h2 id="target-h">Target project</h2>
      <p>
        {team.target_repo
          ? <>The team is contributing to <Link to={`/search?q=${encodeURIComponent(team.target_repo)}`}><strong>{team.target_repo}</strong></Link>.</>
          : 'No project picked yet. Pick one to split its open issues across the team.'}
      </p>
      {isOwner && (
        <form className="inline-form" onSubmit={onSubmit}>
          <label className="sr-only" htmlFor="target">Repo (owner/name)</label>
          <input className="input" id="target" name="full_name" key={team.target_repo} defaultValue={team.target_repo ?? ''}
            placeholder="owner/name, e.g. pallets/flask" autoComplete="off" autoCapitalize="none" spellCheck={false} />
          <button className="btn secondary" type="submit" disabled={state.busy}>Save</button>
        </form>
      )}
      {state.error && <p className="error-text" role="alert">{state.error}</p>}
    </section>
  )
}

function DeleteTeam({ team, onDeleted }) {
  const [open, setOpen] = useState(false)
  const [typed, setTyped] = useState('')
  const [state, setState] = useState({ busy: false, error: null })
  const onSubmit = async (e) => {
    e.preventDefault()
    setState({ busy: true, error: null })
    try {
      await api(`/teams/${team.team_id}`, { method: 'DELETE' })
      onDeleted()
    } catch (err) {
      setState({ busy: false, error: err.message })
    }
  }
  return (
    <section className="section danger" aria-labelledby="del-team-h">
      <h2 id="del-team-h">Danger zone</h2>
      <div className="danger-row">
        <div>
          <strong>Delete this team</strong>
          <p>Removes the team and its member list for everyone. Members keep their own saved issues.</p>
        </div>
        {!open && <button className="btn destructive-outline" onClick={() => setOpen(true)}>Delete team</button>}
      </div>
      {open && (
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, maxWidth: 420 }}>
          <div className="field">
            <label htmlFor="confirm-team">Type <strong>{team.name}</strong> to confirm</label>
            <input className="input" id="confirm-team" required autoComplete="off" spellCheck={false}
              value={typed} onChange={(e) => setTyped(e.target.value)} />
          </div>
          {state.error && <p className="error-text" role="alert">{state.error}</p>}
          <div className="actions">
            <button className="btn destructive" type="submit" disabled={typed !== team.name || state.busy}>Delete team permanently</button>
            <button className="btn quiet" type="button" onClick={() => { setOpen(false); setTyped('') }}>Cancel</button>
          </div>
        </form>
      )}
    </section>
  )
}

export default function Team() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const team = useLoad(() => api(`/teams/${teamId}`), [teamId])

  if (team.loading) return <Skeletons count={2} />
  if (team.error) return <ErrorState error={team.error} onRetry={team.reload} />
  const t = team.data
  const isOwner = t.members.some((m) => m.user_id === user.user_id && m.role === 'owner')

  return (
    <>
      <Link className="back btn quiet" to="/teams" style={{ marginBottom: 8 }}><ArrowLeftIcon size={16} />All teams</Link>
      <div className="page-head">
        <h1>{t.name}</h1>
      </div>
      <div className="teams">
        <Members team={t} me={user.user_id} isOwner={isOwner} onChanged={team.reload} onLeft={() => navigate('/teams')} />
        <Target team={t} isOwner={isOwner} onChanged={team.reload} />
        <Progress teamId={t.team_id} />
        {isOwner && <DeleteTeam team={t} onDeleted={() => navigate('/teams')} />}
      </div>
    </>
  )
}
