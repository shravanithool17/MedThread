/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: {
          DEFAULT: '#f8f7f4',
          50: '#fafaf8',
          100: '#f8f7f4',
          200: '#ede9df',
          300: '#ddd8cc',
        },
        teal: {
          DEFAULT: '#0d7377',
          50: '#f0fdfc',
          100: '#ccfbf5',
          200: '#99f6eb',
          300: '#5ee8d8',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#0d7377',
          900: '#134e4a',
          950: '#0a3535',
        },
        clinical: {
          affirmed: '#047857',
          'affirmed-bg': '#d1fae5',
          'affirmed-border': '#6ee7b7',
          negated: '#b91c1c',
          'negated-bg': '#fee2e2',
          'negated-border': '#fca5a5',
          uncertain: '#b45309',
          'uncertain-bg': '#fef3c7',
          'uncertain-border': '#fcd34d',
          resolved: '#1d4ed8',
          'resolved-bg': '#dbeafe',
          'resolved-border': '#93c5fd',
          unclear: '#374151',
          'unclear-bg': '#f3f4f6',
          'unclear-border': '#d1d5db',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px 0 rgba(0,0,0,0.04)',
        'card-md': '0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04)',
        'card-lg': '0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -2px rgba(0,0,0,0.04)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
