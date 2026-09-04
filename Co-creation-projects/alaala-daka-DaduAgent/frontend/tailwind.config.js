/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#F5F5F7',
        'bg-surface': '#FFFFFF',
        'bg-sidebar': '#ECEDF0',
        'bg-user-bubble': '#007AFF',
        'text-primary': '#1D1D1F',
        'text-secondary': '#6E6E73',
        'text-tertiary': '#AEAEB2',
        'text-user-bubble': '#FFFFFF',
        accent: '#0066CC',
        'accent-hover': '#0077ED',
        success: '#30B158',
        warning: '#FF9F0A',
        danger: '#FF3B30',
        border: '#D2D2D7',
        'border-light': '#E5E5EA',
        'tool-error-bg': '#FFF5F5',
        'tool-error-border': '#FFCCCB',
      },
      fontFamily: {
        sidebar: ['Inter', '-apple-system', 'sans-serif'],
        body: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', '"Fira Code"', 'monospace'],
      },
      backdropBlur: {
        glass: '20px',
      },
      animation: {
        'breathe': 'breathe 2.5s ease-in-out infinite',
        'slide-in-right': 'slideInRight 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { borderColor: '#0066CC' },
          '50%': { borderColor: '#A78BFA' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
