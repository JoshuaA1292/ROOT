import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:      '#f0fdf4',
        surface: '#ffffff',
        raised:  '#f1f5f9',
        green: {
          DEFAULT: '#16a34a',
          mid:     '#22c55e',
          light:   '#4ade80',
          pale:    '#dcfce7',
          mist:    '#f0fdf4',
          deep:    '#15803d',
          border:  '#bbf7d0',
        },
        text: {
          DEFAULT: '#0f172a',
          2:       '#334155',
          muted:   '#64748b',
          subtle:  '#94a3b8',
        },
        amber: {
          DEFAULT: '#d97706',
          light:   '#fef3c7',
        },
        border: '#e2e8f0',
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'green-sm':  '0 1px 3px rgba(22,163,74,0.15), 0 2px 8px rgba(22,163,74,0.1)',
        'green-md':  '0 2px 8px rgba(22,163,74,0.2), 0 8px 24px rgba(22,163,74,0.12)',
        'green-lg':  '0 4px 16px rgba(22,163,74,0.25), 0 16px 40px rgba(22,163,74,0.15)',
        'panel':     '0 0 0 1px rgba(0,0,0,0.06), -8px 0 32px rgba(0,0,0,0.08)',
        'card':      '0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)',
        'card-hover':'0 2px 8px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)',
        'amber':     '0 2px 8px rgba(217,119,6,0.2), 0 4px 16px rgba(217,119,6,0.12)',
      },
      animation: {
        'fade-up':    'fade-up 0.45s cubic-bezier(0.22,1,0.36,1) both',
        'fade-in':    'fade-in 0.3s ease both',
        'slide-right':'slide-right 0.35s cubic-bezier(0.22,1,0.36,1) both',
        'scale-in':   'scale-in 0.3s cubic-bezier(0.22,1,0.36,1) both',
        'pulse-ring': 'pulse-ring 1.6s cubic-bezier(0,0,0.2,1) infinite',
        'leaf-sway':  'leaf-sway 3s ease-in-out infinite',
        'blink':      'blink 1.1s step-end infinite',
        'shimmer':    'shimmer 1.4s ease-in-out infinite',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
    },
  },
  plugins: [],
}

export default config
