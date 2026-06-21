// Demo content for the verification surfaces.
// This IS the demo — the calibration nuance (garlic = Misleading, not False) and
// the abstention story (white-van = Needs human check) live here. Don't dilute it.
// When the live engine is wired, CHECK calls the API instead of reading SAMPLES.

export const LANGS = [
  { key: 'en', label: 'English', glyph: 'A', sub: 'default' },
  { key: 'hi', label: 'हिन्दी Hindi', glyph: 'अ', sub: 'Devanagari' },
  { key: 'hinglish', label: 'Hinglish', glyph: 'Aअ', sub: 'Roman Hindi' },
  { key: 'ta', label: 'தமிழ் Tamil', glyph: 'அ', sub: 'regional' },
]

export const SAMPLES = {
  garlic: {
    icon: 'garlic',
    label: 'Garlic cures COVID-19',
    tag: 'health',
    textEn:
      'Eating raw garlic CURES coronavirus — even doctors confirm it! No need for the hospital. Forward to everyone you love. 🙏',
    textHi:
      'कच्चा लहसुन खाने से कोरोना ठीक हो जाता है — डॉक्टर भी मानते हैं! अस्पताल जाने की ज़रूरत नहीं। अपनों को भेजो।',
    glossEn:
      'Eating raw garlic cures coronavirus — even doctors confirm it. No need for hospital. Forward to everyone.',
    claims: ['Eating raw garlic cures COVID-19.', 'Doctors confirm garlic as a cure.'],
    sources: [
      { org: 'WHO', badge: 'W', url: 'who.int/myth-busters', note: 'Garlic is healthy but there is no evidence it protects against or cures COVID-19.' },
      { org: 'ICMR (India)', badge: 'I', url: 'icmr.gov.in', note: 'No food or home remedy is a proven cure for COVID-19.' },
      { org: 'Reuters Fact Check', badge: 'R', url: 'reuters.com/fact-check', note: 'Rated similar garlic-cure claims as false/misleading.' },
    ],
    verdict: 'misleading',
    confidence: 92,
    weighNote:
      'There is a grain of truth — garlic has general health benefits — but the cure claim is unsupported. That mix is why it lands on "misleading," not outright "false."',
    meaningEn:
      'Garlic is healthy, but it does NOT cure or prevent COVID-19. Treating it as a cure can stop someone from getting real medical care.',
    meaningHi:
      'लहसुन सेहतमंद है, पर यह कोविड-19 को न रोकता है, न ठीक करता है। इसे इलाज समझना खतरनाक हो सकता है।',
    counterEn:
      'Hi! I checked this 🙏 Garlic is healthy, but it does NOT cure or prevent COVID-19 — that’s confirmed by the WHO and ICMR. Please don’t rely on it. If someone is unwell, see a doctor.',
    counterHi:
      'नमस्ते! मैंने जाँच की 🙏 लहसुन सेहतमंद है पर कोरोना को न रोकता है न ठीक करता है — WHO और ICMR यही कहते हैं। कृपया इस पर भरोसा न करें, तबीयत खराब हो तो डॉक्टर को दिखाएँ।',
    escalate: true,
  },
  van: {
    icon: 'van',
    label: 'White-van kidnapping alert',
    tag: 'safety',
    textEn:
      'URGENT 🚨 A white van is grabbing children near the market. The gang has been active for 3 days. Police are staying silent. Forward to EVERY parent NOW!',
    textHi:
      'ज़रूरी 🚨 बाज़ार के पास सफ़ेद वैन बच्चों को उठा रही है। गिरोह 3 दिन से सक्रिय है। पुलिस चुप है। हर माता-पिता को अभी भेजें!',
    glossEn:
      'Urgent: a white van is grabbing children near the market. Gang active 3 days. Police silent. Forward to every parent now.',
    claims: ['A white van is kidnapping children near the market.', 'Police are covering it up.'],
    sources: [
      { org: 'State police feed', badge: 'P', url: 'live advisory check', note: 'No matching kidnapping advisory found in the last 7 days.' },
      { org: 'PIB Fact Check', badge: 'P', url: 'pib.gov.in/factcheck', note: '"White van" child-lifting forwards are a recurring template hoax across regions.' },
    ],
    verdict: 'human',
    confidence: 38,
    weighNote:
      'This is a fast-moving, local, real-time safety claim. Trusted sources can’t confirm or deny it yet, and getting it wrong could cause panic or vigilante harm. Too risky to auto-rule.',
    meaningEn:
      'Viveka can’t verify this on its own. It names a specific local event that trusted sources haven’t confirmed — and these "white van" alerts are a common hoax pattern. A human is checking before any verdict.',
    meaningHi:
      'विवेका इसे खुद पुष्टि नहीं कर सकता। यह एक स्थानीय घटना का दावा है जिसकी पुष्टि भरोसेमंद स्रोतों से नहीं हुई — और ऐसे "सफ़ेद वैन" संदेश अक्सर अफवाह होते हैं। फैसले से पहले एक व्यक्ति जाँच कर रहा है।',
    counterEn:
      'Please hold on before forwarding 🙏 This alert can’t be confirmed by police yet, and "white van" messages are often false. Forwarding it can cause panic. I’ll share an update once it’s verified.',
    counterHi:
      'कृपया भेजने से पहले रुकें 🙏 पुलिस अभी इसकी पुष्टि नहीं कर पाई है, और "सफ़ेद वैन" वाले संदेश अक्सर झूठे होते हैं। इसे फैलाने से दहशत फैल सकती है। पुष्टि होते ही मैं बताऊँगा/बताऊँगी।',
    escalate: false,
  },
}

