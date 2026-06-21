// The Verification Report — the heart of the Workspace. A check produces a REPORT,
// not a conversation: verdict-first (fact-check article), structured and measured
// (lab report), every value sourced. Mono is reserved for data (IDs, %, domains, URLs).
import { useState } from 'react'
import {
  Copy, Check as CheckIcon, ExternalLink, ChevronDown, Share2, ShieldCheck,
  CornerUpLeft, FlaskConical,
} from 'lucide-react'
import { statusOf, confReading, reportId } from '../theme.js'
import ActionCenter from './ActionCenter.jsx'

const fmtWhen = (ts) => {
  const d = new Date(ts || Date.now())
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function Label({ children, n }) {
  return (
    <div className="mb-[10px] flex items-center gap-[10px]">
      <span className="vk-label">{children}</span>
      <span className="h-px flex-1" style={{ background: '#E5E7E7' }} />
      {n != null && <span className="font-mono text-[10.5px] tnum text-muted-faint">{n}</span>}
    </div>
  )
}

function href(url) {
  if (!url) return null
  return /^https?:\/\//.test(url) ? url : `https://${url}`
}

export default function Report({ entry, result, lang, region = 'IN', setRegion, onReset }) {
  const [showMethod, setShowMethod] = useState(false)
  const [copied, setCopied] = useState(false)
  const [shared, setShared] = useState(false)

  const isHi = lang === 'hi'
  const st = statusOf(result)
  const Icon = st.Icon
  const conf = confReading(result)
  const ts = entry?.ts || Date.now()
  const rid = entry?.reportId || reportId(ts)
  const claim = (result.claims && result.claims[0]) || entry?.snippet || 'Submitted forward'
  const answers = (result.answers || []).filter((a) => a && (a.a || a.q))
  const sources = result.sources || []
  const counter = isHi ? (result.counterHi || result.counterEn) : result.counterEn
  const counterAlt = isHi ? result.counterEn : result.counterHi
  const meaning = isHi ? (result.meaningHi || result.meaningEn) : result.meaningEn
  const probs = result.probs && typeof result.probs === 'object' ? result.probs : null

  const copyReply = () => {
    try { counter && navigator.clipboard?.writeText(counter) } catch {}
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }
  const shareReport = async () => {
    const text = `VERIFICATION — ${st.label}\nClaim: ${claim}\n${meaning || ''}\n${sources.slice(0, 3).map((s) => '· ' + s.org).join('\n')}\n— Viveka · ${rid}`
    try {
      if (navigator.share) await navigator.share({ title: `Viveka verification ${rid}`, text })
      else { await navigator.clipboard?.writeText(text); setShared(true); setTimeout(() => setShared(false), 2000) }
    } catch {}
  }

  return (
    <div className="animate-vk-fadeup">
      {/* ---------- Report letterhead ---------- */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-[11px]" style={{ borderColor: '#E5E7E7' }}>
        <div className="flex items-center gap-[9px]">
          <FlaskConical size={15} style={{ color: '#136F7A' }} />
          <span className="vk-label" style={{ color: '#3A3F47' }}>Verification Report</span>
        </div>
        <div className="flex items-center gap-[14px] font-mono text-[11px] tnum text-muted-faint">
          <span style={{ color: '#136F7A' }}>{rid}</span>
          <span className="hidden sm:inline">{fmtWhen(ts)}</span>
        </div>
      </div>

      {/* ---------- Subject (the claim) ---------- */}
      <div className="pt-[18px]">
        <div className="vk-label mb-[7px]">Subject</div>
        <p className="m-0 border-l-2 pl-[13px] text-[15.5px] leading-[1.5] text-ink font-deva" style={{ borderColor: '#D5D8D8' }}>{claim}</p>
      </div>

      {/* ---------- Result banner (verdict-first) ---------- */}
      <div className="mt-[18px] overflow-hidden rounded-[10px] border" style={{ borderColor: st.line, background: st.bg }}>
        <div className="flex items-stretch">
          <span className="w-[5px] flex-shrink-0" style={{ background: st.color }} />
          <div className="flex flex-1 items-center gap-[14px] px-[16px] py-[15px]">
            <span className="flex h-[42px] w-[42px] flex-shrink-0 items-center justify-center rounded-[9px]" style={{ background: '#fff', border: `1px solid ${st.line}` }}>
              <Icon size={23} strokeWidth={2.2} style={{ color: st.color }} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-[10px]">
                <span className="vk-label" style={{ color: st.color, opacity: 0.85 }}>Result</span>
              </div>
              <div className="font-sans text-[24px] font-bold leading-[1.1] tracking-[-0.01em]" style={{ color: st.color }}>{st.label}</div>
              <p className="m-0 mt-[3px] text-[13px] leading-[1.4]" style={{ color: '#3A3F47' }}>{st.gloss}</p>
            </div>
          </div>
        </div>
      </div>

      {/* ---------- Confidence reading (lab value) ---------- */}
      <div className="mt-[14px] rounded-[10px] border bg-raised px-[15px] py-[13px]" style={{ borderColor: '#E5E7E7' }}>
        <div className="flex items-center justify-between">
          <span className="vk-label">Confidence</span>
          {conf.verified ? (
            <span className="inline-flex items-center gap-[5px] font-mono text-[11.5px] font-semibold" style={{ color: '#1C7C54' }}>
              <ShieldCheck size={13} /> VERIFIED RECORD
            </span>
          ) : (
            <span className="font-mono text-[13px] tnum font-semibold text-ink">{conf.pct}<span className="text-muted-faint">%</span> · <span style={{ color: '#3A3F47' }}>{conf.band}</span></span>
          )}
        </div>
        {!conf.verified && (
          <>
            <div className="mt-[10px] h-[6px] overflow-hidden rounded-full" style={{ background: '#EAECEC' }}>
              <div className="h-full origin-left rounded-full animate-vk-grow" style={{ width: `${conf.pct}%`, background: st.color }} />
            </div>
            <div className="mt-[5px] flex justify-between font-mono text-[9.5px] tnum text-muted-faint">
              <span>LOW</span><span>MODERATE</span><span>HIGH</span>
            </div>
          </>
        )}
      </div>

      {/* ---------- Assessment + findings (article TL;DR) ---------- */}
      {meaning && (
        <div className="mt-[20px]">
          <Label>Assessment</Label>
          <p className="m-0 text-[15px] leading-[1.55] text-ink font-deva">{meaning}</p>
        </div>
      )}

      {answers.length > 0 && (
        <div className="mt-[18px]">
          <Label n={`${answers.length} checked`}>Findings</Label>
          <div className="flex flex-col">
            {answers.map((a, i) => (
              <div key={i} className="border-b py-[10px] last:border-b-0" style={{ borderColor: '#EEF0F0' }}>
                {a.q && <div className="text-[12px] leading-[1.4] text-muted-label">{a.q}</div>}
                <div className="mt-[3px] flex items-start gap-[8px]">
                  <span className="mt-[6px] h-[5px] w-[5px] flex-shrink-0 rounded-full" style={{ background: st.color }} />
                  <p className="m-0 flex-1 text-[13.5px] leading-[1.45] text-ink-soft font-deva">{a.a}</p>
                </div>
                {a.src && <div className="mt-[3px] pl-[13px] font-mono text-[10.5px] text-muted-faint">{String(a.src).replace(/^https?:\/\/(www\.)?/, '')}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---------- Recommended reply (the action) ---------- */}
      {counter && (
        <div className="mt-[20px]">
          <Label>Recommended reply</Label>
          <div className="rounded-[10px] border bg-raised p-[14px]" style={{ borderColor: '#E5E7E7' }}>
            <p className="m-0 text-[14px] leading-[1.5] text-ink font-deva">{counter}</p>
            {counterAlt && <p className="m-0 mt-[8px] border-t pt-[8px] text-[12.5px] leading-[1.45] text-muted-label font-deva" style={{ borderColor: '#EEF0F0' }}>{counterAlt}</p>}
            <button onClick={copyReply} className="mt-[12px] flex w-full cursor-pointer items-center justify-center gap-[8px] rounded-[8px] py-[11px] text-[13.5px] font-semibold text-white transition-colors" style={{ background: copied ? '#1C7C54' : '#136F7A' }}>
              {copied ? <><CheckIcon size={15} /> Copied to clipboard</> : <><Copy size={15} /> Copy reply</>}
            </button>
          </div>
        </div>
      )}

      {/* ---------- Act layer (gated on the verdict, region-adaptive) ---------- */}
      <ActionCenter result={result} lang={lang} region={region} setRegion={setRegion} />

      {/* ---------- Evidence table (lab results) ---------- */}
      {sources.length > 0 && (
        <div className="mt-[20px]">
          <Label n={`${sources.length} source${sources.length === 1 ? '' : 's'}`}>Evidence</Label>
          <div className="overflow-hidden rounded-[10px] border" style={{ borderColor: '#E5E7E7' }}>
            {sources.map((s, i) => {
              const link = href(s.url)
              const auth = s.tier === 'authoritative' || s.is_factcheck
              return (
                <div key={i} className="flex items-start gap-[11px] border-b bg-surface px-[13px] py-[11px] last:border-b-0" style={{ borderColor: '#EEF0F0' }}>
                  <span className="mt-[1px] font-mono text-[11px] tnum text-muted-faint">{String(i + 1).padStart(2, '0')}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-[7px]">
                      <span className="text-[13px] font-semibold text-ink">{s.org}</span>
                      {auth && <span className="rounded-[3px] px-[5px] py-[1px] font-mono text-[9px] font-semibold uppercase tracking-[0.06em]" style={{ background: '#E8F3EC', color: '#1C7C54' }}>{s.is_factcheck ? 'fact-check' : 'authoritative'}</span>}
                    </div>
                    {s.note && <p className="m-0 mt-[3px] text-[12.5px] leading-[1.45] text-muted">{s.note}</p>}
                    {link && (
                      <a href={link} target="_blank" rel="noopener noreferrer" className="mt-[4px] inline-flex max-w-full items-center gap-[4px] truncate font-mono text-[11px] underline decoration-dotted underline-offset-2 hover:no-underline" style={{ color: '#136F7A' }}>
                        {s.url.replace(/^https?:\/\/(www\.)?/, '')} <ExternalLink size={10} className="flex-shrink-0" />
                      </a>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ---------- Method & reasoning (progressive disclosure) ---------- */}
      <div className="mt-[18px]">
        <button onClick={() => setShowMethod((v) => !v)} className="flex w-full cursor-pointer items-center justify-between rounded-[8px] border bg-surface px-[13px] py-[11px] transition-colors hover:bg-raised" style={{ borderColor: '#E5E7E7' }}>
          <span className="vk-label" style={{ color: '#3A3F47' }}>Method &amp; reasoning</span>
          <ChevronDown size={15} className="text-muted-faint transition-transform" style={{ transform: showMethod ? 'rotate(180deg)' : 'none' }} />
        </button>
        {showMethod && (
          <div className="animate-vk-fade rounded-b-[8px] border border-t-0 px-[14px] py-[13px]" style={{ borderColor: '#E5E7E7' }}>
            {result.weighNote && (
              <div className="mb-[12px]">
                <div className="vk-label mb-[5px]">How the evidence was weighed</div>
                <p className="m-0 text-[13px] leading-[1.5] text-ink-soft">{result.weighNote}</p>
              </div>
            )}
            {probs && (
              <div className="mb-[12px]">
                <div className="vk-label mb-[7px]">Confidence breakdown</div>
                <div className="flex flex-col gap-[6px]">
                  {[['supported', 'Supported'], ['refuted', 'Refuted'], ['conflicting', 'Conflicting'], ['nei', 'Insufficient']].map(([k, lbl]) => {
                    const p = Math.round((probs[k] || 0) * 100)
                    return (
                      <div key={k} className="flex items-center gap-[9px]">
                        <span className="w-[78px] flex-shrink-0 text-[11.5px] text-muted-label">{lbl}</span>
                        <div className="h-[5px] flex-1 overflow-hidden rounded-full" style={{ background: '#EAECEC' }}>
                          <div className="h-full rounded-full" style={{ width: `${p}%`, background: '#136F7A' }} />
                        </div>
                        <span className="w-[34px] flex-shrink-0 text-right font-mono text-[11px] tnum text-muted">{p}%</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-y-[6px] font-mono text-[11px] tnum text-muted-label">
              <span className="text-muted-faint">DOMAIN</span><span className="text-right text-ink-soft">{result.domain || 'general'}</span>
              <span className="text-muted-faint">SOURCES READ</span><span className="text-right text-ink-soft">{sources.length}</span>
              <span className="text-muted-faint">MODEL</span><span className="text-right text-ink-soft">gemma-4-31b-it</span>
              <span className="text-muted-faint">REPORT ID</span><span className="text-right" style={{ color: '#136F7A' }}>{rid}</span>
            </div>
          </div>
        )}
      </div>

      {/* ---------- Actions + footer ---------- */}
      <div className="mt-[18px] flex gap-[9px]">
        <button onClick={onReset} className="flex flex-1 cursor-pointer items-center justify-center gap-[7px] rounded-[8px] border py-[11px] text-[13px] font-semibold text-ink-soft transition-colors hover:bg-raised" style={{ borderColor: '#D5D8D8' }}>
          <CornerUpLeft size={15} /> New verification
        </button>
        <button onClick={shareReport} className="flex flex-1 cursor-pointer items-center justify-center gap-[7px] rounded-[8px] border py-[11px] text-[13px] font-semibold text-ink-soft transition-colors hover:bg-raised" style={{ borderColor: '#D5D8D8' }}>
          {shared ? <><CheckIcon size={15} /> Copied</> : <><Share2 size={15} /> Share report</>}
        </button>
      </div>
      <p className="mt-[14px] text-center font-mono text-[10.5px] leading-[1.6] text-muted-faint">
        Automated verification · grounded in the cited sources · routes to a human when unsure.<br />Record {rid} · not a substitute for professional advice.
      </p>
    </div>
  )
}
