import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useLoad } from '../useLoad'
import { ErrorState, Skeletons } from '../components'

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
      </div>
    </>
  )
}
