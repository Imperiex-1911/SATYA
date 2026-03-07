import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { submitAnalysis, LANGUAGES } from '../api'

const DEMO_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

const PLATFORMS = [
  { id: 'youtube',    label: 'YouTube',   icon: '▶', color: 'text-red-400',    border: 'border-red-800'    },
  { id: 'instagram',  label: 'Instagram', icon: '📷', color: 'text-pink-400',  border: 'border-pink-800'  },
  { id: 'sharechat',  label: 'ShareChat', icon: '💬', color: 'text-blue-400',  border: 'border-blue-800'  },
  { id: 'x',          label: 'X / Twitter', icon: '✕', color: 'text-slate-300', border: 'border-slate-600' },
]

const SAMPLE_TRENDING = [
  { title: 'Politician speech goes viral — likely deepfake', platform: 'YouTube', verdict: 'HIGH_RISK',  score: 23 },
  { title: 'Celebrity endorsement of financial product',     platform: 'Instagram', verdict: 'SUSPICIOUS', score: 57 },
  { title: 'News anchor clip from regional channel',         platform: 'ShareChat', verdict: 'UNCERTAIN',  score: 72 },
]

function VerdictBadge({ verdict, score }) {
  const meta = {
    HIGH_RISK:  { label: 'High Risk',  cls: 'bg-red-900/50 text-red-400 border-red-700'       },
    SUSPICIOUS: { label: 'Suspicious', cls: 'bg-orange-900/50 text-orange-400 border-orange-700' },
    UNCERTAIN:  { label: 'Uncertain',  cls: 'bg-yellow-900/50 text-yellow-400 border-yellow-700' },
    AUTHENTIC:  { label: 'Authentic',  cls: 'bg-green-900/50 text-green-400 border-green-700'    },
  }[verdict] || { label: verdict, cls: 'bg-slate-700 text-slate-300 border-slate-600' }

  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${meta.cls}`}>
      {score}/100 — {meta.label}
    </span>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [language, setLanguage] = useState('auto')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) {
      setError('Please enter a video URL.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const result = await submitAnalysis(trimmed, language)
      navigate(`/results/${result.analysis_id}`)
    } catch (err) {
      setError(err.message || 'Failed to submit. Is the API running on :8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-satya-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold text-white tracking-tight">SATYA</span>
          <span className="text-xs text-satya-muted bg-satya-card border border-satya-border
                           px-2 py-0.5 rounded-full">AI Authenticity</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="text-sm text-satya-muted hover:text-white transition-colors">
            Dashboard
          </Link>
          <span className="text-xs bg-blue-900/40 text-blue-400 border border-blue-800 px-2 py-1 rounded">
            Prototype v1
          </span>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="w-full max-w-2xl">
          {/* Title */}
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold text-white mb-3 leading-tight">
              Is this content real?
            </h1>
            <p className="text-satya-muted text-lg max-w-md mx-auto">
              Paste a YouTube link. SATYA analyses video, audio, and text using AI forensics
              to detect deepfakes and synthetic media.
            </p>
          </div>

          {/* Input card */}
          <div className="card mb-4">
            <form onSubmit={handleSubmit}>
              <div className="flex gap-2 mb-4">
                <input
                  type="url"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="flex-1 bg-slate-900 border border-satya-border rounded-lg
                             px-4 py-3 text-white placeholder-slate-500 focus:outline-none
                             focus:border-blue-500 transition-colors text-sm"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary whitespace-nowrap"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-4 h-4 border-2 border-white/30
                                       border-t-white rounded-full animate-spin" />
                      Submitting…
                    </span>
                  ) : 'Verify with SATYA'}
                </button>
              </div>

              {/* Language selector */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-satya-muted whitespace-nowrap">Report language:</span>
                <select
                  value={language}
                  onChange={e => setLanguage(e.target.value)}
                  className="bg-slate-900 border border-satya-border rounded-lg px-3 py-1.5
                             text-sm text-white focus:outline-none focus:border-blue-500 flex-1"
                >
                  {LANGUAGES.map(l => (
                    <option key={l.code} value={l.code}>{l.name}</option>
                  ))}
                </select>
              </div>

              {error && (
                <p className="mt-3 text-sm text-red-400 bg-red-900/20 border border-red-800
                               rounded-lg px-4 py-2">{error}</p>
              )}
            </form>
          </div>

          {/* Demo URL for judges */}
          <div className="flex items-center justify-center gap-2 mb-6">
            <span className="text-xs text-satya-muted">Try a demo:</span>
            <button
              type="button"
              onClick={() => setUrl(DEMO_URL)}
              className="text-xs text-blue-400 hover:text-blue-300 border border-blue-800
                         hover:border-blue-600 bg-blue-900/20 px-3 py-1 rounded-full
                         transition-colors"
            >
              ▶ Rick Astley — Never Gonna Give You Up (YouTube)
            </button>
          </div>

          {/* Platform badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
            <span className="text-xs text-satya-muted">Supports:</span>
            {PLATFORMS.map(p => (
              <span
                key={p.id}
                className={`flex items-center gap-1.5 text-xs border rounded-full px-3 py-1
                            ${p.color} ${p.border} bg-satya-card
                            ${p.id !== 'youtube' ? 'opacity-40' : ''}`}
              >
                <span>{p.icon}</span>
                {p.label}
                {p.id !== 'youtube' && <span className="text-[10px] text-satya-muted">(soon)</span>}
              </span>
            ))}
          </div>

          {/* Trending fakes */}
          <div>
            <h2 className="text-sm font-semibold text-satya-muted uppercase tracking-wider mb-3">
              Recent Analyses
            </h2>
            <div className="space-y-2">
              {SAMPLE_TRENDING.map((item, i) => (
                <div key={i} className="card flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="text-sm text-white truncate">{item.title}</p>
                    <p className="text-xs text-satya-muted mt-0.5">{item.platform}</p>
                  </div>
                  <VerdictBadge verdict={item.verdict} score={item.score} />
                </div>
              ))}
            </div>
            <p className="text-xs text-satya-muted text-center mt-3">
              Sample data — live trending updates available via{' '}
              <Link to="/dashboard" className="text-blue-400 hover:underline">Dashboard</Link>
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-satya-border px-6 py-4 text-center">
        <p className="text-xs text-satya-muted">
          SATYA — Team Imperials · AWS AI for Bharat Hackathon 2026 ·
          Built with AWS Bedrock, Amazon Nova Micro, and faster-whisper
        </p>
      </footer>
    </div>
  )
}
