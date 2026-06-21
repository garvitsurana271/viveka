// The "Act" layer — GATED on the verdict and ADAPTIVE to the user's region.
// Decisive verdict -> warn the group + report to the right authority (India OR US)
// + protect. Abstained verdict -> Viveka REFUSES to act and routes to a human.
// The verification engine is region-neutral (it scored on US claims on AVeriTeC);
// only the reporting channels localize.

// Real, official reporting channels per region.
const CHANNELS = {
  IN: {
    chakshu: { id: 'chakshu', icon: 'shield', label: 'Report on Chakshu (Sanchar Saathi)',
      desc: 'Government portal to report fraud WhatsApp/SMS messages and scam links — when no money was lost yet.',
      href: 'https://sancharsaathi.gov.in/sfc/' },
    cyber: { id: 'cyber', icon: 'alert', label: 'Cyber-crime 1930 · cybercrime.gov.in',
      desc: 'If money was already sent, report here at once — the first hour matters most.',
      href: 'https://cybercrime.gov.in/' },
    factcheck: { id: 'pib', icon: 'landmark', label: 'PIB Fact Check',
      desc: 'The official government fact-check unit — for fake claims about government schemes or notices.',
      href: 'https://wa.me/918799711259' },
  },
  US: {
    chakshu: { id: 'ftc', icon: 'shield', label: 'Report to the FTC (ReportFraud.ftc.gov)',
      desc: 'The U.S. Federal Trade Commission portal for reporting scams, fraud texts and phishing.',
      href: 'https://reportfraud.ftc.gov/' },
    cyber: { id: 'ic3', icon: 'alert', label: 'FBI IC3 (ic3.gov)',
      desc: 'If money was lost or it’s an online crime, file with the FBI’s Internet Crime Complaint Center.',
      href: 'https://www.ic3.gov/' },
    factcheck: { id: 'fcc', icon: 'landmark', label: 'FCC complaint · forward to 7726',
      desc: 'Report spam/robocall texts to the FCC, or forward the text to 7726 (SPAM) to flag it to carriers.',
      href: 'https://consumercomplaints.fcc.gov/' },
  },
}

export const REGIONS = { IN: 'India', US: 'United States' }

export function detectRegion() {
  try {
    const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '')
    const loc = navigator.language || ''
    if (/Kolkata|Calcutta/i.test(tz) || /-IN\b/i.test(loc)) return 'IN'
    if (/America\//i.test(tz) || /-US\b/i.test(loc) || /^en-US/i.test(loc)) return 'US'
  } catch { /* ignore */ }
  return 'IN' // flagship default
}

const SCAM_RE = /(https?:\/\/|bit\.ly|tinyurl|register|click here|kyc|otp|lottery|prize|cashback|refund|deposit|wallet|\bupi\b|free laptop|free gift|gift card|account.*(block|suspend))/i

function protectFor(domain, scammy, region) {
  const lossLine = region === 'US'
    ? 'Block the sender; if money was already sent, file at ic3.gov and call your bank now.'
    : 'Block the sender; if money was already sent, call 1930 immediately.'
  if (domain === 'finance' || scammy) return [
    'Do not click any link or call any number in the message.',
    region === 'US'
      ? 'Never share a one-time code, SSN, or card details — no real bank or agency asks by text.'
      : 'Never share an OTP, PIN, CVV or password — no real bank or agency ever asks.',
    lossLine,
  ]
  if (domain === 'health') return [
    'Do not rely on this instead of real medical care.',
    region === 'US' ? 'Check the CDC or FDA, or ask a doctor, before acting on it.' : 'Check WHO or ICMR, or ask a doctor, before acting on it.',
    'Do not forward it to elderly or unwell family.',
  ]
  if (domain === 'communal' || domain === 'disaster') return [
    'Do not forward — messages like this can cause panic or real-world harm.',
    'Verify with local authorities or an official source before acting.',
    'Use the messaging app’s Report option on dangerous or inciting messages.',
  ]
  return [
    'Pause before forwarding — forwarding a false claim spreads the harm.',
    'Send the correction below back to whoever forwarded it to you.',
    region === 'US' ? 'When unsure, check a trusted fact-checker (Snopes, PolitiFact, AP Fact Check).' : 'When unsure, check a trusted fact-checker (PIB, Alt News, BOOM).',
  ]
}

// mode: 'act' (decisive harmful) | 'hold' (abstained) | 'none' (supported / not-a-claim)
export function buildActions(result, lang, region = 'IN') {
  const ch = CHANNELS[region] || CHANNELS.IN
  const verdict = (result?.verdict || '').toLowerCase()
  const domain = result?.domain || 'general'
  const blob = (result?.claims || []).join(' ') + ' ' + (result?.meaningEn || '')
  const scammy = SCAM_RE.test(blob)
  const counter = (lang === 'hi' ? result?.counterHi || result?.counterEn : result?.counterEn) || ''

  if (verdict === 'true' || verdict === 'opinion') return { mode: 'none' }

  if (verdict === 'human') {
    const tipline = []
    if (domain === 'finance' || scammy) tipline.push(ch.chakshu)
    tipline.push(ch.factcheck)
    return { mode: 'hold', protect: protectFor(domain, scammy, region), tipline }
  }

  const reports = []
  if (domain === 'finance' || scammy) { reports.push(ch.chakshu); reports.push(ch.cyber) }
  if (domain === 'general' && !reports.length) reports.push(ch.factcheck)

  return {
    mode: 'act',
    whatsapp: counter ? { text: counter, href: `https://wa.me/?text=${encodeURIComponent(counter)}` } : null,
    reports,
    protect: protectFor(domain, scammy, region),
  }
}
