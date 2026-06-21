// Local persistence — the difference between a single-shot form and an app.
// Every completed check is written here, so the app REMEMBERS the user: their
// history survives reloads and tab switches, and becomes the home screen.
//
// PRIVACY (be precise, not flattering): this HISTORY lives only in your browser's
// localStorage — no account, no login, it is never uploaded. But verification itself
// is not local: the message you check IS sent to the reasoning engine (Gemma, via
// Google's API) to analyse it, and a non-high-stakes rumour may be stored server-side
// in the shared "antibody" memory so the next person who gets it is answered instantly.
// Health / communal / disaster verdicts are never cached. See the System Card.

const CHECKS_KEY = 'viveka.checks.v1'
const PREFS_KEY = 'viveka.prefs.v1'
const MAX_CHECKS = 60

export function loadChecks() {
  try {
    const raw = localStorage.getItem(CHECKS_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function persist(list) {
  try {
    localStorage.setItem(CHECKS_KEY, JSON.stringify(list.slice(0, MAX_CHECKS)))
  } catch {
    /* private mode / quota — degrade silently to an in-memory session */
  }
}

// Prepend a new check; collapse an immediate duplicate (same text re-checked) so
// the list reflects distinct forwards, not repeats. Returns the new list.
export function addCheck(prev, entry) {
  const deduped = prev.filter((e) => e.snippet !== entry.snippet)
  const list = [entry, ...deduped].slice(0, MAX_CHECKS)
  persist(list)
  return list
}

export function clearChecks() {
  try {
    localStorage.removeItem(CHECKS_KEY)
  } catch {
    /* ignore */
  }
  return []
}

export function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY) || '{}') || {}
  } catch {
    return {}
  }
}

export function savePrefs(prefs) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    /* ignore */
  }
}

// "2m ago" / "3h ago" / "5d ago" — relative time for the history list.
export function relTime(ts) {
  const s = Math.max(0, Math.floor((Date.now() - ts) / 1000))
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return d === 1 ? 'yesterday' : `${d}d ago`
}
