import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon, BookmarkIcon, CheckIcon, LinkExternalIcon } from '@primer/octicons-react'
import { api } from '../api'
import { useLoad } from '../useLoad'
import { ErrorState, Labels, RepoLine, Skeletons, timeAgo } from '../components'

const MAINTAINER = new Set(['OWNER', 'MEMBER', 'COLLABORATOR'])
const percent = (rate) => `${Math.round(rate * 100)}%`
const duration = (hours) => (hours < 48 ? `${Math.max(1, Math.round(hours))} hours` : `${Math.round(hours / 24)} days`)

function paceSummary(i) {
  if (i.responsiveness == null) return 'Not enough activity in the last 90 days to judge how quickly maintainers respond.'
  const parts = []
  if (i.reply_rate != null) {
    parts.push(`replied to ${percent(i.reply_rate)} of new issues` +
      (i.median_reply_hours != null ? ` (typically within ${duration(i.median_reply_hours)})` : ''))
  }
  if (i.merge_rate != null) parts.push(`merged ${percent(i.merge_rate)} of outside pull requests`)
  const rank = i.responsiveness >= 0.5
    ? `more responsive than ${percent(i.responsiveness)}`
    : `less responsive than ${percent(1 - i.responsiveness)}`
  return `In the last 90 days, maintainers ${parts.join(' and ')}. That's ${rank} of the projects Starpull tracks.`
}

export default function IssueDetail() {
  const { issueId } = useParams()
  const navigate = useNavigate()
  const shared = new Set(useLocation().state?.shared ?? [])
  const issue = useLoad(() => api(`/issues/${issueId}`), [issueId])
  const [saved, setSaved] = useState(null) // null | 'saving' | 'saved' | error message

  const save = async () => {
    setSaved('saving')
    try {
      await api('/saved', { method: 'POST', body: { issue_id: Number(issueId) } })
      setSaved('saved')
    } catch (err) {
      setSaved(err.status === 409 ? 'saved' : err.message)
    }
  }

  if (issue.loading) return <Skeletons count={2} />
  if (issue.error) return <ErrorState error={issue.error} onRetry={issue.reload} />
  const i = issue.data
  const maintainerReplies = i.comments.filter((c) => MAINTAINER.has(c.author_association)).length
  const packages = [...i.repo_packages].sort((a, b) => shared.has(b) - shared.has(a))

  return (
    <article className="detail">
      <button className="back btn quiet" onClick={() => navigate(-1)}><ArrowLeftIcon size={16} />Back</button>
      <div style={{ display: 'grid', gap: 10 }}>
        <RepoLine repo={i.full_name} language={i.primary_language} stars={i.stars} pace={i.responsiveness} />
        <h1>{i.title} <span className="muted" style={{ fontWeight: 400 }}>#{i.number}</span></h1>
        <p className="muted" style={{ fontSize: 14 }}>Opened {timeAgo(i.created_at)} · {i.is_assigned ? 'Assigned' : 'Nobody assigned'}</p>
        <Labels labels={i.labels} max={10} />
      </div>
      <div className="actions">
        {saved === 'saved' ? (
          <Link className="btn secondary" to="/saved"><CheckIcon size={16} />Saved. Open your board</Link>
        ) : (
          <button className="btn" onClick={save} disabled={saved === 'saving'}><BookmarkIcon size={16} />Save issue</button>
        )}
        <a className="btn secondary" href={i.url} target="_blank" rel="noreferrer"><LinkExternalIcon size={16} />Open on GitHub</a>
        {saved && !['saving', 'saved'].includes(saved) && <span className="error-text" role="alert">{saved}</span>}
      </div>
      <section className="section" aria-labelledby="pk-h">
        <h2 id="pk-h">{shared.size ? `Uses ${shared.size} of your packages` : 'Packages this project uses'}</h2>
        {packages.length ? (
          <div className="chips">
            {packages.slice(0, 40).map((p) => <code key={p} className={shared.has(p) ? 'pkg' : 'pkg plain'}>{p}</code>)}
            {packages.length > 40 && <span className="muted" style={{ fontSize: 13 }}>+{packages.length - 40} more</span>}
          </div>
        ) : (
          <p className="muted" style={{ fontSize: 14 }}>No requirements.txt, pyproject.toml, package.json, go.mod or Cargo.toml at the repo root.</p>
        )}
      </section>
      <section className="section" aria-labelledby="act-h">
        <h2 id="act-h">Recent activity</h2>
        <p style={{ fontSize: 14 }}>{paceSummary(i)}</p>
        {i.comments.length ? (
          <>
            <p className="muted" style={{ fontSize: 14 }}>
              {i.comments.length} comments in the last 90 days, {maintainerReplies} from maintainers.
            </p>
            <ul className="timeline">
              {i.comments.slice(-10).map((c, n) => (
                <li key={n}>
                  <strong>{c.author_login ?? 'deleted user'}</strong>
                  {MAINTAINER.has(c.author_association) && <span className="role">Maintainer</span>}
                  <span className="muted">commented {timeAgo(c.created_at)}</span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="muted" style={{ fontSize: 14 }}>No comments in the last 90 days. Leave one on GitHub before you start, so the maintainers know.</p>
        )}
      </section>
    </article>
  )
}
