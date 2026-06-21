// Pulse — a secondary "signal monitor": what's circulating, with real verdicts.
// Clinical, list-first. The rumours and verdicts are real (from the antibody DB);
// volumes/regions are an explicit illustrative preview of a deployed monitoring board.
import { useState, useEffect } from 'react'
import { TrendingUp, MapPin, Activity } from 'lucide-react'
import { PULSE_CATS, PULSE_RUMORS } from '../data.js'
import { statusByVerdict } from '../theme.js'

const DOMAIN_CAT = { health: 'health', finance: 'finance', communal: 'safety', disaster: 'safety', product: 'civic', general: 'civic' }
function mapLive(r) {
  // Real rumour + verdict from the antibody DB; no fabricated volume/reach numbers.
  return { id: r.id, cat: DOMAIN_CAT[r.domain] || 'civic', verdict: r.verdict, claim: r.claim, gloss: r.gloss,
    surge: !!(r.age && (String(r.age).includes('hour') || String(r.age).includes('now'))) }
}

export default function Pulse() {
  const [filter, setFilter] = useState('all')
  const [live, setLive] = useState(null)
  useEffect(() => {
    let ok = true
    fetch((import.meta.env.VITE_ENGINE_URL || '') + '/api/pulse')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (ok && d?.rumors?.length) setLive(d.rumors.map(mapLive)) })
      .catch(() => {})
    return () => { ok = false }
  }, [])
  const source = live?.length ? live : PULSE_RUMORS
  const flagged = source.filter((r) => ['false', 'misleading', 'human'].includes(r.verdict)).length
  const rows = source.filter((r) => filter === 'all' || r.cat === filter)

  return (
    <section className="mx-auto w-full max-w-[820px] px-4 pb-24 pt-8 sm:px-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-[10px] inline-flex items-center gap-[7px] rounded-[7px] border px-[10px] py-[5px] font-mono text-[10.5px] uppercase tracking-[0.1em]" style={{ background: '#F6EEDC', color: '#946612', borderColor: '#E7D6AE' }}>
            <Activity size={12} /> Signal monitor
          </div>
          <h1 className="m-0 text-[24px] font-semibold tracking-[-0.01em] text-ink">What&apos;s circulating</h1>
          <p className="m-0 mt-[6px] max-w-[60ch] text-[13.5px] leading-[1.55] text-muted">The rumours and their verdicts are real, drawn from Viveka&apos;s memory. <span className="text-muted-faint">Volumes and regions are an illustrative preview of the monitoring board a deployed Viveka builds from live activity.</span></p>
        </div>
        <div className="flex gap-[10px]">
          <Stat value={source.length} label="tracked" />
          <Stat value={flagged} label="flagged" accent />
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-[7px]">
        {PULSE_CATS.map((c) => {
          const on = filter === c.key
          return <button key={c.key} onClick={() => setFilter(c.key)} className="cursor-pointer rounded-[7px] border px-[12px] py-[6px] text-[12px] font-semibold transition-colors" style={on ? { background: '#136F7A', color: '#fff', borderColor: '#136F7A' } : { background: '#fff', color: '#5A616A', borderColor: '#E5E7E7' }}>{c.label}</button>
        })}
      </div>

      <div className="overflow-hidden rounded-[12px] border bg-surface shadow-panel" style={{ borderColor: '#E5E7E7' }}>
        {rows.map((r, i) => {
          const st = statusByVerdict(r.verdict)
          const Icon = st.Icon
          return (
            <div key={r.id} className="flex items-start gap-[13px] border-b px-[15px] py-[13px] last:border-b-0" style={{ borderColor: '#EEF0F0' }}>
              <span className="mt-[1px] w-[20px] flex-shrink-0 text-center font-mono text-[13px] tnum text-muted-faint">{i + 1}</span>
              <span className="mt-[1px] flex h-[28px] w-[28px] flex-shrink-0 items-center justify-center rounded-[8px]" style={{ background: st.bg }}><Icon size={16} strokeWidth={2.3} style={{ color: st.color }} /></span>
              <div className="min-w-0 flex-1">
                <p className="m-0 text-[13.5px] font-medium leading-[1.45] text-ink font-deva">{r.claim}</p>
                <p className="m-0 mt-[3px] text-[12.5px] leading-[1.45] text-muted-label">{r.gloss}</p>
                <div className="mt-[7px] flex flex-wrap items-center gap-x-[12px] gap-y-[3px] font-mono text-[10.5px] tnum">
                  <span className="font-semibold uppercase tracking-[0.06em]" style={{ color: st.color }}>{st.label}</span>
                  {r.regions && <span className="flex items-center gap-[4px] text-muted-faint"><MapPin size={11} /> {r.regions.join(', ')}</span>}
                  {r.surge && <span className="flex items-center gap-[4px]" style={{ color: '#B23A36' }}><TrendingUp size={11} /> surging</span>}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Stat({ value, label, accent }) {
  return (
    <div className="rounded-[9px] border bg-surface px-[14px] py-[8px] text-center" style={{ borderColor: '#E5E7E7' }}>
      <div className="font-mono text-[20px] tnum font-semibold leading-none" style={{ color: accent ? '#B23A36' : '#136F7A' }}>{value}</div>
      <div className="mt-[3px] font-mono text-[9px] uppercase tracking-[0.1em] text-muted-faint">{label}</div>
    </div>
  )
}