export const REVIEW_QUEUE = [
  {
    id: 'r1', harm: 'high', lang: 'Hindi', age: '6 min', group: 'Family • 38 members', reach: 'seen in 12 groups',
    forwardEn: 'URGENT 🚨 A white van is grabbing children near the market. Police are silent. Forward to EVERY parent NOW!',
    forwardGloss: 'सफ़ेद वैन बच्चों को उठा रही है… पुलिस चुप है। हर माता-पिता को भेजें!',
    claims: ['A white van is kidnapping children near the market.', 'Police are covering it up.'],
    sources: ['State police feed — no advisory', 'PIB Fact Check — recurring hoax pattern'],
    suggested: 'human', confidence: 38,
    why: 'Local, real-time safety claim. Sources can neither confirm nor deny, and a wrong call could trigger panic or vigilante harm.',
  },
  {
    id: 'r2', harm: 'high', lang: 'Hinglish', age: '14 min', group: 'Mohalla Updates • 210 members', reach: 'seen in 31 groups',
    forwardEn: 'Govt is giving FREE laptops to all students! Register before midnight at this link 👉 bit.ly/free-lptp-gov',
    forwardGloss: 'Sarkar sab students ko FREE laptop de rahi hai! Aaj raat tak register karo is link pe.',
    claims: ['The government is giving free laptops to all students.', 'Registration link is official.'],
    sources: ['PIB Fact Check — scheme does not exist', 'Domain check — link is a known phishing host'],
    suggested: 'false', confidence: 94,
    why: 'No such scheme exists and the link resolves to a credential-phishing domain. High financial-fraud risk.',
  },
  {
    id: 'r3', harm: 'med', lang: 'Tamil', age: '22 min', group: 'Pension Forum • 96 members', reach: 'seen in 7 groups',
    forwardEn: 'RBI will withdraw all ₹500 notes from December 31. Deposit yours before the deadline or lose the money!',
    forwardGloss: 'டிசம்பர் 31 முதல் ₹500 நோட்டுகள் செல்லாது…',
    claims: ['RBI is withdrawing all ₹500 notes on Dec 31.', 'Money is lost if not deposited.'],
    sources: ['RBI press releases — no such notice', 'Reuters — earlier identical claim was false'],
    suggested: 'false', confidence: 89,
    why: 'No RBI notice exists. Causes financial panic among elderly savers — high real-world harm.',
  },
  {
    id: 'r4', harm: 'med', lang: 'Hindi', age: '40 min', group: 'Health Tips 🌿 • 154 members', reach: 'seen in 19 groups',
    forwardEn: 'Drinking warm water every 15 minutes flushes the coronavirus out of your throat into the stomach where acid kills it.',
    forwardGloss: 'हर 15 मिनट में गर्म पानी पीने से वायरस पेट में चला जाता है…',
    claims: ['Warm water flushes the virus out of the throat.', 'Stomach acid then kills it.'],
    sources: ['WHO — no evidence', 'ICMR — not a recognised preventive'],
    suggested: 'misleading', confidence: 83,
    why: 'Staying hydrated is fine; the "flushes out the virus" mechanism is invented. Mostly harmless but spreads false reassurance.',
  },
  {
    id: 'r5', harm: 'low', lang: 'English', age: '1 hr', group: 'Office Banter • 64 members', reach: 'seen in 2 groups',
    forwardEn: 'If Mondays were a person, they would have unfollowed all of us by now 😂 forward to your tired friends.',
    forwardGloss: '',
    claims: ['No verifiable factual claim — humour.'],
    sources: ['Intent classifier — joke/meme'],
    suggested: 'opinion', confidence: 97,
    why: 'Auto-flagged by a keyword filter but it is a joke. Nothing to fact-check — confirm and clear.',
  },
]

