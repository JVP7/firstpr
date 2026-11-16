import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PeopleIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useLoad } from '../useLoad'
import { Empty, ErrorState, Skeletons } from '../components'

function CreateTeam() {
  const navigate = useNavigate()
  const [state, setState] = useState({ busy: false, error: null })
  const onSubmit = async (e) => {
    e.preventDefault()
    setState({ busy: true, error: null })
    try {
      const team = await api('/teams', { method: 'POST', body: { name: new FormData(e.currentTarget).get('name').trim() } })
      navigate(`/teams/${team.team_id}`)
    } catch (err) {
      setState({ busy: false, error: err.message })
    }
  }
  return (
    <section className="section" aria-labelledby="new-team-h">
      <h2 id="new-team-h">New team</h2>
      <form className="inline-form" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="team-name">Team name</label>
        <input className="input" id="team-name" name="name" required maxLength={100} placeholder="e.g. CS 461 group" autoComplete="off" />
        <button className="btn secondary" type="submit" disabled={state.busy}>Create team</button>
      </form>
      {state.error && <p className="error-text" role="alert">{state.error}</p>}
    </section>
  )
}

export default function Teams() {
  const teams = useLoad(() => api('/teams'), [])
  return (
    <>
      <div className="page-head">
        <h1>Teams</h1>
        <p>Contribute with friends or classmates and see everyone's saved issues on one board.</p>
      </div>
      <div className="teams">
        <CreateTeam />
        {teams.loading ? (
          <Skeletons count={2} />
        ) : teams.error ? (
          <ErrorState error={teams.error} onRetry={teams.reload} />
        ) : teams.data.length === 0 ? (
          <Empty title="No teams yet">
            <p>Create one above, then add teammates by their GitHub username once they've signed up.</p>
          </Empty>
        ) : (
          <ul className="list">
            {teams.data.map((t) => (
              <li key={t.team_id} className="card">
                <Link className="card-title" to={`/teams/${t.team_id}`}>{t.name}</Link>
                <span className="repo-line">
                  <PeopleIcon size={14} />
                  {t.member_count} {t.member_count === 1 ? 'member' : 'members'} · {t.role === 'owner' ? 'Owner' : 'Member'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}
