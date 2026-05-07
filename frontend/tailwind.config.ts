import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg:            '#0e1311',
        panel:         '#141a17',
        'panel-2':     '#1a211d',
        ink:           '#d8e4d8',
        'ink-dim':     '#8a9a8c',
        'ink-faint':   '#56625a',
        line:          '#2c3530',
        'line-strong': '#44504a',
        amber:         '#c9a24a',
        'amber-dim':   '#7a6428',
        green:         '#6f9b6e',
        'green-dim':   '#3a5239',
        red:           '#b56353',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
