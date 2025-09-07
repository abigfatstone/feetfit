/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      animation: {
        progressBar: 'progressBar 2.5s ease-in-out infinite',
        pulse: 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        ping: 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        bounce: 'bounce 1.5s infinite',
        spin: 'spin 1.5s linear infinite',
        'gradient-x': 'gradient-x 15s ease infinite',
        'gradient-y': 'gradient-y 15s ease infinite',
        'gradient-xy': 'gradient-xy 15s ease infinite',
        'pressure-pulse': 'pressure-pulse 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        progressBar: {
          '0%': { width: '0%' },
          '50%': { width: '100%' },
          '100%': { width: '0%' },
        },
        pulse: {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '0.3' },
        },
        ping: {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '75%, 100%': { transform: 'scale(2)', opacity: '0' },
        },
        bounce: {
          '0%, 100%': { 
            transform: 'translateY(0)',
            animationTimingFunction: 'cubic-bezier(0.8, 0, 1, 1)',
          },
          '50%': { 
            transform: 'translateY(-25%)',
            animationTimingFunction: 'cubic-bezier(0, 0, 0.2, 1)',
          },
        },
        spin: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        'gradient-x': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center'
          },
        },
        'gradient-y': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'center top'
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'center bottom'
          },
        },
        'gradient-xy': {
          '0%, 100%': {
            'background-size': '400% 400%',
            'background-position': 'left center'
          },
          '50%': {
            'background-size': '400% 400%',
            'background-position': 'right center'
          },
        },
        'pressure-pulse': {
          '0%': { transform: 'scale(1)', opacity: '0.8' },
          '50%': { transform: 'scale(1.1)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '0.8' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(59, 130, 246, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(59, 130, 246, 0.8), 0 0 30px rgba(59, 130, 246, 0.6)' },
        },
      },
      boxShadow: {
        'elegant': '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.06)',
        'pressure': '0 0 20px rgba(59, 130, 246, 0.5)',
        'pressure-high': '0 0 30px rgba(239, 68, 68, 0.7)',
        'neon': '0 0 5px theme(colors.blue.400), 0 0 20px theme(colors.blue.400), 0 0 35px theme(colors.blue.400)',
        'cyber': '0 0 10px rgba(0, 255, 255, 0.5), 0 0 20px rgba(0, 255, 255, 0.3), 0 0 30px rgba(0, 255, 255, 0.1)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'pressure-gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'cyber-gradient': 'linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%)',
        'neural-network': 'radial-gradient(circle at 25% 25%, #00ffff22 0%, transparent 50%), radial-gradient(circle at 75% 75%, #ff00ff22 0%, transparent 50%)',
      },
      colors: {
        pressure: {
          50: '#eff6ff',
          100: '#dbeafe', 
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          low: '#3b82f6',
          medium: '#10b981',
          high: '#f59e0b',
          critical: '#ef4444',
        },
        cyber: {
          primary: '#00ffff',
          secondary: '#ff00ff',
          accent: '#ffff00',
          dark: '#0a0a0a',
          blue: '#00d4ff',
          purple: '#b300ff',
          green: '#00ff88',
        }
      },
      fontFamily: {
        'cyber': ['Orbitron', 'monospace'],
        'tech': ['Rajdhani', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
