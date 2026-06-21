// Streams the verification trace from the Viveka engine over SSE.
// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.js).
// In prod, set VITE_ENGINE_URL to the deployed engine's origin.
const BASE = import.meta.env.VITE_ENGINE_URL || ''

// payload: { text?, lang, image?, image_mime?, audio?, audio_mime? }
export async function streamCheck(payload, handlers, { signal } = {}) {
  const res = await fetch(`${BASE}/api/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`engine ${res.status}`)

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, i)
      buf = buf.slice(i + 2)
      const line = block.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      let ev
      try {
        ev = JSON.parse(line.slice(5).trim())
      } catch {
        continue
      }
      if (ev.type === 'error') throw new Error(ev.message || 'engine error')
      handlers[ev.type]?.(ev)
    }
  }
}
