import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrashIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useLoad } from '../useLoad'
import { Empty, ErrorState, Skeletons } from '../components'

const STATUSES = [
  ['interested', 'Interested'],
  ['working', 'Working'],
  ['pr_submitted', 'PR submitted'],
  ['merged', 'Merged'],
]

function SavedCard({ item, onChange, onError }) {
  const move = async (status) => {
    try {
      onChange(await api(`/saved/${item.issue_id}`, { method: 'PATCH', body: { status } }))
    } catch (err) {
      onError(err)
    }
  }
  const remove = async () => {
    try {
      await api(`/saved/${item.issue_id}`, { method: 'DELETE' })
      onChange({ issue_id: item.issue_id, removed: true })
    } catch (err) {
      onError(err)
    }
  }
  return (
    <li className="card">
      <span className="repo-line"><span className="name">{item.full_name}</span></span>
      <Link className="card-title" to={`/issues/${item.issue_id}`}>{item.title} <span className="num">#{item.number}</span></Link>
      <div className="card-actions">
        <label className="sr-only" htmlFor={`st-${item.issue_id}`}>Status</label>
        {/* The API can't move an issue back to "Interested", so it is only shown as the starting state. */}
        <select id={`st-${item.issue_id}`} className="select" value={item.status} onChange={(e) => move(e.target.value)}>
          {STATUSES.map(([value, label]) => (
            <option key={value} value={value} disabled={value === 'interested'}>{label}</option>
          ))}
        </select>
        <button className="btn quiet small" onClick={remove} aria-label={`Remove ${item.title}`}><TrashIcon size={14} /></button>
      </div>
    </li>
  )
}

export default function Saved() {
  const saved = useLoad(() => api('/saved'), [])
  const [tab, setTab] = useState('interested')
  const [error, setError] = useState(null)

  const onChange = (change) => {
    setError(null)
    saved.setData(change.removed
      ? saved.data.filter((s) => s.issue_id !== change.issue_id)
      : saved.data.map((s) => (s.issue_id === change.issue_id ? { ...s, status: change.status } : s)))
  }

  return (
    <>
      <div className="page-head">
        <h1>Saved issues</h1>
        <p>Move an issue along as you work on it.</p>
      </div>
      {saved.loading ? (
        <Skeletons count={2} />
      ) : saved.error ? (
        <ErrorState error={saved.error} onRetry={saved.reload} />
      ) : saved.data.length === 0 ? (
        <Empty title="Nothing saved yet">
          <p>Open an issue from your matches and press Save issue. It lands here so you can track it to a merged PR.</p>
          <Link className="btn secondary" to="/">See your matches</Link>
        </Empty>
      ) : (
        <>
          {error && <p className="error-text" role="alert" style={{ marginBottom: 12 }}>{error.message}</p>}
          <div className="tabs" role="tablist" aria-label="Status">
            {STATUSES.map(([value, label]) => (
              <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)}>
                {label} {saved.data.filter((s) => s.status === value).length}
              </button>
            ))}
          </div>
          <div className="board">
            {STATUSES.map(([value, label]) => {
              const items = saved.data.filter((s) => s.status === value)
              return (
                <section key={value} className="column" data-active={tab === value} aria-label={label}>
                  <h2><span>{label}</span><span>{items.length}</span></h2>
                  {items.length ? (
                    <ul className="list">{items.map((s) => <SavedCard key={s.issue_id} item={s} onChange={onChange} onError={setError} />)}</ul>
                  ) : (
                    <p className="empty-col">None yet</p>
                  )}
                </section>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}
