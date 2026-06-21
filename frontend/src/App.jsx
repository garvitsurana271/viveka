import { useState, useEffect } from 'react'
import { ChevronDown, ShieldCheck } from 'lucide-react'
import BrandMark from './components/BrandMark.jsx'
import { LANGS } from './data.js'
import Verify from './surfaces/Verify.jsx'
import History from './surfaces/History.jsx'
import Review from './surfaces/Review.jsx'
import Pulse from './surfaces/Pulse.jsx'
import { loadChecks, addCheck as addCheckStore, clearChecks, loadPrefs, savePrefs } from './store.js'
import { detectRegion } from './actions.js'

const PRIMARY = [{ key: 'verify', label: 'Verify' }, { key: 'history', label: 'History' }]
const SECONDARY = [{ key: 'pulse', label: 'Pulse' }, { key: 'review', label: 'Review' }]

export default function App() {
  const prefs0 = loadPrefs()
  const [surface, setSurface] = useState(prefs0.surface || 'verify')
  const [lang, setLang] = useState(prefs0.lang || 'en')
  const [langOpen, setLangOpen] = useState(false)
  const [history, setHistory] = useState(() => loadChecks())
  const [openEntry, setOpenEntry] = useState(null)
  const [engineUp, setEngineUp] = useState(null)
  const [region, setRegion] = useState(prefs0.region || detectRegion())   // adaptive reporting channels

  useEffect(() => {
    let ok = true
    fetch((import.meta.env.VITE_ENGINE_URL || '') + '/api/health')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (ok) setEngineUp(d ? !d.offline : false) })
      .catch(() => { if (ok) setEngineUp(false) })
    return () => { ok = false }
  }, [])
  useEffect(() => { savePrefs({ surface, lang, region }) }, [surface, lang, region])

  const recordCheck = (e) => setHistory((prev) => addCheckStore(prev, e))
  const wipeHistory = () => setHistory(clearChecks())
  const openReport = (entry) => { setOpenEntry(entry); setSurface('verify') }
  const caught = history.filter((h) => ['false', 'misleading', 'human'].includes(h.verdict)).length

  const curLang = LANGS.find((l) => l.key === lang) || LANGS[0]
  const langLabel = lang === 'en' ? 'EN' : lang === 'hi' ? 'हिन्दी' : curLang.label.split(' ')[0]

  const NavBtn = ({ t }) => {
    const active = surface === t.key
    return (
      <button onClick={() => { setSurface(t.key); setLangOpen(false) }} aria-current={active ? 'page' : undefined}
        className="cursor-pointer rounded-[7px] px-[13px] py-[6px] text-[13px] font-semibold transition-colors"
        style={active ? { background: '#136F7A', color: '#fff' } : { background: 'transparent', color: '#5A616A' }}>
        {t.label}
      </button>
    )
  }

  return (
    <div className="vk-canvas flex min-h-screen flex-col text-ink">
      {/* ---------- Header ---------- */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b px-4 py-[11px] sm:px-7"
        style={{ borderColor: '#E5E7E7', background: 'rgba(246,247,247,0.86)', backdropFilter: 'blur(10px)' }}>
        <div className="flex items-center gap-[10px]">
          <BrandMark size={28} />
          <div className="flex flex-col leading-none">
            <span className="text-[18px] font-semibold tracking-[-0.01em] text-ink">Viveka</span>
            <span className="mt-[3px] font-mono text-[9px] uppercase tracking-[0.16em] text-muted-faint">Verification Workspace</span>
          </div>
        </div>

        <nav className="flex items-center gap-[3px] rounded-[10px] border p-[3px]" style={{ background: '#fff', borderColor: '#E5E7E7' }}>
          {PRIMARY.map((t) => <NavBtn key={t.key} t={t} />)}
          <span className="mx-[3px] h-[18px] w-px" style={{ background: '#E5E7E7' }} />
          {SECONDARY.map((t) => <NavBtn key={t.key} t={t} />)}
        </nav>

        <div className="relative flex items-center gap-[10px]">
          {history.length > 0 && (
            <div className="hidden items-center gap-[6px] rounded-[8px] border px-[10px] py-[5px] font-mono text-[11px] tnum lg:flex" style={{ background: '#fff', borderColor: '#E5E7E7', color: '#0C5560' }} title="Forwards you've verified, and how many were flagged false, misleading or routed to review">
              <ShieldCheck size={13} style={{ color: '#136F7A' }} />
              {history.length} verified{caught > 0 && <span className="text-muted-faint">· {caught} flagged</span>}
            </div>
          )}
          <div className="hidden items-center gap-[6px] font-mono text-[11px] text-muted-label sm:flex" title={engineUp === false ? 'Offline demo (no live key)' : 'Live reasoning engine reachable'}>
            <span className="h-[7px] w-[7px] rounded-full" style={engineUp === false ? { background: '#946612' } : { background: '#1C7C54' }} />
            {engineUp === null ? 'connecting' : engineUp ? 'engine online' : 'offline demo'}
          </div>
          <button onClick={() => setLangOpen((o) => !o)} className="flex cursor-pointer items-center gap-[7px] rounded-[8px] border bg-surface px-[11px] py-[6px] text-[12.5px] font-semibold text-ink" style={{ borderColor: '#E5E7E7' }}>
            <span className="font-deva">{curLang.glyph}</span><span>{langLabel}</span><ChevronDown size={12} className="text-muted-faint" />
          </button>
          {langOpen && (
            <div className="absolute right-0 top-[42px] z-40 w-[236px] rounded-[10px] border bg-surface p-[6px] shadow-pop" style={{ borderColor: '#E5E7E7' }}>
              <div className="vk-label px-[9px] pb-[5px] pt-[6px]">Read input in</div>
              {LANGS.map((l) => {
                const active = l.key === lang
                return (
                  <button key={l.key} onClick={() => { setLang(l.key); setLangOpen(false) }}
                    className="flex w-full cursor-pointer items-center gap-[10px] rounded-[7px] px-[9px] py-[8px] text-[13px] font-medium transition-colors"
                    style={active ? { background: '#E5F0F1', color: '#0C5560' } : { background: 'transparent', color: '#3A3F47' }}>
                    <span className="font-deva text-[15px]">{l.glyph}</span><span className="flex-1 text-left">{l.label}</span>
                    <span className="font-mono text-[10px] text-muted-faint">{l.sub}</span>
                  </button>
                )
              })}
              <div className="mt-[3px] border-t px-[9px] pb-[5px] pt-[8px] font-mono text-[10.5px] leading-[1.5] text-muted-faint" style={{ borderColor: '#EEF0F0' }}>
                Input any language · reports in English + Hindi.
              </div>
            </div>
          )}
        </div>
      </header>

      {/* ---------- Surfaces ---------- */}
      <main className="flex-1">
        {surface === 'verify' && <Verify lang={lang} region={region} setRegion={setRegion} history={history} recordCheck={recordCheck} wipeHistory={wipeHistory} openEntry={openEntry} onConsumeOpen={() => setOpenEntry(null)} />}
        {surface === 'history' && <History history={history} openReport={openReport} wipeHistory={wipeHistory} onVerify={() => setSurface('verify')} />}
        {surface === 'pulse' && <Pulse />}
        {surface === 'review' && <Review />}
      </main>
    </div>
  )
}
