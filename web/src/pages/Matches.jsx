import { useState } from 'react'
import { Link } from 'react-router-dom'
import { XIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useLoad } from '../useLoad'
import { Empty, ErrorState, IssueCard, Skeletons } from '../components'

function AddSkill({ onAdded }) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState([])
  const [error, setError] = useState(null)

  const onChange = async (e) => {
    const q = e.target.value
    setQuery(q)
    setError(null)
    if (q.length >= 2) setOptions(await api(`/packages?q=${encodeURIComponent(q)}`).catch(() => []))
  }
  const onSubmit = async (e) => {
    e.preventDefault()
    const pkg = options.find((o) => o.name.toLowerCase() === query.trim().toLowerCase())
    if (!pkg) return setError(`We don't track a package called "${query}". Pick one from the list.`)
    try {
      await api('/me/skills', { method: 'POST', body: { package_id: pkg.package_id } })
      setQuery('')
      onAdded()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form onSubmit={onSubmit} className="field">
      <label htmlFor="skill">Add a package you know</label>
      <div className="add-skill">
        <input id="skill" className="input" list="pkg-options" value={query} onChange={onChange}
          placeholder="e.g. requests, react…" autoComplete="off" spellCheck={false} aria-invalid={!!error} aria-describedby="skill-err" />
        <datalist id="pkg-options">{options.map((o) => <option key={o.package_id} value={o.name}>{o.ecosystem}</option>)}</datalist>
        <button className="btn secondary" type="submit">Add</button>
      </div>
      {error && <span className="error-text" id="skill-err">{error}</span>}
    </form>
  )
}

function Stack({ me, onChange }) {
  const pkgCount = me.repos.reduce((n, r) => n + r.package_count, 0)
  const remove = async (id) => {
    await api(`/me/skills/${id}`, { method: 'DELETE' })
    onChange()
  }
  return (
    <section className="stack" aria-labelledby="stack-h">
      <h2 id="stack-h">Your stack</h2>
      <p>
        {me.repos.length
          ? `${pkgCount} packages found in ${me.repos.length} of your public repos${me.skills.length ? `, plus ${me.skills.length} you added` : ''}.`
          : 'No repos imported yet.'}
      </p>
      {me.skills.length > 0 && (
        <div className="chips">
          {me.skills.map((s) => (
            <span key={s.package_id} className="pkg chip-remove">
              {s.name}
              <button onClick={() => remove(s.package_id)} aria-label={`Remove ${s.name}`}><XIcon size={12} /></button>
            </span>
          ))}
        </div>
      )}
      <AddSkill onAdded={onChange} />
    </section>
  )
}

export default function Matches() {
  const { user, refresh } = useAuth()
  const matches = useLoad(() => api('/issues/matches'), [user])
  const hasPackages = user.repos.some((r) => r.package_count > 0) || user.skills.length > 0

  return (
    <>
      <div className="page-head">
        <h1>Issues that match your stack</h1>
        <p>Open, unassigned issues in projects that use the same packages you do. At most three per project.</p>
      </div>
      <Stack me={user} onChange={refresh} />
      {matches.loading ? (
        <Skeletons />
      ) : matches.error ? (
        <ErrorState error={matches.error} onRetry={matches.reload} />
      ) : !hasPackages ? (
        <Empty title="No packages to match yet">
          <p>We didn't find a requirements.txt, pyproject.toml or package.json in your public repos. Add a few packages you know above and matches show up here.</p>
        </Empty>
      ) : matches.data.length === 0 ? (
        <Empty title="No matching issues right now">
          <p>None of the projects we track use your packages yet. Add more packages above, or browse everything.</p>
          <Link className="btn secondary" to="/search?beginner=1">Browse beginner issues</Link>
        </Empty>
      ) : (
        <ul className="list">{matches.data.map((i) => <IssueCard key={i.issue_id} issue={i} />)}</ul>
      )}
    </>
  )
}
