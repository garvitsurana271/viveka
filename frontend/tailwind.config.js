/** @type {import('tailwindcss').Config} */
// Viveka — Verification Workspace. Clean & clinical: a verification instrument,
// not a chatbot. Near-white surfaces, cool neutrals, one deep clinical accent,
// and status colors that read like a lab-report flag. IBM Plex Sans + Mono;
// mono is reserved for DATA (confidence, report IDs, timestamps, domains).
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Surfaces — near-white, a whisper cool
        page: '#F6F7F7',
        surface: '#FFFFFF',
        raised: '#FBFCFC',
        // Ink / text — cool near-black down to faint
        ink: '#16181C',
        'ink-soft': '#3A3F47',
        muted: { DEFAULT: '#5A616A', label: '#727A84', faint: '#9AA0A8' },
        // Hairlines / structure
        line: '#E5E7E7',
        'line-strong': '#D5D8D8',
        // The single clinical accent (deep teal-slate) + states
        accent: { DEFAULT: '#136F7A', deep: '#0C5560', soft: '#E5F0F1', line: '#BFDADD' },
        // Verdict status — institutional, slightly desaturated (a lab flag, not a siren)
        v: {
          supported: '#1C7C54', 'supported-bg': '#E8F3EC', 'supported-line': '#C5E2D2',
          refuted: '#B23A36', 'refuted-bg': '#F8E9E8', 'refuted-line': '#ECCAC7',
          misleading: '#946612', 'misleading-bg': '#F6EEDC', 'misleading-line': '#E7D6AE',
          human: '#4B49B6', 'human-bg': '#ECECF8', 'human-line': '#D2D2F0',
          insufficient: '#566069', 'insufficient-bg': '#EEF0F1', 'insufficient-line': '#D8DCDE',
          opinion: '#6B7079', 'opinion-bg': '#EFF0F1', 'opinion-line': '#DCDEE0',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        deva: ['"Noto Sans Devanagari"', '"IBM Plex Sans"', 'sans-serif'],
      },
      letterSpacing: {
        label: '0.12em',  // for the small uppercase mono section labels
      },
      boxShadow: {
        panel: '0 1px 2px rgba(22,24,28,0.04), 0 8px 24px -12px rgba(22,24,28,0.10)',
        raised: '0 1px 3px rgba(22,24,28,0.06), 0 16px 40px -20px rgba(22,24,28,0.16)',
        pop: '0 12px 40px -8px rgba(22,24,28,0.20)',
      },
      keyframes: {
        'vk-fadeup': { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'vk-fade': { from: { opacity: '0' }, to: { opacity: '1' } },
        'vk-scan': { '0%': { transform: 'translateY(-100%)' }, '100%': { transform: 'translateY(400%)' } },
        'vk-pulse': { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.35' } },
        'vk-blink': { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.2' } },
        'vk-grow': { from: { transform: 'scaleX(0)' }, to: { transform: 'scaleX(1)' } },
      },
      animation: {
        'vk-fadeup': 'vk-fadeup .42s cubic-bezier(.2,.7,.3,1) both',
        'vk-fade': 'vk-fade .5s ease both',
        'vk-scan': 'vk-scan 1.5s linear infinite',
        'vk-pulse': 'vk-pulse 1.6s ease-in-out infinite',
        'vk-blink': 'vk-blink 1s steps(2) infinite',
        'vk-grow': 'vk-grow .6s cubic-bezier(.2,.7,.3,1) both',
      },
    },
  },
  plugins: [],
}
