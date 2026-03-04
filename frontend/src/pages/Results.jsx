import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysis, VERDICT_META, isTerminal } from '../api'

const POLL_INTERVAL_MS = 3000

/* ── Circular score gauge ─────────────────────────────────── */
function ScoreGauge({ score, verdict }) {
  const meta = VERDICT_META[verdict] || VERDICT_META['UNCERTAIN']
  const radius = 72
  const circumference = 2 * Math.PI * radius
  const fill = score != null ? (score / 100) * circumference : 0

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="180" height="180" viewBox="0 0 180 180" className="rotate-[-90deg]">
        {/* Track */}
        <circle cx="90" cy="90" r={radius} fill="none" stroke="#1E293B" strokeWidth="14" />
        {/* Score arc */}
        <circle
          cx="90" cy="90" r={radius}
          fill="none"
          stroke={meta.color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circumference}`}
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
      </svg>
      {/* Centred label (undo rotation) */}
      <div className="absolute flex flex-col items-center pointer-events-none"
           style={{ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
        <span className="text-4xl font-bold text-white">{score ?? '—'}</span>
        <span className="text-xs text-satya-muted">/100</span>
      </div>
    </div>
  )
}

/* ── Radial gauge wrapper ─────────────────────────────────── */
function GaugeCard({ score, verdict, confidence }) {
  const meta = VERDICT_META[verdict] || {}
  const radius = 72
  const circumference = 2 * Math.PI * radius
  const fill = score != null ? (score / 100) * circumference : 0

  return (
    <div className="card flex flex-col items-center py-8">
      <div className="relative" style={{ width: 180, height: 180 }}>
        <svg width="180" height="180" viewBox="0 0 180 180"
             style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="90" cy="90" r={radius} fill="none" stroke="#1E293B" strokeWidth="14" />
          <circle
            cx="90" cy="90" r={radius}
            fill="none" stroke={meta.color || '#94A3B8'}
            strokeWidth="14" strokeLinecap="round"
            strokeDasharray={`${fill} ${circumference}`}
            style={{ transition: 'stroke-dasharray 1s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white">{score ?? '—'}</span>
          <span className="text-xs text-satya-muted">/100</span>
        </div>
      </div>

      {verdict && (
        <div className={`mt-4 px-4 py-1.5 rounded-full border text-sm font-semibold
                        ${meta.bg} ${meta.border} ${meta.text}`}>
          {meta.label}
        </div>
      )}
      {confidence && (
        <p className="text-xs text-satya-muted mt-2">Confidence: {confidence}</p>
      )}
    </div>
  )
}

/* ── Sub-score bar ────────────────────────────────────────── */
function SubScoreBar({ label, score, icon }) {
  const pct = score != null ? score : 0
  const color =
    score == null   ? 'bg-slate-600' :
    score >= 85     ? 'bg-green-500' :
    score >= 70     ? 'bg-yellow-500' :
    score >= 50     ? 'bg-orange-500' :
                      'bg-red-500'

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-300 flex items-center gap-1.5">
          <span>{icon}</span>{label}
        </span>
        <span className="text-sm font-semibold text-white">
          {score != null ? `${score}/100` : 'N/A'}
        </span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

/* ── Finding row ──────────────────────────────────────────── */
const SEVERITY_STYLE = {
  HIGH:   'bg-red-900/40 text-red-400 border-red-800',
  MEDIUM: 'bg-orange-900/40 text-orange-400 border-orange-800',
  INFO:   'bg-slate-700/40 text-slate-400 border-slate-600',
}

function FindingRow({ finding }) {
  const [open, setOpen] = useState(false)
  const sev = finding.severity || 'INFO'
  const sevCls = SEVERITY_STYLE[sev] || SEVERITY_STYLE['INFO']

  return (
    <button
      onClick={() => setOpen(o => !o)}
      className="w-full text-left card py-3 hover:border-slate-500 transition-colors"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border whitespace-nowrap ${sevCls}`}>
            {sev}
          </span>
          <span className="text-sm text-white truncate">{finding.signal?.replace(/_/g, ' ')}</span>
        </div>
        <span className="text-satya-muted text-xs flex-shrink-0">{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <p className="mt-2 text-xs text-satya-muted pl-1 text-left">{finding.detail}</p>
      )}
    </button>
  )
}

/* ── Status banner while processing ──────────────────────── */
const STATUS_LABEL = {
  queued:     { label: 'Queued — waiting for a worker…',   pct: 5  },
  processing: { label: 'Processing — analysing content…',  pct: 40 },
  ingesting:  { label: 'Ingesting video from platform…',   pct: 20 },
  scoring:    { label: 'Computing SATYA score…',           pct: 80 },
  failed:     { label: 'Analysis failed',                  pct: 0  },
}

function ProcessingBanner({ status }) {
  const info = STATUS_LABEL[status] || { label: status, pct: 10 }
  return (
    <div className="card py-10 flex flex-col items-center gap-5">
      {status !== 'failed' && (
        <div className="w-10 h-10 border-4 border-blue-400/30 border-t-blue-400
                         rounded-full animate-spin" />
      )}
      <p className="text-sm text-satya-muted">{info.label}</p>
      {status !== 'failed' && (
        <div className="w-64 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${info.pct}%` }}
          />
        </div>
      )}
      <p className="text-xs text-slate-600">Polling every 3 s…</p>
    </div>
  )
}


