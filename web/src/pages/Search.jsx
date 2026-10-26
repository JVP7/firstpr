import { useSearchParams } from 'react-router-dom'
import { SearchIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useLoad } from '../useLoad'
import { Empty, ErrorState, IssueCard, Skeletons } from '../components'

export default function Search() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const language = params.get('language') ?? ''
  const beginner = params.get('beginner') === '1'
  const results = useLoad(
    () => api(`/issues/search?${new URLSearchParams({ q, language, beginner_only: beginner, limit: 50 })}`),
    [q, language, beginner],
  )

  const update = (changes) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) v ? next.set(k, v) : next.delete(k)
    setParams(next)
  }
  const onSubmit = (e) => {
    e.preventDefault()
    update({ q: new FormData(e.currentTarget).get('q').trim() })
  }

  return (
    <>
      <div className="page-head">
        <h1>Search issues</h1>
        <p>Every open, unassigned issue across the 300 projects we track, newest first.</p>
      </div>
      <form className="search-form" onSubmit={onSubmit} role="search">
        <div className="field">
          <label htmlFor="q">Title or project</label>
          <input id="q" name="q" className="input" type="search" defaultValue={q} key={q} placeholder="e.g. docs, flask, typo…" spellCheck={false} />
        </div>
        <div className="field">
          <label htmlFor="language">Language</label>
          <select id="language" className="select" value={language} onChange={(e) => update({ language: e.target.value })}>
            <option value="">Any</option>
            <option>Python</option>
            <option>JavaScript</option>
            <option>TypeScript</option>
          </select>
        </div>
        <button className="btn" type="submit"><SearchIcon size={16} />Search</button>
      </form>
      <div className="search-options">
        <label className="check">
          <input type="checkbox" checked={beginner} onChange={(e) => update({ beginner: e.target.checked ? '1' : '' })} />
          Only issues with a beginner label (good first issue, help wanted…)
        </label>
        {results.data && <span role="status">{results.data.length === 50 ? 'Showing the newest 50' : `${results.data.length} issues`}</span>}
      </div>
      {results.loading ? (
        <Skeletons />
      ) : results.error ? (
        <ErrorState error={results.error} onRetry={results.reload} />
      ) : results.data.length === 0 ? (
        <Empty title="No issues match">
          <p>Try a shorter word, another language, or turn off the beginner filter.</p>
        </Empty>
      ) : (
        <ul className="list">{results.data.map((i) => <IssueCard key={i.issue_id} issue={i} />)}</ul>
      )}
    </>
  )
}
