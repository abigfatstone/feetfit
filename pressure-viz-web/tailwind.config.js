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
        'spin-reverse': 'spin-reverse 1s linear infinite',
        'gradient-shift': 'gradient-shift 4s ease infinite',
        'float': 'float 6s ease-in-out infinite',
        'pulse-modern': 'pulse-modern 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite',
      },
      keyframes: {
        'spin-reverse': {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' },
        },
        'gradient-shift': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center',
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center',
          },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
          '33%': { transform: 'translateY(-10px) rotate(1deg)' },
          '66%': { transform: 'translateY(5px) rotate(-1deg)' },
        },
        'pulse-modern': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.03)' },
        },
        'shimmer': {
          '0%': { 'background-position': '-200% 0' },
          '100%': { 'background-position': '200% 0' },
        },
      },
      boxShadow: {
        'premium': '0 32px 64px -12px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(148, 163, 184, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.6)',
        'intense': '0 48px 96px -24px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(59, 130, 246, 0.1)',
      },
    },
  },
  plugins: [],
}