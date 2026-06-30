/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        guardian: {
          bg: '#0f1117',
          card: '#1a1d2e',
          header: '#232640',
          border: '#2d3748',
          muted: '#718096',
          dim: '#4a5568',
          text: '#e2e8f0',
          accent: '#63b3ed',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
