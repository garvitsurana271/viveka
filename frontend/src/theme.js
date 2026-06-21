// Verification semantics for the Workspace. Verdicts use INSTITUTIONAL,
// fact-checking language (SUPPORTED / REFUTED / …), not probabilistic phrasing —
// a verification outcome, not a guess. Status colours read like a lab-report flag.
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  UserRoundSearch,
  CircleHelp,
  CircleSlash2,
} from 'lucide-react'

// Keyed by STATUS KEY (not the raw engine verdict — see statusKeyOf()).
export const STATUS = {
  supported: {
    key: 'supported', label: 'SUPPORTED', word: 'Supported', Icon: CheckCircle2,
    color: '#1C7C54', bg: '#E8F3EC', line: '#C5E2D2',
    gloss: 'The evidence backs this claim.',
  },
  misleading: {
    key: 'misleading', label: 'MISLEADING', word: 'Misleading', Icon: AlertTriangle,
    color: '#946612', bg: '#F6EEDC', line: '#E7D6AE',
    gloss: 'Partly true, but stripped of context or twisted.',
  },
  refuted: {
    key: 'refuted', label: 'REFUTED', word: 'Refuted', Icon: XCircle,
    color: '#B23A36', bg: '#F8E9E8', line: '#ECCAC7',
    gloss: 'The evidence contradicts this claim.',
  },
  insufficient: {
    key: 'insufficient', label: 'INSUFFICIENT EVIDENCE', word: 'Insufficient evidence', Icon: CircleHelp,
    color: '#566069', bg: '#EEF0F1', line: '#D8DCDE',
    gloss: 'Not enough trustworthy evidence to rule either way.',
  },
  human: {
    key: 'human', label: 'REQUIRES HUMAN REVIEW', word: 'Requires human review', Icon: UserRoundSearch,
    color: '#4B49B6', bg: '#ECECF8', line: '#D2D2F0',
    gloss: 'High-stakes or unclear — routed to a human reviewer.',
  },
  opinion: {
    key: 'opinion', label: 'NOT A FACTUAL CLAIM', word: 'Not a factual claim', Icon: CircleSlash2,
    color: '#6B7079', bg: '#EFF0F1', line: '#DCDEE0',
    gloss: 'Opinion, satire or prediction — nothing to verify.',
  },
}

// Display/legend order (best outcome to least-resolved).
export const STATUS_ORDER = ['supported', 'misleading', 'refuted', 'insufficient', 'human', 'opinion']

// Map the engine's raw verdict to an institutional status key. The engine emits a
// single "human" abstention; we split it: with NO retrieved evidence it reads as
// INSUFFICIENT EVIDENCE (a neutral non-finding); with evidence but still unsafe to
// rule, it reads as REQUIRES HUMAN REVIEW (a safety escalation).
export function statusKeyOf(result) {
  const v = (result?.verdict || 'human').toLowerCase()
  if (v === 'true') return 'supported'
  if (v === 'false') return 'refuted'
  if (v === 'misleading') return 'misleading'
  if (v === 'opinion') return 'opinion'
  // v === 'human'
  return (result?.sources?.length ? 'human' : 'insufficient')
}

export function statusOf(result) {
  return STATUS[statusKeyOf(result)] || STATUS.human
}

// Convenience for surfaces that hold a raw verdict string (Pulse/Review fixtures).
export function statusByVerdict(verdict) {
  return statusOf({ verdict, sources: verdict === 'human' ? [{}] : [] })
}

// Confidence presented as a measured READING, not a probability claim. A known-rumour
// match is a curated verified record, so it reads "VERIFIED", not a percentage.
export function confReading(result) {
  if (result?.matched) return { verified: true, pct: 100, band: 'Verified record' }
  const pct = Math.max(0, Math.min(100, Math.round(Number(result?.confidence ?? 0))))
  const band = pct >= 65 ? 'High confidence' : pct >= 48 ? 'Moderate confidence' : 'Low confidence'
  return { verified: false, pct, band }
}

// Stable, document-style report ID: VR-YYYY-MM-DD-HHMM. Every check is a record.
export function reportId(ts) {
  const d = new Date(ts || Date.now())
  const p = (n) => String(n).padStart(2, '0')
  return `VR-${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`
}

// Compact count formatter for stat chips.
export const fmtCount = (n) =>
  n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : '' + n
