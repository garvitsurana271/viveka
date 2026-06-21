// History — the archive of verification records. Past reports are documents you
// return to (reopenable instantly), searchable, with their IDs and verdicts.
import { useState } from 'react'
import { Search, X, ChevronRight, Trash2, FileSearch, ScanSearch } from 'lucide-react'
import { statusOf } from '../theme.js'
import { relTime } from '../store.js'

export default function History({ history = [], openReport, wipeHistory, onVerify }) {
  const [filter, setFilter] = useState('')
  const [cat, setCat] = useState('all')

  const cats = [
    { key: 'all', label: 'All' },
    { key: 'refuted', label: 'Refuted' },
    { key: 'misleading', label: 'Misleading' },
    { key: 'supported', label: 'Supported' },
    { key: 'human', label: 'Unresolved' },
  ]
  const matchCat = (h) => {
    if (cat === 'all') return true
    const k = statusOf(h.result || { verdict: h.verdict }).key
    if (cat === 'human') return k === 'human' || k === 'insufficient'
    return k === cat
  }
  const list = history
    .filter(matchCat)
    .filter((h) => !filter.trim() || (h.snippet || '').toLowerCase().includes(filter.toLowerCase()))

  return (
    <section className="mx-auto w-full max-w-[760px] px-4 pb-24 pt-8 sm:px-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="m-0 text-[24px] font-semibold tracking-[-0.01em] text-ink">Verification history</h1>
          <p className="m-0 mt-[5px] font-mono text-[11.5px] tnum text-muted-label">{history.length} record{history.length === 1 ? '' : 's'} · stored on this device</p>
        </div>
        {history.length > 0 && (
          <button onClick={wipeHistory} className="flex cursor-pointer items-center gap-[6px] rounded-[8px] border px-[11px] py-[7px] font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-label transition-colors hover:text-ink" style={{ borderColor: '#E5E7E7' }}><Trash2 size={12} /> clear all</button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="rounded-[14px] border bg-surface px-6 py-14 text-center shadow-panel" style={{ borderColor: '#E5E7E7' }}>
          <FileSearch size={26} className="mx-auto mb-3 text-muted-faint" />
          <div className="text-[15px] font-semibold text-ink">No records yet</div>
          <p className="mx-auto mb-5 mt-[6px] max-w-[320px] text-[13px] leading-[1.55] text-muted">Every forward you verify is saved here as a report you can reopen and search.</p>
          <button onClick={onVerify} className="mx-auto flex cursor-pointer items-center gap-[8px] rounded-[9px] px-[18px] py-[11px] text-[13.5px] font-semibold text-white" style={{ background: '#136F7A' }}><ScanSearch size={16} /> Verify a forward</button>
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-center gap-[8px] rounded-[10px] border bg-surface px-[12px] py-[9px]" style={{ borderColor: '#E5E7E7' }}>
            <Search size={15} className="text-muted-faint" />
            <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search records…" className="w-full border-0 bg-transparent text-[13.5px] text-ink outline-none placeholder:text-muted-faint" />
            {filter && <button onClick={() => setFilter('')} className="cursor-pointer"><X size={14} className="text-muted-faint" /></button>}
          </div>

          <div className="mb-4 flex flex-wrap gap-[7px]">
            {cats.map((c) => {
              const on = cat === c.key
              return (
                <button key={c.key} onClick={() => setCat(c.key)} className="cursor-pointer rounded-[7px] border px-[12px] py-[6px] text-[12px] font-semibold transition-colors"
                  style={on ? { background: '#136F7A', color: '#fff', borderColor: '#136F7A' } : { background: '#fff', color: '#5A616A', borderColor: '#E5E7E7' }}>{c.label}</button>
              )
            })}
          </div>

          <div className="overflow-hidden rounded-[12px] border bg-surface shadow-panel" style={{ borderColor: '#E5E7E7' }}>
            {list.length === 0 && <div className="px-[14px] py-[18px] text-center text-[13px] text-muted-faint">No records match.</div>}
            {list.map((h) => {
              const st = statusOf(h.result || { verdict: h.verdict })
              const Icon = st.Icon
              return (
                <button key={h.id} onClick={() => openReport(h)} className="flex w-full cursor-pointer items-start gap-[12px] border-b px-[15px] py-[13px] text-left transition-colors last:border-b-0 hover:bg-raised" style={{ borderColor: '#EEF0F0' }}>
                  <span className="mt-[1px] flex h-[28px] w-[28px] flex-shrink-0 items-center justify-center rounded-[8px]" style={{ background: st.bg }}><Icon size={16} strokeWidth={2.3} style={{ color: st.color }} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13.5px] font-medium text-ink font-deva">{h.snippet}</span>
                    <span className="mt-[3px] flex flex-wrap items-center gap-x-[8px] gap-y-[2px] font-mono text-[10.5px] tnum text-muted-faint">
                      <span className="font-semibold" style={{ color: st.color }}>{st.label}</span>
                      <span>·</span><span>{h.reportId || ''}</span>
                      <span>·</span><span>{relTime(h.ts)}</span>
                    </span>
                  </span>
                  <ChevronRight size={16} className="mt-[2px] flex-shrink-0 text-muted-faint" />
                </button>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
