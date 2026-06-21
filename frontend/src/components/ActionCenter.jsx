// The gated Act layer. Decisive verdict -> warn the group + report to the right
// Indian authority + protect checklist. Abstained verdict -> Viveka REFUSES to act
// and routes to a human. Action is earned by certainty.
import { buildActions, REGIONS } from '../actions.js'
import {
  Send, ShieldAlert, Siren, Landmark, ExternalLink, ShieldQuestion, Check, UserRoundSearch, Globe,
} from 'lucide-react'

const ICON = { shield: ShieldAlert, alert: Siren, landmark: Landmark }

// Small region toggle — channels adapt to where the user is (India / US).
function RegionToggle({ region, setRegion }) {
  if (!setRegion) return null
  return (
    <span className="inline-flex items-center gap-[5px] rounded-[6px] border bg-surface px-[7px] py-[3px]" style={{ borderColor: '#E5E7E7' }}>
      <Globe size={11} className="text-muted-faint" />
      {Object.entries(REGIONS).map(([k, label]) => (
        <button key={k} onClick={() => setRegion(k)} className="cursor-pointer rounded-[4px] px-[6px] py-[1px] font-mono text-[10px] font-semibold uppercase tracking-[0.06em] transition-colors"
          style={region === k ? { background: '#136F7A', color: '#fff' } : { background: 'transparent', color: '#727A84' }}
          title={`Reporting channels for ${label}`}>{k}</button>
      ))}
    </span>
  )
}

function Label({ children }) {
  return (
    <div className="mb-[10px] flex items-center gap-[10px]">
      <span className="vk-label">{children}</span>
      <span className="h-px flex-1" style={{ background: '#E5E7E7' }} />
    </div>
  )
}

function ChannelRow({ ch }) {
  const I = ICON[ch.icon] || Landmark
  return (
    <a href={ch.href} target="_blank" rel="noopener noreferrer" className="flex items-start gap-[11px] border-b bg-surface px-[13px] py-[11px] transition-colors last:border-b-0 hover:bg-raised" style={{ borderColor: '#EEF0F0' }}>
      <span className="mt-[1px] flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-[7px]" style={{ background: '#EEF0F1' }}><I size={15} style={{ color: '#566069' }} /></span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-[5px] text-[13px] font-semibold text-ink">{ch.label} <ExternalLink size={11} className="flex-shrink-0 text-muted-faint" /></span>
        <span className="mt-[2px] block text-[12px] leading-[1.45] text-muted">{ch.desc}</span>
      </span>
    </a>
  )
}

function Protect({ items }) {
  return (
    <div className="mt-[16px]">
      <Label>Protect yourself</Label>
      <div className="flex flex-col gap-[7px]">
        {items.map((t, i) => (
          <div key={i} className="flex items-start gap-[8px]">
            <Check size={14} className="mt-[2px] flex-shrink-0" style={{ color: '#1C7C54' }} />
            <p className="m-0 text-[13px] leading-[1.45] text-ink-soft">{t}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ActionCenter({ result, lang, region = 'IN', setRegion }) {
  const plan = buildActions(result, lang, region)
  if (!plan || plan.mode === 'none') return null

  // ---- Abstained: Viveka won't act, routes to a human (the gating made visible) ----
  if (plan.mode === 'hold') {
    return (
      <div className="mt-[20px]">
        <Label>What to do</Label>
        <div className="rounded-[10px] border px-[14px] py-[13px]" style={{ background: '#ECECF8', borderColor: '#D2D2F0' }}>
          <div className="flex items-center gap-[8px]">
            <ShieldQuestion size={16} style={{ color: '#4B49B6' }} />
            <span className="text-[13.5px] font-semibold" style={{ color: '#4B49B6' }}>Viveka won&apos;t act on this one</span>
          </div>
          <p className="m-0 mt-[6px] text-[12.5px] leading-[1.5]" style={{ color: '#3A3F47' }}>
            It only warns a group or reports a forward when it reaches a confident verdict. This one didn&apos;t — so rather than spread an unverified rebuttal, <strong>don&apos;t forward it</strong>, and get a human to check it.
          </p>
        </div>
        {plan.tipline?.length > 0 && (
          <div className="mt-[12px] overflow-hidden rounded-[10px] border" style={{ borderColor: '#E5E7E7' }}>
            <div className="flex items-center justify-between gap-[7px] border-b bg-raised px-[13px] py-[8px]" style={{ borderColor: '#EEF0F0' }}>
              <span className="flex items-center gap-[7px]"><UserRoundSearch size={13} className="text-muted-label" /><span className="vk-label" style={{ color: '#3A3F47' }}>Get it checked</span></span>
              <RegionToggle region={region} setRegion={setRegion} />
            </div>
            {plan.tipline.map((ch) => <ChannelRow key={ch.id} ch={ch} />)}
          </div>
        )}
        <Protect items={plan.protect} />
      </div>
    )
  }

  // ---- Decisive verdict: act on it ----
  return (
    <div className="mt-[20px]">
      <Label>Act on this</Label>
      <div className="rounded-[10px] border px-[13px] py-[11px]" style={{ background: '#E8F3EC', borderColor: '#C5E2D2' }}>
        <p className="m-0 text-[12px] leading-[1.5]" style={{ color: '#1C7C54' }}>
          <strong>Unlocked by a confident verdict.</strong> Viveka reached a clear ruling, so you can safely push back and report it.
        </p>
      </div>

      {plan.whatsapp && (
        <a href={plan.whatsapp.href} target="_blank" rel="noopener noreferrer" className="mt-[12px] flex w-full items-center justify-center gap-[8px] rounded-[9px] py-[12px] text-[14px] font-semibold text-white transition-colors hover:opacity-95" style={{ background: '#136F7A' }}>
          <Send size={16} /> Warn your group on WhatsApp
        </a>
      )}

      {plan.reports?.length > 0 && (
        <div className="mt-[14px]">
          <div className="mb-[10px] flex items-center justify-between gap-[10px]">
            <span className="vk-label">Report this forward</span>
            <RegionToggle region={region} setRegion={setRegion} />
          </div>
          <div className="overflow-hidden rounded-[10px] border" style={{ borderColor: '#E5E7E7' }}>
            {plan.reports.map((ch) => <ChannelRow key={ch.id} ch={ch} />)}
          </div>
        </div>
      )}

      <Protect items={plan.protect} />
    </div>
  )
}
