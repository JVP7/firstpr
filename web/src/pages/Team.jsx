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
            {(m.user_id === me || isOwner) && (
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
        <Progress teamId={t.team_id} />
      </div>
    </>
  )
}
