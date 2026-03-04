import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getStats, getTrending, VERDICT_META } from '../api'

const PLATFORM_OPTIONS = [
  { id: 'youtube',   label: 'YouTube'   },
  { id: 'instagram', label: 'Instagram' },
  { id: 'sharechat', label: 'ShareChat' },
  { id: 'x',        label: 'X'         },
]

function StatCard({ label, value, sub, color }) {
  return (
    <div className="card">
      <p className="text-xs text-satya-muted uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color || 'text-white'}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-satya-muted mt-1">{sub}</p>}
    </div>
  )
}

function VerdictBadge({ verdict }) {
  const meta = VERDICT_META[verdict] || { label: verdict, bg: 'bg-slate-700', border: 'border-slate-600', text: 'text-slate-300' }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${meta.bg} ${meta.border} ${meta.text}`}>
      {meta.label}
    </span>
  )
}

function TrendingRow({ item }) {
  const score = item.satya_score != null ? parseFloat(item.satya_score).toFixed(1) : '—'
  const meta = VERDICT_META[item.verdict] || {}

  return (
    <div className="flex items-center gap-4 py-3 border-b border-satya-border last:border-0">
      {/* Score circle */}
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 border-2 text-sm font-bold"
        style={{ borderColor: meta.color || '#475569', color: meta.color || '#94A3B8' }}
      >
        {score}
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm text-white truncate">
          {item.content_url ? (
            <a href={item.content_url} target="_blank" rel="noopener noreferrer"
               className="hover:text-blue-400 transition-colors">
              {item.content_url.replace(/https?:\/\/(www\.)?/, '').slice(0, 55)}…
            </a>
          ) : item.analysis_id}
        </p>
        <p className="text-xs text-satya-muted mt-0.5 capitalize">
          {item.platform || 'unknown'} · {item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}
        </p>
      </div>

      <VerdictBadge verdict={item.verdict} />
    </div>
  )
}

function LoadingRows() {
  return Array.from({ length: 4 }, (_, i) => (
    <div key={i} className="flex items-center gap-4 py-3 border-b border-satya-border animate-pulse">
      <div className="w-11 h-11 rounded-full bg-satya-card flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-satya-card rounded w-3/4" />
        <div className="h-2 bg-satya-card rounded w-1/2" />
      </div>
      <div className="h-5 bg-satya-card rounded w-16" />
    </div>
  ))
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [trending, setTrending] = useState(null)
  const [platform, setPlatform] = useState('youtube')
  const [loadingStats, setLoadingStats] = useState(true)
  const [loadingTrending, setLoadingTrending] = useState(true)
  const [statsError, setStatsError] = useState('')
  const [trendingError, setTrendingError] = useState('')

  useEffect(() => {
    setLoadingStats(true)
    getStats()
      .then(data => {
        setStats(data)
        setStatsError(data ? '' : 'Could not load stats')
      })
      .catch(err => setStatsError(err.message))
      .finally(() => setLoadingStats(false))
  }, [])

  useEffect(() => {
    setLoadingTrending(true)
    setTrendingError('')
    getTrending(platform)
      .then(data => {
        if (!data) { setTrendingError('Could not load trending data'); return }
        setTrending(data.trending_fakes || [])
      })
      .catch(err => setTrendingError(err.message))
      .finally(() => setLoadingTrending(false))
  }, [platform])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-satya-border px-6 py-4 flex items-center gap-4">
        <Link to="/" className="text-2xl font-bold text-white tracking-tight">SATYA</Link>
        <span className="text-satya-muted text-sm">/</span>
        <span className="text-sm text-white font-semibold">Dashboard</span>
        <div className="ml-auto flex items-center gap-3">
          <Link to="/" className="btn-secondary text-sm py-1.5 px-4">Analyse URL</Link>
        </div>
      </nav>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-8">
        {/* Stats grid */}
        <section>
          <h2 className="text-sm font-semibold text-satya-muted uppercase tracking-wider mb-4">
            Platform Overview
          </h2>
          {statsError && (
            <p className="text-xs text-amber-400 mb-3">
              {statsError} — make sure the API is running on :8000
            </p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {loadingStats ? (
              Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="card animate-pulse h-24" />
              ))
            ) : (
              <>
                <StatCard
                  label="Total Analyses"
                  value={stats?.total_analyses ?? '—'}
                  sub="All time"
                />
                <StatCard
                  label="Fakes Detected"
                  value={stats?.fakes_detected ?? '—'}
                  color="text-red-400"
                  sub="HIGH_RISK verdict"
                />
                <StatCard
                  label="Authenticity Rate"
                  value={stats?.authenticity_rate != null ? `${stats.authenticity_rate}%` : '—'}
                  color="text-green-400"
                  sub="Non-high-risk"
                />
                <StatCard
                  label="Languages"
                  value={stats?.languages_supported?.length ?? 11}
                  color="text-blue-400"
                  sub="Indian languages"
                />
              </>
            )}
          </div>
        </section>

        {/* Trending feed */}
        <section>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 className="text-sm font-semibold text-satya-muted uppercase tracking-wider">
              Trending Suspicious Content (Today)
            </h2>
            {/* Platform filter */}
            <div className="flex gap-2">
              {PLATFORM_OPTIONS.map(p => (
                <button
                  key={p.id}
                  onClick={() => setPlatform(p.id)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors
                    ${platform === p.id
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'bg-satya-card border-satya-border text-satya-muted hover:text-white'}`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="card py-2">
            {trendingError && (
              <p className="text-xs text-amber-400 px-2 py-4">
                {trendingError}
              </p>
            )}
            {loadingTrending && <LoadingRows />}
            {!loadingTrending && !trendingError && trending?.length === 0 && (
              <div className="text-center py-12">
                <p className="text-satya-muted text-sm">No suspicious content detected today.</p>
                <p className="text-xs text-slate-600 mt-2">
                  Only HIGH_RISK and SUSPICIOUS verdicts appear here.
                </p>
              </div>
            )}
            {!loadingTrending && trending?.map((item, i) => (
              <TrendingRow key={item.analysis_id || i} item={item} />
            ))}
          </div>
        </section>

        {/* Info banner */}
        <div className="card bg-blue-950/30 border-blue-800">
          <div className="flex flex-col sm:flex-row gap-4 items-start">
            <div>
              <h3 className="text-sm font-semibold text-blue-300 mb-1">About SATYA</h3>
              <p className="text-xs text-satya-muted leading-relaxed">
                SATYA (Synthetic Audio-Text-Video Authenticity) uses multi-modal AI forensics to detect
                deepfakes and AI-generated content across Indian social media platforms.
                Supports 11 Indian languages with AI explanations via Amazon Bedrock.
              </p>
            </div>
            <div className="flex-shrink-0 flex flex-col gap-1.5 text-xs text-satya-muted">
              <span>✓ Video forensics (GAN, temporal, face)</span>
              <span>✓ Audio forensics (voice clone, prosody)</span>
              <span>✓ Text analysis (LLM detection, bots)</span>
              <span>✓ Bedrock AI explanations</span>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-satya-border px-6 py-4 text-center">
        <p className="text-xs text-satya-muted">
          SATYA — Team Imperials · AWS AI for Bharat Hackathon 2026
        </p>
      </footer>
    </div>
  )
}
