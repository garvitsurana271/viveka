# Viveka — UX & Feature Spec (locked)

Web app, $0, three surfaces. Primary user: **the worried forwarder** — someone who just received a suspicious message in a family/community group and wants to know *is this real, and what do I do* before reacting or re-forwarding.

## Verdict taxonomy (the labels Viveka can return)
| Chip | Meaning | When |
|---|---|---|
| ✅ **Likely true** | Evidence supports it | sources confirm |
| ⚠️ **Misleading** | Partly true but distorted / missing context | the most common real case |
| ❌ **False** | Evidence contradicts it | sources refute |
| 🔍 **Needs human check** | Abstain → routed to a reviewer | low confidence OR high-stakes domain |
| 💬 **Not a factual claim** | Opinion / satire / unverifiable | nothing to check |

Every non-abstain verdict carries a **confidence meter** and **shown citations** — no unsourced verdicts, ever.

---

## Surface 1 — CHECK (the hero loop)
Four beats on one screen:

1. **Input.** One box: *"Paste a message, or drop an image or voice note you received."* Tabs: `Text | Image | Voice`. Language auto-detected. Sample chips for the demo. Big, friendly, low-literacy-safe.
2. **Verifying (live reasoning trace).** The box morphs into a streamed step list as the engine runs:
   - `Reading your message… 2 claims found`
   - `Claim 1: "X cures COVID" → searching WHO, ICMR…`
   - `→ WHO: no evidence X cures COVID`
   - `Claim 2: "hospitals are hiding it" → checking…`
   This is the signature "watch it think" beat.
3. **Verdict card.** Verdict chip + confidence meter + **"What this means"** in plain language **in the user's language** + clickable real sources + the **counter-message** (a ready-to-forward reply) with a **Copy** button.
4. **Act.** Copy the counter-message, or **"This looks dangerous → send to a human reviewer"** (pushes it to Surface 2).

**States:** empty (with samples) · verifying · verdict · abstain ("Needs human check — a person will look at this") · error (any module failure degrades here, never a crash).

## Surface 2 — REVIEW (human-in-the-loop)
A reviewer queue: every claim Viveka abstained on or flagged high-stakes. Each row: the original forward, the engine's partial reasoning + evidence, the suggested verdict, and **Confirm / Override / Add note** controls. Shows the Responsible-AI story live — *the AI flags, a human decides*. (Demo seeded with a few realistic items.)

## Surface 3 — PULSE (virality map)
A map/list of **what's spreading now** — claims trending by region, each with its current verdict and how many times it's been checked. Makes the "antibody memory" + community-gap angle tangible: *"this false cure is spiking across 3 states right now."* (Seeded/simulated data, clearly labeled as such.)

---

## Input handling
- **Text** — passthrough; handles Hinglish / code-mixed.
- **Image** — OCR (Tesseract) for text-in-image + reverse-image/web-detection (Google Vision free tier) for out-of-context photos; failure → "Needs human check".
- **Voice** — local Whisper transcription; failure → "Needs human check".
- **Language** — auto-detect → English pivot for reasoning (IndicTrans2/Bhashini) → justification + counter-message translated back to the user's language.

## Multilingual behavior
User writes/speaks in their language; the verdict card, explanation, and counter-message all come back **in that same language**. The reasoning trace can show English internally (it's the engine's working), but everything user-facing is localized.

## Cross-cutting principles
- **Graceful degradation** — every module failure routes to "Needs human check"; the demo cannot hard-break.
- **Flag, never censor** — Viveka informs and equips; it never blocks, hides, or reports a user. (Free-speech-safe.)
- **Accessibility** — large text, high contrast, icon+color+word for every verdict (not color alone), works on low-end screens.

## Visual identity — TBD (next decision)
Mood, palette, and typography to be confirmed; will be built with the frontend-design skill to avoid generic AI aesthetics.
