// Review — the human-in-the-loop. When the engine abstains or flags high harm, a
// person decides. Clinical queue; an explicitly illustrative workflow (sample items).
import { useState } from 'react'
import { Check as CheckIcon, ShieldAlert, UserRoundSearch } from 'lucide-react'
import { REVIEW_QUEUE } from '../data.js'
import { STATUS, statusByVerdict } from '../theme.js'

const HARM = {
  high: { label: 'High harm', color: '#B23A36', bg: '#F8E9E8' },
  med: { label: 'Medium', color: '#946612', bg: '#F6EEDC' },
  low: { label: 'Low', color: '#1C7C54', bg: '#E8F3EC' },
}
const CHOICES = ['supported', 'misleading', 'refuted', 'human', 'opinion']

export default function Review() {
  const [decisions, setDecisions] = useState({})   // id -> chosen status key
  const [published, setPublished] = useState({})    // id -> true

  return (
    <section className="mx-auto w-full max-w-[780px] px-4 pb-24 pt-8 sm:px-6">
      <div className="mb-5">
        <div className="mb-[10px] inline-flex items-center gap-[7px] rounded-[7px] border px-[10px] py-[5px] font-mono text-[10.5px] uppercase tracking-[0.1em]" style={{ background: '#ECECF8', color: '#4B49B6', borderColor: '#D2D2F0' }}>
          <UserRoundSearch size={12} /> Human-in-the-loop · illustrative workflow
        </div>
        <h1 className="m-0 text-[24px] font-semibold tracking-[-0.01em] text-ink">Review queue</h1>
        <p className="m-0 mt-[6px] max-w-[60ch] text-[13.5px] leading-[1.55] text-muted">The engine flags; a person decides. Each item is one the engine couldn&apos;t rule on confidently or marked high-harm. Confirm its call, change it, or clear it. <span className="text-muted-faint">Sample items, for demonstration.</span></p>
      </div>

      <div className="flex flex-col gap-[14px]">
        {REVIEW_QUEUE.map((it) => {
          const sug = statusByVerdict(it.suggested)
          const h = HARM[it.harm] || HARM.med
          const chosenKey = decisions[it.id] || sug.key
          const chosen = STATUS[chosenKey]
          const isPub = published[it.id]
          return (
            <div key={it.id} className="overflow-hidden rounded-[12px] border bg-surface shadow-panel" style={{ borderColor: '#E5E7E7' }}>
              {/* meta */}
              <div className="flex flex-wrap items-center gap-x-[12px] gap-y-[4px] border-b px-[15px] py-[10px] font-mono text-[10.5px] tnum text-muted-faint" style={{ borderColor: '#EEF0F0', background: '#FBFCFC' }}>
                <span className="inline-flex items-center gap-[4px] rounded-[4px] px-[6px] py-[2px] font-semibold uppercase tracking-[0.06em]" style={{ background: h.bg, color: h.color }}><ShieldAlert size={11} /> {h.label}</span>
                <span>{it.lang}</span><span>·</span><span>{it.age}</span><span>·</span><span>{it.reach}</span>
              </div>
              <div className="px-[15px] py-[14px]">
                {/* the forward */}
                <p className="m-0 text-[14px] leading-[1.5] text-ink font-deva">{it.forwardEn}</p>
                {it.forwardGloss && <p className="m-0 mt-[5px] text-[12.5px] leading-[1.45] text-muted-label font-deva">{it.forwardGloss}</p>}

                {/* engine suggestion */}
                <div className="mt-[12px] flex flex-wrap items-center gap-[9px]">
                  <span className="vk-label">Engine suggests</span>
                  <span className="inline-flex items-center gap-[5px] rounded-[6px] border px-[8px] py-[3px] text-[11.5px] font-semibold" style={{ background: sug.bg, color: sug.color, borderColor: sug.line }}><sug.Icon size={12} /> {sug.label}</span>
                  <span className="font-mono text-[11px] tnum text-muted">{it.confidence}%</span>
                </div>
                <p className="m-0 mt-[7px] text-[12.5px] leading-[1.5] text-muted">{it.why}</p>
                {it.sources?.length > 0 && (
                  <div className="mt-[8px] flex flex-col gap-[2px]">
                    {it.sources.map((s, i) => <div key={i} className="font-mono text-[10.5px] leading-[1.5] text-muted-faint">· {s}</div>)}
                  </div>
                )}

                {/* decision */}
                {isPub ? (
                  <div className="mt-[13px] flex items-center gap-[9px] rounded-[9px] border px-[13px] py-[11px]" style={{ background: chosen.bg, borderColor: chosen.line }}>
                    <CheckIcon size={16} style={{ color: chosen.color }} />
                    <div className="text-[12.5px]" style={{ color: chosen.color }}>
                      <span className="font-semibold">Decision recorded — {chosen.label}.</span>
                      <span className="text-muted-label"> In a deployment this notifies everyone who checked the same forward.</span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-[13px] border-t pt-[12px]" style={{ borderColor: '#EEF0F0' }}>
                    <div className="vk-label mb-[8px]">Reviewer decision</div>
                    <div className="flex flex-wrap gap-[6px]">
                      {CHOICES.map((k) => {
                        const st = STATUS[k]; const on = chosenKey === k
                        return (
                          <button key={k} onClick={() => setDecisions((d) => ({ ...d, [it.id]: k }))} className="flex cursor-pointer items-center gap-[5px] rounded-[7px] border px-[10px] py-[6px] text-[11.5px] font-semibold transition-colors"
                            style={on ? { background: st.bg, color: st.color, borderColor: st.color } : { background: '#fff', color: '#5A616A', borderColor: '#E5E7E7' }}>
                            <st.Icon size={12} /> {st.word}
                          </button>
                        )
                      })}
                    </div>
                    <button onClick={() => setPublished((p) => ({ ...p, [it.id]: true }))} className="mt-[11px] flex w-full cursor-pointer items-center justify-center gap-[7px] rounded-[8px] py-[10px] text-[13px] font-semibold text-white" style={{ background: '#136F7A' }}>
                      Publish decision
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