/* ── Main Results page ────────────────────────────────────── */
export default function Results() {
  const { analysisId } = useParams()
  const [data, setData] = useState(null)
  const [fetchError, setFetchError] = useState('')
  const timerRef = useRef(null)

  const poll = useCallback(async () => {
    try {
      const result = await getAnalysis(analysisId)
      setData(result)
      if (!isTerminal(result.status)) {
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
      }
    } catch (err) {
      setFetchError(err.message)
    }
  }, [analysisId])

  useEffect(() => {
    poll()
    return () => clearTimeout(timerRef.current)
  }, [poll])

  const done = data && isTerminal(data.status)
  const failed = data?.status === 'failed'

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-satya-border px-6 py-4 flex items-center gap-4">
        <Link to="/" className="text-satya-muted hover:text-white text-sm transition-colors">
          ← Back
        </Link>
        <span className="text-white font-semibold">Analysis Results</span>
        <span className="ml-auto text-xs text-satya-muted font-mono">{analysisId}</span>
      </nav>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-8 space-y-6">
        {/* Fetch error */}
        {fetchError && (
          <div className="card border-red-700 bg-red-900/20">
            <p className="text-sm text-red-400">Error: {fetchError}</p>
            <p className="text-xs text-satya-muted mt-1">Make sure the API is running on :8000</p>
          </div>
        )}

        {/* Content URL */}
        {data?.content_url && (
          <div className="flex items-center gap-2 text-sm text-satya-muted">
            <span>Analysing:</span>
            <a href={data.content_url} target="_blank" rel="noopener noreferrer"
               className="text-blue-400 hover:underline truncate max-w-xs">
              {data.content_url}
            </a>
            {data.platform && (
              <span className="text-xs bg-satya-card border border-satya-border
                               px-2 py-0.5 rounded-full capitalize">
                {data.platform}
              </span>
            )}
          </div>
        )}

        {/* Processing / failed */}
        {!done && data && <ProcessingBanner status={data.status} />}

        {/* Results grid */}
        {done && !failed && (
          <>
            {/* Main score + sub-scores */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <GaugeCard
                score={data.satya_score}
                verdict={data.verdict}
                confidence={data.confidence}
              />
              <div className="card space-y-4">
                <h3 className="text-sm font-semibold text-satya-muted uppercase tracking-wider">
                  Modality Scores
                </h3>
                <SubScoreBar label="Video Forensics" icon="🎥" score={data.video_score} />
                <SubScoreBar label="Audio Forensics" icon="🎙" score={data.audio_score} />
                <SubScoreBar label="Text / Metadata" icon="📝" score={data.text_score} />
                <p className="text-xs text-satya-muted pt-1">
                  Higher score = more authentic. Lower score = more suspicious.
                </p>
              </div>
            </div>

            {/* Bedrock AI Summary */}
            {data.summary && (
              <div className="card">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xs bg-violet-900/40 text-violet-400 border border-violet-800
                                   px-2 py-0.5 rounded-full">Claude 3 Haiku</span>
                  <h3 className="text-sm font-semibold text-white">AI Explanation</h3>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed mb-4">{data.summary}</p>
                {data.findings?.length > 0 && (
                  <div className="border-t border-satya-border pt-4 space-y-2">
                    <h4 className="text-xs font-semibold text-satya-muted uppercase tracking-wider mb-2">
                      Forensic Findings
                    </h4>
                    {data.findings.map((f, i) => <FindingRow key={i} finding={f} />)}
                  </div>
                )}
              </div>
            )}

            {/* Recommendations */}
            {data.recommendations?.length > 0 && (
              <div className="card">
                <h3 className="text-sm font-semibold text-satya-muted uppercase tracking-wider mb-3">
                  Recommendations
                </h3>
                <ul className="space-y-2">
                  {data.recommendations.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <span className="text-blue-400 mt-0.5 flex-shrink-0">→</span>
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Meta */}
            <div className="card grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              {[
                { label: 'Processing Time', value: data.processing_time_ms ? `${(data.processing_time_ms/1000).toFixed(1)}s` : 'N/A' },
                { label: 'Language',        value: data.language || 'auto' },
                { label: 'Platform',        value: data.platform || '—' },
                { label: 'Analysis ID',     value: analysisId?.slice(0, 8) + '…' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <p className="text-xs text-satya-muted mb-1">{label}</p>
                  <p className="text-sm font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-center">
              <Link to="/" className="btn-secondary">Analyse another URL</Link>
              <Link to="/dashboard" className="btn-secondary">View Dashboard</Link>
            </div>
          </>
        )}

        {/* Failed state */}
        {failed && (
          <div className="card border-red-700 bg-red-900/20 text-center py-10">
            <p className="text-lg font-semibold text-red-400 mb-2">Analysis Failed</p>
            <p className="text-sm text-satya-muted mb-6">
              {data.error_message || 'An unexpected error occurred during processing.'}
            </p>
            <Link to="/" className="btn-primary">Try another URL</Link>
          </div>
        )}
      </main>
    </div>
  )
}
