import { Link } from 'react-router-dom'
import { IssueOpenedIcon, StarIcon } from '@primer/octicons-react'

// GitHub linguist colors for the languages in the seed list.
const LANG_COLORS = { Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6', 'Jupyter Notebook': '#DA5B0B' }
const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })
const relative = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function timeAgo(iso) {
  const days = Math.round((new Date(iso) - Date.now()) / 86400000)
  if (Math.abs(days) < 1) return 'today'
  if (Math.abs(days) < 30) return relative.format(days, 'day')
  if (Math.abs(days) < 365) return relative.format(Math.round(days / 30), 'month')
  return relative.format(Math.round(days / 365), 'year')
}

export function RepoLine({ repo, language, stars }) {
  return (
    <div className="repo-line">
      {language && <span className="lang-dot" style={{ background: LANG_COLORS[language] ?? 'var(--muted)' }} title={language} />}
      <span className="name">{repo}</span>
      {stars != null && (
        <span className="meta" aria-label={`${stars} stars`}>
          <StarIcon size={14} />
          {compact.format(stars)}
        </span>
      )}
    </div>
  )
}

export function Labels({ labels, max = 3 }) {
  if (!labels?.length) return null
  return (
    <div className="labels">
      {labels.slice(0, max).map((l) => <span key={l} className="label">{l}</span>)}
      {labels.length > max && <span className="label">+{labels.length - max}</span>}
    </div>
  )
}

export function MatchLine({ shared, languageMatch }) {
  if (!shared?.length) return null
  return (
    <div className="match-line">
      <span>Uses {shared.length} of your packages:</span>
      {shared.slice(0, 3).map((p) => <code key={p} className="pkg">{p}</code>)}
      {shared.length > 3 && <span>+{shared.length - 3}</span>}
      {languageMatch && <span className="same-lang">Same language as your repos</span>}
    </div>
  )
}

export function IssueCard({ issue }) {
  return (
    <li className="card">
      <RepoLine repo={issue.full_name} language={issue.primary_language} stars={issue.stars} />
      <Link className="card-title" to={`/issues/${issue.issue_id}`} state={{ shared: issue.shared_packages }}>
        {issue.title} <span className="num">#{issue.number}</span>
      </Link>
      <Labels labels={issue.labels} />
      <MatchLine shared={issue.shared_packages} languageMatch={issue.language_match} />
    </li>
  )
}

export function Skeletons({ count = 4 }) {
  return (
    <div className="list" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton">
          <i style={{ width: '30%' }} />
          <i style={{ width: '80%', height: 16 }} />
          <i style={{ width: '45%' }} />
        </div>
      ))}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="empty" role="alert">
      <h2>Couldn't load this</h2>
      <p>{error.message}</p>
      {onRetry && <button className="btn secondary" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <IssueOpenedIcon size={20} className="muted" />
      <h2>{title}</h2>
      {children}
    </div>
  )
}
