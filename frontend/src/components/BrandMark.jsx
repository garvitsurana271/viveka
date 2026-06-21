// The Viveka mark: a conic teal/cream disc — discernment, two halves resolving.
export default function BrandMark({ size = 30, ring = '#f3eee3' }) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'conic-gradient(from 220deg, #0f6e66 0deg 180deg, #e7dfce 180deg 360deg)',
        border: '1.5px solid #0f6e66',
        boxShadow: `inset 0 0 0 ${Math.max(2, Math.round(size / 10))}px ${ring}`,
        flexShrink: 0,
      }}
    />
  )
}
