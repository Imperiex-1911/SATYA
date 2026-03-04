const BASE = '/api/v1'

export async function submitAnalysis(url, language = 'auto') {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, language }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const msg = err?.detail?.message || err?.detail || `HTTP ${res.status}`
    throw new Error(msg)
  }
  return res.json()
}

export async function getAnalysis(analysisId) {
  const res = await fetch(`${BASE}/analyze/${analysisId}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail?.message || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getStats() {
  const res = await fetch(`${BASE}/dashboard/stats`)
  if (!res.ok) return null
  return res.json()
}

export async function getTrending(platform = 'youtube') {
  const res = await fetch(`${BASE}/dashboard/trending?platform=${platform}`)
  if (!res.ok) return null
  return res.json()
}

// Verdict display helpers
export const VERDICT_META = {
  HIGH_RISK:  { label: 'High Risk',  color: '#EF4444', bg: 'bg-red-900/30',    border: 'border-red-700',    text: 'text-red-400'    },
  SUSPICIOUS: { label: 'Suspicious', color: '#F97316', bg: 'bg-orange-900/30', border: 'border-orange-700', text: 'text-orange-400' },
  UNCERTAIN:  { label: 'Uncertain',  color: '#EAB308', bg: 'bg-yellow-900/30', border: 'border-yellow-700', text: 'text-yellow-400' },
  AUTHENTIC:  { label: 'Authentic',  color: '#22C55E', bg: 'bg-green-900/30',  border: 'border-green-700',  text: 'text-green-400'  },
}

export const LANGUAGES = [
  { code: 'auto', name: 'Auto-detect' },
  { code: 'en',   name: 'English'     },
  { code: 'hi',   name: 'Hindi'       },
  { code: 'ta',   name: 'Tamil'       },
  { code: 'te',   name: 'Telugu'      },
  { code: 'bn',   name: 'Bengali'     },
  { code: 'mr',   name: 'Marathi'     },
  { code: 'kn',   name: 'Kannada'     },
  { code: 'ml',   name: 'Malayalam'   },
  { code: 'gu',   name: 'Gujarati'    },
  { code: 'pa',   name: 'Punjabi'     },
  { code: 'or',   name: 'Odia'        },
  { code: 'ur',   name: 'Urdu'        },
]

export const TERMINAL_STATUSES = ['completed', 'failed']

export function isTerminal(status) {
  return TERMINAL_STATUSES.includes(status)
}
