// A lightweight phone frame for the CHECK surface (CHECK is a true phone screen).
export default function AndroidFrame({ children }) {
  return (
    <div
      style={{
        width: 412,
        height: 860,
        borderRadius: 44,
        background: '#0f0d0a',
        padding: 11,
        boxShadow: '0 30px 70px rgba(40,36,30,0.28), 0 6px 18px rgba(40,36,30,0.16)',
        transform: 'scale(0.83)',
        transformOrigin: 'top center',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          borderRadius: 34,
          overflow: 'hidden',
          background: '#f6f2ea',
        }}
      >
        {/* camera punch-hole */}
        <div
          style={{
            position: 'absolute',
            top: 12,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 9,
            height: 9,
            borderRadius: '50%',
            background: '#0f0d0a',
            zIndex: 20,
          }}
        />
        <div style={{ width: '100%', height: '100%', overflowY: 'auto' }}>{children}</div>
      </div>
    </div>
  )
}