export const PULSE_CATS = [
  { key: 'all', label: 'All' },
  { key: 'health', label: 'Health' },
  { key: 'finance', label: 'Money & scams' },
  { key: 'safety', label: 'Safety' },
  { key: 'civic', label: 'Civic & misc' },
]

// Real rumours + their real verdicts (from the antibody DB). We deliberately carry
// NO fabricated volume/reach numbers — a misinformation tool must not ship fake stats.
// `surge` is an illustrative recency flag for the preview board, not a metric.
export const PULSE_RUMORS = [
  { id: 'p1', cat: 'finance', verdict: 'false', surge: true,
    claim: '"Government is giving FREE laptops to all students — register at this link"',
    gloss: 'A phishing scheme; no such government programme exists.',
    regions: ['Mumbai', 'Pune', 'Ahmedabad'] },
  { id: 'p2', cat: 'safety', verdict: 'human', surge: true,
    claim: '"White-van gangs are kidnapping children near markets"',
    gloss: 'Recurring template hoax; routed to human review.',
    regions: ['Hyderabad', 'Bengaluru'] },
  { id: 'p3', cat: 'health', verdict: 'misleading', surge: false,
    claim: '"Eating raw garlic cures the coronavirus"',
    gloss: 'Garlic is healthy but does not cure or prevent COVID-19.',
    regions: ['Delhi', 'Lucknow', 'Patna'] },
  { id: 'p4', cat: 'finance', verdict: 'false', surge: false,
    claim: '"RBI will withdraw all ₹500 notes on December 31"',
    gloss: 'No such RBI notice exists. Identical claim was debunked before.',
    regions: ['Chennai', 'Kolkata'] },
  { id: 'p5', cat: 'civic', verdict: 'false', surge: false,
    claim: '"The new currency note contains a hidden GPS tracking chip"',
    gloss: 'Notes contain only standard security features — no chip.',
    regions: ['Jaipur', 'Delhi'] },
  { id: 'p6', cat: 'health', verdict: 'false', surge: false,
    claim: '"The COVID vaccine makes your body magnetic"',
    gloss: 'Vaccines contain no metals or microchips; physically impossible.',
    regions: ['Kolkata', 'Bhubaneswar'] },
]

export const PULSE_HOTSPOTS = [
  { city: 'Delhi', x: 41, y: 27, intensity: 0.78, verdict: 'misleading', cats: ['health', 'civic'] },
  { city: 'Mumbai', x: 29, y: 58, intensity: 0.95, verdict: 'false', cats: ['finance'] },
  { city: 'Hyderabad', x: 45, y: 61, intensity: 0.88, verdict: 'human', cats: ['safety'] },
  { city: 'Bengaluru', x: 42, y: 73, intensity: 0.7, verdict: 'human', cats: ['safety'] },
  { city: 'Chennai', x: 52, y: 77, intensity: 0.55, verdict: 'false', cats: ['finance'] },
  { city: 'Kolkata', x: 74, y: 47, intensity: 0.6, verdict: 'false', cats: ['finance', 'health'] },
  { city: 'Lucknow', x: 53, y: 33, intensity: 0.5, verdict: 'misleading', cats: ['health'] },
  { city: 'Ahmedabad', x: 27, y: 45, intensity: 0.62, verdict: 'false', cats: ['finance'] },
  { city: 'Jaipur', x: 35, y: 31, intensity: 0.38, verdict: 'false', cats: ['civic'] },
]
