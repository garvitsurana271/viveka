# Viveka System Card

A one-page, honest account of what Viveka is, how it behaves, and where it fails. Written so our claims match our code.

## Intended use

Help an ordinary person decide whether a forwarded message (chat forward, headline, screenshot, voice note) is trustworthy, in the moment before they forward it, and give them a safe next action. It is a decision aid, not an authority.

## Out of scope

Viveka does not make legal, medical, or financial decisions for the user. It does not block, report, or penalise users. It is not a content-moderation or censorship tool. It is not a substitute for a doctor, a lawyer, a bank, or a professional fact-checker.

## How it decides (and when it declines)

- Pipeline: decompose into claims and questions, retrieve evidence (web + Wikipedia + Google Fact Check, full-document), rate all four AVeriTeC verdicts (Likert-softmax), then commit or abstain on a domain-aware margin.
- Five product verdicts: Supported, Refuted, Misleading, Insufficient Evidence, Requires Human Review (and "Not a factual claim" for opinion/satire).
- **Abstention thresholds.** A domain-aware confidence floor (`ABSTAIN_BELOW`) routes weak verdicts to a human. High-stakes domains (health, communal, disaster) keep the floor even for an otherwise-calibrated verdict.
- **High-stakes corroboration gate** (`engine.py:144`). A decisive verdict on a health / communal / disaster claim must rest on at least one authoritative source (gov / WHO / a real fact-checker) or it is force-routed to a human. This is the main defence against a confident-wrong verdict from poisoned search results.
- **Action is gated by confidence.** The Act layer (warn the group, report the forward) only unlocks on a confident verdict; on an abstained verdict it refuses to act and tells the user to hold and get it checked.

## Measured behaviour (with caveats stated)

- **0.733 macro-F1** on AVeriTeC gold-evidence reasoning, on a **balanced 25-per-class slice** (n=100). This isolates verdict quality given good evidence. It is **label-only**, not the official Ev2R-conditioned AVeriTeC score (SOTA around 0.48). Balanced on purpose so macro-F1 is not inflated by AVeriTeC's natural ~61%-Refuted majority.
- **0.398 macro-F1** live end-to-end (n=40 balanced). Retrieval is the bottleneck; we publish this number.
- **Abstention:** ~15% live; **~36% even on gold evidence** (the high-stakes floor declining to commit). We treat abstention as correct behaviour, not failure.
- **Calibration:** self-reported confidence ECE 0.327 (useless), recalibrated to about **0.21** (still imperfect, which is why we abstain). Measured on the same dev slice, not third-party verified.
- n is small (100 / 40); we report it plainly and do not imply leaderboard precision.

## Safety and robustness controls

- Prompt-injection hardening: the forward and the fetched evidence are both treated as untrusted data; fence-breakouts neutralised.
- SSRF guard on evidence fetching (rejects private / loopback / link-local addresses; no redirect following).
- Per-IP rate limiting; request size caps.
- Graceful degradation: every failing stage routes to "Requires human review"; with no key the engine serves canned reasoning. It never crashes into a wrong answer.

## Data handling and privacy

- Your **check history** lives only in your browser (localStorage). No account, no login, never uploaded.
- **Verification is not local:** the message you check is sent to the reasoning engine (Gemma, via Google's API).
- A **non-high-stakes** rumour may be stored server-side in a shared "antibody" memory (its text, truncated) so the next person who receives it is answered instantly. **High-stakes (health / communal / disaster) verdicts are never cached.**
- Set `VIVEKA_NO_LEARN=1` to disable all server-side learning (curated seeds still load; no user text is persisted).

## Known limitations (stated honestly)

- **Live accuracy is modest (0.398).** On the ~85% of live cases where it commits, it is right less often than a human expert. Its safety answer is to abstain on the hard cases, not to be right on all of them.
- **Multilingual: measured, and it holds.** On a 20-claim gold-evidence slice we ran the shipped recipe on the same claims in English and machine-translated to Hindi: accuracy was **identical (0.65 both)** with **100% verdict agreement**, so the reasoning is robust to Hindi claim phrasing. Honest caveats: this isolates *reasoning* (evidence retrieval is still English-first), and n is small (20). Report: `backend/eval/reports/hindi_slice_dev_n20.json`.
- **Retrieval depends on keyless web search**, which can be rate-limited or blocked from a cloud server IP, degrading live performance.
- **Small n** on every reported metric; decimals should not be read as precise.
- The primary risk we design against is **automation bias** (over-trusting a confident machine). Calibration, abstention, and always-shown sources exist to keep the human in charge.
