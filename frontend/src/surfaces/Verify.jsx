// The Verify surface — a verification workspace. Input is search-like (Google),
// output is a structured Report (lab report × fact-check article). The home is the
// check field + your past records; running shows an instrument log, not a chat.
import { useEffect, useRef, useState } from 'react'
import {
  Type, Image as ImageIcon, Mic, ScanSearch, Search, X, AlertTriangle,
  ChevronRight, CheckCircle2, Circle, Loader, FileSearch, Trash2,
} from 'lucide-react'
import { streamCheck } from '../api.js'
import { SAMPLES } from '../data.js'
import { statusOf, reportId } from '../theme.js'
import { relTime } from '../store.js'
import Report from '../components/Report.jsx'

const EMPTY_TRACE = { claims: [], questions: [], sources: [], hops: [], panel: null }
const STAGES = ['Decompose claim', 'Retrieve evidence', 'Reason over evidence', 'Weigh & rate verdict']

export default function Verify({ lang, region = 'IN', setRegion, history = [], recordCheck, wipeHistory, openEntry, onConsumeOpen }) {
  const [phase, setPhase] = useState('home')          // home | running | report | error
  const [mode, setMode] = useState('text')            // text | image | voice
  const [inputText, setInputText] = useState('')
  const [imageData, setImageData] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [imageMime, setImageMime] = useState('image/png')
  const [dragging, setDragging] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceErr, setVoiceErr] = useState('')
  const [extracting, setExtracting] = useState(null)
  const [step, setStep] = useState(0)
  const [trace, setTrace] = useState(EMPTY_TRACE)
  const [matched, setMatched] = useState(false)
  const [slow, setSlow] = useState(false)
  const [result, setResult] = useState(null)
  const [entry, setEntry] = useState(null)
  const [filter, setFilter] = useState('')
  const timers = useRef([])
  const abort = useRef(null)
  const recog = useRef(null)

  const clear = () => { timers.current.forEach(clearTimeout); timers.current = []; if (abort.current) { abort.current.abort(); abort.current = null } }
  useEffect(() => clear, [])

  // Open a stored report when History (or anywhere) requests it.
  useEffect(() => {
    if (openEntry) { showStored(openEntry); onConsumeOpen?.() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openEntry])

  const showStored = (e) => { clear(); setResult(e.result); setEntry(e); setMatched(!!e.matched); setPhase('report') }
  const reset = () => { clear(); setPhase('home'); setResult(null); setEntry(null); setInputText(''); setImageData(null); setImagePreview(null); setMatched(false); setExtracting(null); setVoiceErr('') }

  // ---- image input ----
  const ingestFile = (file) => {
    if (!file || !file.type?.startsWith('image/')) return
    setImageMime(file.type || 'image/png')
    const reader = new FileReader()
    reader.onload = () => { setImagePreview(String(reader.result)); setImageData(String(reader.result).split(',')[1]) }
    reader.readAsDataURL(file)
  }
  const onDrop = (e) => { e.preventDefault(); setDragging(false); ingestFile(e.dataTransfer.files?.[0]) }
  useEffect(() => {
    if (mode !== 'image') return
    const onPaste = (e) => { const f = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith('image/')); if (f) ingestFile(f.getAsFile()) }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [mode])

  // ---- voice input ----
  const startVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) { setVoiceErr('Voice input needs Chrome or Edge. Please type or paste instead.'); return }
    setVoiceErr('')
    if (listening) { recog.current?.stop(); return }
    const r = new SR()
    r.lang = { hi: 'hi-IN', hinglish: 'hi-IN', ta: 'ta-IN', en: 'en-IN' }[lang] || 'en-IN'
    r.interimResults = true; r.continuous = false
    r.onresult = (ev) => { let t = ''; for (let i = 0; i < ev.results.length; i++) t += ev.results[i][0].transcript; setInputText(t) }
    r.onerror = () => { setListening(false); setVoiceErr('Could not hear that. Please try again or type it.') }
    r.onend = () => setListening(false)
    recog.current = r; setListening(true); r.start()
  }

  // ---- run a verification ----
  const recordAndShow = (res, snippetText) => {
    const ts = Date.now()
    const e = {
      id: `c${ts}${Math.round(performance.now())}`, ts, reportId: reportId(ts),
      snippet: (snippetText || res.claims?.[0] || '').trim().slice(0, 120) || 'A checked forward',
      verdict: res.verdict, confidence: res.confidence, matched: !!res.matched, lang, result: res,
    }
    recordCheck?.(e)
    setResult(res); setEntry(e)
  }

  const runCheck = async () => {
    clear()
    let captured = inputText
    setPhase('running'); setStep(0); setTrace(EMPTY_TRACE); setMatched(false); setSlow(false); setExtracting(null)
    abort.current = new AbortController()
    timers.current.push(setTimeout(() => setSlow(true), 12000))
    timers.current.push(setTimeout(() => { try { abort.current?.abort() } catch {} }, 150000))
    const payload = (mode === 'image' && imageData) ? { image: imageData, image_mime: imageMime, lang } : { text: inputText, lang }
    try {
      await streamCheck(payload, {
        extracting: (ev) => setExtracting(ev.kind),
        extracted: (ev) => { setExtracting(null); if (ev.text) { setInputText(ev.text); captured = ev.text } },
        reading: () => setStep(0),
        matched: () => setMatched(true),
        claims: (ev) => { setTrace((t) => ({ ...t, claims: ev.claims })); setStep(1) },
        questions: (ev) => setTrace((t) => ({ ...t, questions: ev.questions })),
        hop: (ev) => setTrace((t) => ({ ...t, hops: [...t.hops, ev] })),
        sources: (ev) => { setTrace((t) => ({ ...t, sources: ev.sources })); setStep(2) },
        escalating: () => setStep(2),
        panel: (ev) => setTrace((t) => ({ ...t, panel: ev })),
        verdict: (ev) => {
          setStep(3)
          recordAndShow(ev.result, captured)
          timers.current.push(setTimeout(() => setPhase('report'), matched ? 500 : 850))
        },
      }, { signal: abort.current.signal })
    } catch {
      const sm = Object.values(SAMPLES).find((x) => inputText === x.textEn || inputText === x.textHi)
      if (mode === 'text' && sm) runMock(sm)
      else setPhase('error')
    }
  }

  const runMock = (sm) => {
    clear(); setStep(0); setTrace({ ...EMPTY_TRACE, claims: sm.claims, sources: sm.sources })
    ;[[1, 800], [2, 1700], [3, 2600]].forEach(([s, t]) => timers.current.push(setTimeout(() => setStep(s), t)))
    recordAndShow(sm, isHiText(sm))
    timers.current.push(setTimeout(() => setPhase('report'), 3400))
  }
  const isHiText = (sm) => (lang === 'hi' ? sm.textHi : sm.textEn)

  const canRun = mode === 'image' ? !!imageData : !!inputText.trim()
  const filtered = filter.trim()
    ? history.filter((h) => (h.snippet || '').toLowerCase().includes(filter.toLowerCase()))
    : history

  // ============================ REPORT ============================
  if (phase === 'report' && result) {
    return (
      <section className="mx-auto w-full max-w-[720px] px-4 pb-24 pt-7 sm:px-6">
        <div className="rounded-[14px] border bg-surface p-5 shadow-panel sm:p-7" style={{ borderColor: '#E5E7E7' }}>
          <Report entry={entry} result={result} lang={lang} region={region} setRegion={setRegion} onReset={reset} />
        </div>
      </section>
    )
  }

  // ============================ RUNNING ============================
  if (phase === 'running') {
    return (
      <section className="mx-auto w-full max-w-[640px] px-4 pb-24 pt-7 sm:px-6">
        <div className="overflow-hidden rounded-[14px] border bg-surface shadow-panel" style={{ borderColor: '#E5E7E7' }}>
          <div className="relative border-b px-5 py-[14px]" style={{ borderColor: '#E5E7E7' }}>
            <div className="absolute left-0 top-0 h-[2px] w-full overflow-hidden">
              <div className="h-full w-1/3 animate-vk-scan" style={{ background: 'linear-gradient(90deg, transparent, #136F7A, transparent)' }} />
            </div>
            <div className="flex items-center gap-[9px]">
              <Loader size={15} className="animate-spin" style={{ color: '#136F7A' }} />
              <span className="vk-label" style={{ color: '#3A3F47' }}>
                {extracting ? (extracting === 'image' ? 'Reading image' : 'Transcribing') : matched ? 'Matching known records' : 'Running verification'}
              </span>
            </div>
          </div>
          <div className="px-5 py-[18px]">
            {matched ? (
              <p className="m-0 text-[13.5px] leading-[1.55] text-muted">This forward matches a record Viveka already verified. Returning the report instantly — no fresh lookup needed.</p>
            ) : (
              <div className="flex flex-col gap-[14px]">
                {STAGES.map((label, i) => {
                  const state = step > i ? 'done' : step === i ? 'active' : 'pending'
                  const detail = i === 0 ? (trace.claims.length ? `${trace.claims.length} claim${trace.claims.length === 1 ? '' : 's'}` : '')
                    : i === 1 ? (trace.sources.length ? `${trace.sources.length} sources` : '')
                    : i === 3 && trace.panel ? `panel ${Math.round((trace.panel.agreement || 0) * 100)}% agree` : ''
                  return (
                    <div key={i} className="flex items-center gap-[11px]">
                      <span className="flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center">
                        {state === 'done' ? <CheckCircle2 size={17} style={{ color: '#1C7C54' }} />
                          : state === 'active' ? <Loader size={16} className="animate-spin" style={{ color: '#136F7A' }} />
                          : <Circle size={15} style={{ color: '#C9CDCD' }} />}
                      </span>
                      <span className="font-mono text-[10.5px] tnum text-muted-faint">{String(i + 1).padStart(2, '0')}</span>
                      <span className="flex-1 text-[13.5px] font-medium" style={{ color: state === 'pending' ? '#9AA0A8' : '#16181C' }}>{label}</span>
                      {detail && <span className="font-mono text-[11px] tnum text-muted-label">{detail}</span>}
                    </div>
                  )
                })}
              </div>
            )}
            {trace.claims.length > 0 && !matched && (
              <div className="mt-[16px] border-t pt-[13px]" style={{ borderColor: '#EEF0F0' }}>
                <div className="vk-label mb-[6px]">Claims identified</div>
                {trace.claims.slice(0, 3).map((c, i) => (
                  <p key={i} className="m-0 mb-[3px] flex gap-[7px] text-[12.5px] leading-[1.45] text-ink-soft font-deva"><span className="text-muted-faint">·</span>{c}</p>
                ))}
              </div>
            )}
            {slow && !matched && <p className="m-0 mt-[14px] font-mono text-[11px] text-muted-faint">Still working — the free reasoning tier can be slow under load.</p>}
          </div>
        </div>
      </section>
    )
  }

  // ============================ ERROR ============================
  if (phase === 'error') {
    return (
      <section className="mx-auto w-full max-w-[560px] px-4 pb-24 pt-12 sm:px-6">
        <div className="rounded-[14px] border bg-surface p-7 text-center shadow-panel" style={{ borderColor: '#E5E7E7' }}>
          <AlertTriangle size={26} className="mx-auto mb-3" style={{ color: '#B23A36' }} />
          <div className="text-[17px] font-semibold text-ink">Verification could not complete</div>
          <p className="mx-auto mb-5 mt-[7px] max-w-[360px] text-[13px] leading-[1.55] text-muted">The engine didn't respond — it may be waking up or under load. Your input was not changed.</p>
          <div className="flex justify-center gap-[9px]">
            <button onClick={reset} className="cursor-pointer rounded-[8px] border px-[16px] py-[10px] text-[13px] font-semibold text-ink-soft" style={{ borderColor: '#D5D8D8' }}>Back</button>
            <button onClick={runCheck} className="cursor-pointer rounded-[8px] px-[18px] py-[10px] text-[13px] font-semibold text-white" style={{ background: '#136F7A' }}>Retry</button>
          </div>
        </div>
      </section>
    )
  }

  // ============================ HOME (the check field) ============================
  const MODES = [{ key: 'text', label: 'Text', Icon: Type }, { key: 'image', label: 'Image', Icon: ImageIcon }, { key: 'voice', label: 'Voice', Icon: Mic }]
  const returning = history.length > 0

  return (
    <section className="mx-auto w-full max-w-[680px] px-4 pb-24 pt-8 sm:px-6 sm:pt-12">
      {!returning && (
        <div className="mb-7 text-center animate-vk-fadeup">
          <h1 className="m-0 text-[27px] font-semibold tracking-[-0.01em] text-ink">Verify a forward</h1>
          <p className="mx-auto mt-[7px] max-w-[44ch] text-[14px] leading-[1.55] text-muted">Paste a message, headline, or claim. Viveka returns a structured verification report — verdict, confidence, evidence and sources — so you can answer one question: <span className="font-medium text-ink-soft">can I trust this?</span></p>
        </div>
      )}

      {/* The search-like check field */}
      <div className="animate-vk-fadeup rounded-[14px] border bg-surface p-[6px] shadow-panel vk-focus" style={{ borderColor: '#E5E7E7' }}>
        {/* mode segmented control */}
        <div className="flex items-center gap-[2px] rounded-[10px] p-[3px]" style={{ background: '#F1F3F3' }}>
          {MODES.map((m) => {
            const on = mode === m.key
            return (
              <button key={m.key} onClick={() => setMode(m.key)} className="flex flex-1 cursor-pointer items-center justify-center gap-[6px] rounded-[8px] py-[7px] text-[12.5px] font-semibold transition-colors"
                style={on ? { background: '#fff', color: '#0C5560', boxShadow: '0 1px 3px rgba(22,24,28,0.10)' } : { background: 'transparent', color: '#727A84' }}>
                <m.Icon size={14} /> {m.label}
              </button>
            )
          })}
        </div>

        {mode === 'text' && (
          <div className="p-[12px]">
            <textarea autoFocus value={inputText} onChange={(e) => setInputText(e.target.value)} rows={4}
              onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && canRun) runCheck() }}
              placeholder="Paste a forward, headline, or claim to verify…"
              className="w-full resize-none border-0 bg-transparent p-0 text-[15px] leading-[1.55] text-ink outline-none font-deva" style={{ minHeight: 84 }} />
          </div>
        )}

        {mode === 'image' && (
          <div className="p-[12px]">
            <label onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop}
              className="flex h-[150px] cursor-pointer items-center justify-center overflow-hidden rounded-[10px] border-2 border-dashed transition-colors"
              style={{ borderColor: dragging ? '#136F7A' : '#D5D8D8', background: imagePreview ? '#0F1413' : dragging ? '#E5F0F1' : '#FAFBFB' }}>
              {imagePreview ? <img src={imagePreview} alt="forward" className="max-h-full max-w-full object-contain" />
                : <div className="flex flex-col items-center gap-[6px]" style={{ color: '#0C5560' }}>
                    <ImageIcon size={24} />
                    <span className="text-[13px] font-semibold">{dragging ? 'Drop the screenshot' : 'Drop, paste, or tap to upload'}</span>
                    <span className="font-mono text-[10.5px] text-muted-faint">reads text from the image · any language</span>
                  </div>}
              <input type="file" accept="image/*" className="hidden" onChange={(e) => ingestFile(e.target.files?.[0])} />
            </label>
          </div>
        )}

        {mode === 'voice' && (
          <div className="p-[12px]">
            <button onClick={startVoice} className="flex w-full cursor-pointer items-center justify-center gap-[10px] rounded-[10px] py-[18px] text-[14px] font-semibold text-white transition-colors" style={{ background: listening ? '#B23A36' : '#136F7A' }}>
              <Mic size={18} /> {listening ? 'Listening… tap to stop' : 'Tap and speak the message'}
            </button>
            {inputText && <p className="m-0 mt-[10px] rounded-[8px] p-[10px] text-[13.5px] leading-[1.45] text-ink font-deva" style={{ background: '#F1F3F3' }}>{inputText}</p>}
            {voiceErr && <p className="m-0 mt-[10px] rounded-[8px] px-[11px] py-[9px] text-[12px]" style={{ background: '#F8E9E8', color: '#8E2D2A' }}>{voiceErr}</p>}
          </div>
        )}

        <button onClick={runCheck} disabled={!canRun}
          className="m-[6px] mt-[2px] flex w-[calc(100%-12px)] cursor-pointer items-center justify-center gap-[8px] rounded-[10px] py-[13px] text-[14.5px] font-semibold text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
          style={{ background: '#136F7A' }}>
          <ScanSearch size={17} /> Verify
        </button>
      </div>

      {/* First run: examples. Returning: your records. */}
      {returning ? (
        <div className="mt-7 animate-vk-fadeup">
          <div className="mb-[10px] flex items-center justify-between gap-3">
            <span className="vk-label">Your verifications · {history.length}</span>
            <button onClick={wipeHistory} className="flex cursor-pointer items-center gap-[5px] font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-faint transition-colors hover:text-muted-label"><Trash2 size={11} /> clear</button>
          </div>
          {history.length > 4 && (
            <div className="mb-[10px] flex items-center gap-[8px] rounded-[9px] border bg-surface px-[11px] py-[8px]" style={{ borderColor: '#E5E7E7' }}>
              <Search size={14} className="text-muted-faint" />
              <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search your records…" className="w-full border-0 bg-transparent text-[13px] text-ink outline-none placeholder:text-muted-faint" />
              {filter && <button onClick={() => setFilter('')} className="cursor-pointer"><X size={13} className="text-muted-faint" /></button>}
            </div>
          )}
          <div className="overflow-hidden rounded-[12px] border bg-surface" style={{ borderColor: '#E5E7E7' }}>
            {filtered.length === 0 && <div className="px-[14px] py-[16px] text-center text-[12.5px] text-muted-faint">No records match “{filter}”.</div>}
            {filtered.slice(0, 12).map((h) => {
              const st = statusOf(h.result || { verdict: h.verdict })
              const Icon = st.Icon
              return (
                <button key={h.id} onClick={() => showStored(h)} className="flex w-full cursor-pointer items-center gap-[12px] border-b px-[14px] py-[11px] text-left transition-colors last:border-b-0 hover:bg-raised" style={{ borderColor: '#EEF0F0' }}>
                  <span className="flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-[7px]" style={{ background: st.bg }}><Icon size={15} strokeWidth={2.3} style={{ color: st.color }} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium text-ink font-deva">{h.snippet}</span>
                    <span className="mt-[1px] block font-mono text-[10.5px] tnum text-muted-faint"><span style={{ color: st.color }}>{st.label}</span> · {h.reportId || ''} · {relTime(h.ts)}</span>
                  </span>
                  <ChevronRight size={15} className="flex-shrink-0 text-muted-faint" />
                </button>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="mt-7 animate-vk-fadeup">
          <div className="mb-[10px] flex items-center gap-[8px]"><FileSearch size={14} className="text-muted-faint" /><span className="vk-label">New here — try a real one</span></div>
          <div className="flex flex-col gap-[8px]">
            {Object.entries(SAMPLES).slice(0, 4).map(([id, sm]) => (
              <button key={id} onClick={() => { setMode('text'); setInputText(lang === 'hi' ? sm.textHi : sm.textEn) }}
                className="flex w-full cursor-pointer items-center gap-[11px] rounded-[10px] border bg-surface px-[13px] py-[11px] text-left transition-colors hover:border-accent-line hover:bg-raised" style={{ borderColor: '#E5E7E7' }}>
                <Search size={14} className="flex-shrink-0 text-muted-faint" />
                <span className="flex-1 text-[13.5px] font-medium text-ink-soft">{sm.label}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted-faint">{sm.tag}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
